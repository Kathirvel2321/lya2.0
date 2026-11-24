"""lya_agent configuration.

Loads allowlists from lya_agent.local.json (gitignored, next to this module's
package root's parent - i.e. the LYA repo root is NOT used; the file lives in
this folder's parent so the agent works from any cwd, but by default it is
looked up relative to the repository root so the runner's cwd (the project
root) also resolves).

Shape:
  {
    "apps":  {"notepad": "C:/Windows/System32/notepad.exe"},
    "folders": {"docs": "C:/Users/me/Documents"}
  }

Every alias must match SAFE_NAME; every path must be absolute with a drive,
non-UNC, and must not point at the LYA repo itself (owner directive, same as
runner/security.resolve_inside).
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger("lya_agent.config")

SAFE_NAME = re.compile(r"[a-z0-9_-]{1,40}")
TEXT_EXTENSIONS = (".txt", ".md", ".json", ".py", ".csv")
MAX_TEXT_BYTES = 200 * 1024


class ConfigError(RuntimeError):
    pass


def _candidate_paths() -> list[Path]:
    """Where lya_agent.local.json may live. First existing one wins."""
    here = Path(__file__).resolve().parent
    repo = here.parent                       # lya-main root when run in-tree
    return [here / "lya_agent.local.json", repo / "lya_agent.local.json"]


def _lya_repo_root() -> Path | None:
    here = Path(__file__).resolve().parent
    return here.parent


def _validate_root(name: str, kind: str, raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigError(f"{kind} alias {name!r}: path must be a non-empty string.")
    resolved = Path(os.path.realpath(raw)).resolve()
    if str(resolved).startswith("\\\\") or str(resolved).startswith("//"):
        raise ConfigError(f"{kind} alias {name!r}: UNC paths are not allowed.")
    if not resolved.drive or not os.path.isabs(str(resolved)):
        raise ConfigError(f"{kind} alias {name!r}: needs an absolute path with a drive letter.")
    lya_root = _lya_repo_root()
    if lya_root:
        try:
            resolved.relative_to(lya_root)
        except ValueError:
            pass
        else:
            raise ConfigError(
                f"{kind} alias {name!r}: the LYA repository itself is a protected path.")
    return resolved


def load_config() -> dict[str, dict[str, Path]]:
    """Load and validate both allowlists. Raises ConfigError on any problem.

    Returns {"apps": {...}, "folders": {...}} with resolved Path values.
    """
    candidates = _candidate_paths()
    local = next((p for p in candidates if p.is_file()), None)
    if local is None:
        raise ConfigError(
            "lya_agent.local.json is missing. Copy "
            "lya_agent/lya_agent.local.example.json to lya_agent.local.json "
            "and fill in real values.")
    try:
        data = json.loads(local.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ConfigError("lya_agent.local.json is malformed JSON.") from exc
    if not isinstance(data, dict):
        raise ConfigError("lya_agent.local.json must contain a JSON object.")

    out: dict[str, dict[str, Path]] = {}
    for kind in ("apps", "folders"):
        raw = data.get(kind)
        if not isinstance(raw, dict) or not raw:
            raise ConfigError(f"lya_agent.local.json: {kind!r} must be a non-empty object.")
        table: dict[str, Path] = {}
        for name, value in raw.items():
            if not isinstance(name, str) or not SAFE_NAME.fullmatch(name):
                raise ConfigError(f"{kind} alias {name!r} must match [a-z0-9_-]{{1,40}}.")
            table[name] = _validate_root(name, kind, value if kind == "folders" else str(value))
        out[kind] = table
    log.info("lya_agent config loaded: %d apps, %d folders",
             len(out["apps"]), len(out["folders"]))
    return out
