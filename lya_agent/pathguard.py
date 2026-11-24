"""Safe path resolution for the LYA agent.

Every folder alias maps to an absolute root. A subpath is only accepted when
it resolves to a location strictly inside that root. Rejects: absolute
subpaths, "..", drive changes, UNC paths, symlinks/junctions that escape the
root, alternate data streams, and reserved Windows device names.
"""
from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

import logging

logger = logging.getLogger("lya_agent.pathguard")

# Reserved device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9).
_RESERVED = re.compile(
    r"^(?:(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?)$", re.IGNORECASE)


class PathOutsideAllowlist(ValueError):
    pass


def _check_no_ads(name: str) -> None:
    """Alternate data streams: 'file.txt:stream' names a hidden stream.
    A single colon is only ever legal as a drive separator, which cannot
    appear inside a relative subpath (drives are rejected earlier)."""
    if ":" in name:
        raise PathOutsideAllowlist("alternate data streams are not allowed")


def _check_reserved(rel: PureWindowsPath) -> None:
    for part in rel.parts:
        if _RESERVED.match(part):
            raise PathOutsideAllowlist("reserved device name is not allowed")


def check_subpath(root: Path, subpath: str) -> Path:
    """Resolve subpath against root and prove containment. Returns the
    resolved path. Raises PathOutsideAllowlist on any escape."""
    if not isinstance(subpath, str) or not subpath.strip():
        raise PathOutsideAllowlist("subpath must be a non-empty string")
    rel = PureWindowsPath(subpath)
    if rel.is_absolute() or rel.drive or rel.root:
        raise PathOutsideAllowlist("absolute subpaths are not accepted")
    _check_reserved(rel)
    for part in rel.parts:
        if part == "..":
            raise PathOutsideAllowlist("'..' is not allowed")
        _check_no_ads(part)
    root_real = Path(root).resolve()
    if str(root_real).startswith("\\\\") or str(root_real).startswith("//"):
        raise PathOutsideAllowlist("UNC roots are not allowed")
    if not root_real.drive or not root_real.is_absolute():
        raise PathOutsideAllowlist("the root must be an absolute path with a drive")
    target = (root / rel).resolve(strict=False)
    # Symlinks/junctions that escape the root are caught by the resolved
    # containment check below; drive change is caught too.
    if target.drive != root_real.drive:
        raise PathOutsideAllowlist("drive change is not allowed")
    if str(target).startswith("\\\\") or str(target).startswith("//"):
        raise PathOutsideAllowlist("UNC paths are not allowed")
    if not target.is_relative_to(root_real):
        raise PathOutsideAllowlist("resolves outside the allowlisted root")
    return target


def check_root(root: str) -> Path:
    """Validate one allowlisted root itself. Returns the resolved path."""
    resolved = Path(root).resolve(strict=False)
    if str(resolved).startswith("\\\\") or str(resolved).startswith("//"):
        raise PathOutsideAllowlist("UNC roots are not allowed")
    if not resolved.drive or not resolved.is_absolute():
        raise PathOutsideAllowlist("roots must be absolute paths with a drive")
    if any(part == ".." for part in PureWindowsPath(root).parts):
        raise PathOutsideAllowlist("'..' is not allowed in roots")
    return resolved
