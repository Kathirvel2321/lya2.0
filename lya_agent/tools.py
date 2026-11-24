"""Phase-1 tools for the LYA agent: the ONLY actions the model can take.

Seven in-process MCP tools (create_sdk_mcp_server). Every argument is
allowlist-checked here; the model never names a raw path, raw exe, or raw
command. All tool results returned to the model are wrapped in
<untrusted_data> and truncated to 4000 chars. Tools tagged "danger" (none in
Phase 1) would require owner confirmation; the plumbing denies when that
flow is unavailable.
"""
from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path

from lya_agent import pathguard
from lya_agent.config import (MAX_TEXT_BYTES, TEXT_EXTENSIONS, ConfigError,
                              load_config)

log = logging.getLogger("lya_agent.tools")

MAX_RESULT_CHARS = 4000
UIA_WAIT_SECONDS = 5.0

# UI automation library choice: pywinauto - it exposes window.process_id()
# directly (needed for the apps-allowlist check) and has a stable Desktop API.
_pywinauto_lock = threading.Lock()


class ToolError(RuntimeError):
    pass


class ToolContext:
    """Allowlists + audit + optional owner-confirm, shared by all tools."""

    def __init__(self, config: dict, audit=None):
        self.apps: dict[str, Path] = config["apps"]
        self.folders: dict[str, Path] = config["folders"]
        self.audit = audit                    # ChainedAudit-like or None
        self.owner_confirm = None             # callable(action, summary) -> bool

    def _audit(self, command: str, subject: str, outcome: str) -> None:
        if self.audit is None:
            return
        try:
            self.audit.log(command, subject, outcome, approver="agent")
        except Exception:
            log.exception("audit write failed")


def _deny_danger(ctx: ToolContext, action: str) -> bool:
    """Danger-tier gate. No Phase-1 tool is danger-tagged. If one ever is,
    owner confirmation is mandatory: unavailable flow => deny."""
    if action != "danger":
        return False
    if ctx.owner_confirm is None:
        log.warning("danger-tier tool requested but no owner-confirm flow; denying")
        ctx._audit("danger", "unavailable", "denied")
        return True
    return False


def wrap_result(text: str) -> str:
    """Wrap tool output as untrusted data, truncated. Prompt-injection
    defence: the model is told (system prompt) never to follow instructions
    found inside."""
    text = text if isinstance(text, str) else str(text)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS - 20] + "...[truncated]"
    return f"<untrusted_data>{text}</untrusted_data>"


# ---- window lookup --------------------------------------------------------------

def _exe_name_for_pid(pid: int) -> str | None:
    """Process image name WITHOUT pulling in psutil: QueryFullProcessImageNameW."""
    import ctypes
    import ctypes.wintypes as wt
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wt.DWORD(len(buf))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return None
        return Path(buf.value).name.lower()
    finally:
        kernel32.CloseHandle(handle)


def _allowlisted_window(ctx: ToolContext, title_substring: str):
    """Return the first top-level UIA window whose title matches and whose
    process image is an allowlisted app exe. None when no match."""
    from pywinauto import Desktop          # lazy import; Windows-only
    exe_names = {Path(str(p)).name.lower() for p in ctx.apps.values()}
    with _pywinauto_lock:
        desktop = Desktop(backend="uia")
        for window in desktop.windows():
            try:
                text = window.window_text() or ""
                if title_substring.lower() not in text.lower():
                    continue
                pid = window.process_id()
            except Exception:
                continue                       # window vanished mid-iteration
            exe_name = _exe_name_for_pid(pid)
            if exe_name and exe_name in exe_names:
                return window
    return None


# ---- tool implementations (sync; thin async wrappers register them) -------------

def open_app(ctx: ToolContext, name: str) -> str:
    if not isinstance(name, str) or name not in ctx.apps:
        ctx._audit("open_app", str(name)[:40], "denied-not-allowlisted")
        raise ToolError(f"{name!r} is not in the apps allowlist.")
    exe = str(ctx.apps[name])
    try:
        subprocess.Popen([exe], shell=False, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        ctx._audit("open_app", name, f"failed:{type(exc).__name__}")
        raise ToolError(f"could not launch {name}: {exc}") from exc
    ctx._audit("open_app", name, "ok")
    return f"launched {name}"


def open_folder(ctx: ToolContext, alias: str) -> str:
    if not isinstance(alias, str) or alias not in ctx.folders:
        ctx._audit("open_folder", str(alias)[:40], "denied-not-allowlisted")
        raise ToolError(f"{alias!r} is not in the folders allowlist.")
    root = ctx.folders[alias]
    if not root.is_dir():
        ctx._audit("open_folder", alias, "failed:missing")
        raise ToolError(f"folder {alias!r} no longer exists on disk.")
    subprocess.Popen(["explorer", str(root)], shell=False)
    ctx._audit("open_folder", alias, "ok")
    return f"opened folder {alias}"


def list_dir(ctx: ToolContext, alias: str, subpath: str) -> str:
    if not isinstance(alias, str) or alias not in ctx.folders:
        ctx._audit("list_dir", str(alias)[:40], "denied-not-allowlisted")
        raise ToolError(f"{alias!r} is not in the folders allowlist.")
    try:
        target = pathguard.check_subpath(ctx.folders[alias], subpath or ".")
    except pathguard.PathOutsideAllowlist as exc:
        ctx._audit("list_dir", alias, f"denied:{type(exc).__name__}")
        raise ToolError(f"refused: {exc}") from exc
    if not target.is_dir():
        ctx._audit("list_dir", alias, "failed:not-a-folder")
        raise ToolError(f"{subpath!r} is not a folder inside {alias}.")
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    names = [f"{p.name}{'/' if p.is_dir() else ''}" for p in entries[:200]]
    ctx._audit("list_dir", alias, "ok")
    return f"{len(names)} entries:\n" + "\n".join(names)


def read_text_file(ctx: ToolContext, alias: str, relpath: str) -> str:
    if not isinstance(alias, str) or alias not in ctx.folders:
        ctx._audit("read_text_file", str(alias)[:40], "denied-not-allowlisted")
        raise ToolError(f"{alias!r} is not in the folders allowlist.")
    try:
        target = pathguard.check_subpath(ctx.folders[alias], relpath)
    except pathguard.PathOutsideAllowlist as exc:
        ctx._audit("read_text_file", alias, f"denied:{type(exc).__name__}")
        raise ToolError(f"refused: {exc}") from exc
    if not target.is_file():
        ctx._audit("read_text_file", alias, "failed:not-a-file")
        raise ToolError(f"{relpath!r} is not a file inside {alias}.")
    if target.suffix.lower() not in TEXT_EXTENSIONS:
        ctx._audit("read_text_file", alias, "denied:extension")
        raise ToolError(f"extension {target.suffix!r} is not allowed; allowed: "
                        f"{', '.join(TEXT_EXTENSIONS)}.")
    size = target.stat().st_size
    if size > MAX_TEXT_BYTES:
        ctx._audit("read_text_file", alias, "denied:too-large")
        raise ToolError(f"file is {size} bytes; limit is {MAX_TEXT_BYTES}.")
    raw = target.read_bytes()
    if b"\x00" in raw:
        ctx._audit("read_text_file", alias, "denied:binary")
        raise ToolError("file looks binary (NUL byte); refusing.")
    ctx._audit("read_text_file", alias, "ok")
    return raw.decode("utf-8", errors="replace")


def focus_window(ctx: ToolContext, title: str) -> str:
    if not isinstance(title, str) or not title.strip():
        raise ToolError("window title must be a non-empty string.")
    window = _allowlisted_window(ctx, title)
    if window is None:
        ctx._audit("focus_window", title[:40], "denied-not-allowlisted")
        raise ToolError(f"no window titled like {title!r} belongs to an "
                        "allowlisted app.")
    try:
        window.set_focus()
    except Exception as exc:
        ctx._audit("focus_window", title[:40], f"failed:{type(exc).__name__}")
        raise ToolError(f"could not focus {title!r}: {exc}") from exc
    ctx._audit("focus_window", title[:40], "ok")
    return f"focused window matching {title!r}"


def uia_click(ctx: ToolContext, window_title: str, control_name: str) -> str:
    window = _allowlisted_window(ctx, window_title)
    if window is None:
        ctx._audit("uia_click", f"{window_title[:20]}:{control_name[:20]}",
                   "denied-not-allowlisted")
        raise ToolError(f"no allowlisted window matches {window_title!r}.")
    try:
        ctrl = window.child_window(title=control_name)
        if not ctrl.exists(timeout=UIA_WAIT_SECONDS):
            ctrl = window.child_window(auto_id=control_name)
        if not ctrl.exists(timeout=UIA_WAIT_SECONDS):
            ctx._audit("uia_click", f"{window_title[:20]}:{control_name[:20]}",
                       "failed:not-found")
            raise ToolError(f"control {control_name!r} not found on {window_title!r}.")
        ctrl.wait("ready", timeout=UIA_WAIT_SECONDS)
        ctrl.click_input()
    except ToolError:
        raise
    except Exception as exc:
        ctx._audit("uia_click", f"{window_title[:20]}:{control_name[:20]}",
                   f"failed:{type(exc).__name__}")
        raise ToolError(f"click failed: {exc}") from exc
    ctx._audit("uia_click", f"{window_title[:20]}:{control_name[:20]}", "ok")
    return f"clicked {control_name!r} on {window_title!r}"


def uia_type(ctx: ToolContext, window_title: str, control_name: str, text) -> str:
    """Type into a control. Audit records ONLY the text length, never the text."""
    if not isinstance(text, str):
        raise ToolError("text to type must be a string.")
    subject = f"len={len(text)}"           # never the text itself
    window = _allowlisted_window(ctx, window_title)
    if window is None:
        ctx._audit("uia_type", subject, "denied-not-allowlisted")
        raise ToolError(f"no allowlisted window matches {window_title!r}.")
    try:
        ctrl = window.child_window(title=control_name, control_type="Edit")
        if not ctrl.exists(timeout=UIA_WAIT_SECONDS):
            ctrl = window.child_window(auto_id=control_name, control_type="Edit")
        if not ctrl.exists(timeout=UIA_WAIT_SECONDS):
            ctx._audit("uia_type", subject, "failed:not-found")
            raise ToolError(f"edit control {control_name!r} not found on "
                            f"{window_title!r}.")
        ctrl.wait("ready", timeout=UIA_WAIT_SECONDS)
        ctrl.set_edit_text(text)
    except ToolError:
        raise
    except Exception as exc:
        ctx._audit("uia_type", subject, f"failed:{type(exc).__name__}")
        raise ToolError(f"typing failed: {exc}") from exc
    ctx._audit("uia_type", subject, "ok")
    return f"typed {len(text)} characters into {control_name!r}"


# ---- MCP wiring -------------------------------------------------------------------

# name -> (function, description, property schemas, required, dangerous)
TOOL_TABLE = {
    "open_app": (open_app, "Launch an app by allowlisted alias (e.g. 'notepad').",
                 {"name": {"type": "string", "description": "app alias"}}, ["name"], False),
    "open_folder": (open_folder, "Open an allowlisted folder alias in Explorer.",
                    {"alias": {"type": "string", "description": "folder alias"}},
                    ["alias"], False),
    "list_dir": (list_dir, "List a folder inside an allowlisted alias.",
                 {"alias": {"type": "string"}, "subpath": {"type": "string"}},
                 ["alias", "subpath"], False),
    "read_text_file": (read_text_file, "Read a small text file inside an allowlisted alias.",
                       {"alias": {"type": "string"}, "relpath": {"type": "string"}},
                       ["alias", "relpath"], False),
    "focus_window": (focus_window, "Focus a window of an allowlisted app by title substring.",
                     {"title": {"type": "string"}}, ["title"], False),
    "uia_click": (uia_click, "Click a named control on an allowlisted window.",
                  {"window_title": {"type": "string"},
                   "control_name": {"type": "string"}},
                  ["window_title", "control_name"], False),
    "uia_type": (uia_type, "Type text into a named edit control on an allowlisted window.",
                 {"window_title": {"type": "string"}, "control_name": {"type": "string"},
                  "text": {"type": "string"}},
                 ["window_title", "control_name", "text"], False),
}

CAUGHT = (ToolError, pathguard.PathOutsideAllowlist, ConfigError, OSError, ValueError)


def build_mcp_server(audit=None):
    """Build the in-process MCP server. Returns (server, ctx)."""
    from claude_agent_sdk import create_sdk_mcp_server, tool

    config = load_config()
    ctx = ToolContext(config, audit=audit)
    sync_impls = {name: spec[0] for name, spec in TOOL_TABLE.items()}

    def make_handler(name, dangerous):
        async def handler(args):
            if dangerous and _deny_danger(ctx, "danger"):
                return {"content": [{"type": "text",
                                     "text": "DENIED: owner confirmation unavailable."}],
                        "isError": True}
            try:
                result = sync_impls[name](ctx, **args)
            except CAUGHT as exc:
                ctx._audit(name, "error", type(exc).__name__)
                return {"content": [{"type": "text", "text": f"ERROR: {exc}"}],
                        "isError": True}
            return {"content": [{"type": "text", "text": wrap_result(result)}]}
        return handler

    mcp_tools = []
    for name, (_, description, properties, required, dangerous) in TOOL_TABLE.items():
        decorated = tool(
            name=name,
            description=description,
            input_schema={"type": "object", "properties": properties,
                          "required": required},
        )(make_handler(name, dangerous))
        mcp_tools.append(decorated)

    server = create_sdk_mcp_server(name="lya_desktop", version="1.0.0",
                                   tools=mcp_tools)
    return server, ctx
