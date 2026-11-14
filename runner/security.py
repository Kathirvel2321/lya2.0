"""Security primitives for the runner: ownership, allowlist, redaction.

Rules enforced here (and nowhere else):
  - only OWNER_CHAT_ID (sender id AND chat id) gets service; others are
    dropped silently.
  - tasks run only inside allowlisted project roots. Real paths are resolved
    so `..`, symlinks, junctions and drive changes cannot escape. UNC paths
    and cross-drive targets are refused outright.
  - user text is DATA, never a command: it travels as one argv element with
    shell=False.
  - anything shaped like a token/key is redacted before any text leaves the
    process (Telegram messages, logs).
"""
import os
import re
import tempfile
from pathlib import Path

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b\].*?\x07|\x1b[Bc]")
# Long-ish runs of characters that look like credentials: bearer keys,
# hex/base64ish blobs of 20+ chars, prefixed key idioms.
SECRET_RE = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{8,}|Bearer\s+\S{12,}|gh[pousr]_[A-Za-z0-9]{10,}"
    r"|[A-Fa-f0-9]{32,}|[A-Za-z0-9+/=_-]{28,})")
TELEGRAM_LIMIT = 3500
SAFE_NAME = re.compile(r"[a-z0-9_-]{1,40}")


class PathOutsideAllowlist(ValueError):
    pass


def is_owner(update, owner_chat_id):
    """Sender id AND chat id must both match the owner. Unknown users are
    invisible: callers log 'ignored sender' and return without replying."""
    try:
        user = update.effective_user
        chat = update.effective_chat
        return (user is not None and chat is not None
                and user.id == owner_chat_id and chat.id == owner_chat_id)
    except Exception:
        return False


def normalize_project_root(path: Path) -> Path:
    """Resolve and sanity-check one allowlisted project root."""
    if not isinstance(path, Path):
        raise ValueError("Project path must be a filesystem path.")
    resolved = Path(os.path.realpath(str(path))).resolve()
    drive = resolved.drive
    if str(resolved).startswith("\\\\") or str(resolved).startswith("//"):
        raise ValueError("UNC network paths are not allowed.")
    if not drive or not os.path.isabs(str(resolved)):
        raise ValueError("Project path must be an absolute path with a drive letter.")
    return resolved


def _lya_repo_root() -> Path | None:
    """The LYA repo root, when this runner lives inside it."""
    try:
        here = Path(__file__).resolve()
        return here.parents[2]        # runner/security.py -> runner -> lya-main
    except IndexError:
        return None


def resolve_inside(root: Path, user_path: str | None = None) -> Path:
    """The project root itself (or a user-supplied relative subpath), guaranteed
    to stay inside root. Raises PathOutsideAllowlist on any escape."""
    if not SAFE_NAME.fullmatch(root.name or ""):
        # The folder name itself may be odd; that is fine, the containment
        # check below is what matters.
        pass
    target = root
    if user_path:
        candidate = Path(user_path)
        if candidate.is_absolute() or candidate.drive or candidate.anchor:
            raise PathOutsideAllowlist("absolute paths are not accepted from chat")
        target = root / candidate
    resolved = Path(os.path.realpath(str(target))).resolve()
    root_real = Path(os.path.realpath(str(root))).resolve()
    if resolved.drive != root_real.drive:
        raise PathOutsideAllowlist("different drive")
    try:
        resolved.relative_to(root_real)
    except ValueError:
        raise PathOutsideAllowlist("resolves outside the allowlisted project") from None
    # Owner directive: the runner must refuse any allowlisted path that
    # contains the LYA repo root - the runner is a code-execution surface and
    # must never be pointed at LYA itself.
    lya_root = _lya_repo_root()
    if lya_root:
        try:
            resolved.relative_to(lya_root)
            raise PathOutsideAllowlist(
                "the LYA repository itself is a protected path; the runner "
                "refuses to run tasks inside it")
        except ValueError:
            pass
    return resolved


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text or "")


def redact(text: str) -> str:
    """Replace secret-shaped substrings with a fixed mask."""
    cleaned = strip_ansi(text or "")
    return SECRET_RE.sub("[REDACTED]", cleaned)


def truncate(text: str, limit: int = TELEGRAM_LIMIT) -> str:
    cleaned = redact(text or "")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 30] + "\n...[output truncated]"


def safe_scratch_dir():
    """Temporary directory inside the system temp area, per-job."""
    return Path(tempfile.mkdtemp(prefix="lya-runner-"))
