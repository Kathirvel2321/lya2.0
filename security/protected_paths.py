"""Protected paths - the do-not-touch list.

The gate, any code-change feature, and the runner must refuse to modify
anything under these paths. Changed only manually by the owner through git.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROTECTED_RELATIVE = (
    "security/",
    "runner/",
    "tests/",
    "brain/admin_recognizer.py",
    "bridge/gate.py",
    "skills/forge.py",
)


def is_protected(path) -> bool:
    """True if `path` falls under a protected module or folder."""
    try:
        resolved = Path(path).resolve()
    except (OSError, ValueError):
        return True          # unresolvable = treat as protected (fail closed)
    root = ROOT.resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError:
        return False         # outside the repo is not LYA's responsibility
    as_posix = rel.as_posix()
    for entry in PROTECTED_RELATIVE:
        entry = entry.rstrip("/")
        if as_posix == entry:
            return True
        if as_posix.startswith(entry + "/"):
            return True
        if "/" not in entry and entry.endswith(".py") is False and \
                rel.parts and rel.parts[0] == entry:
            return True      # folder entry like "security" matching "security/x.py"
    return False


def guard_write(target_path, source="unnamed"):
    """Raise PermissionError if target_path is protected. Call before any
    file write that originates from model-directed or automated flow."""
    if is_protected(target_path):
        raise PermissionError(
            f"{source} refuses to modify a protected path: {Path(target_path).name}. "
            "Security modules are changed only manually by the owner through git.")
