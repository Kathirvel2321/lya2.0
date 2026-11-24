"""Read a small allowlist of LYA provider passwords from the Bitwarden CLI."""
import os
import shutil
import subprocess
import threading


_ITEMS = {
    "GROQ_API_KEY": "LYA GROQ_API_KEY",
    "OPENAI_API_KEY": "LYA OPENAI_API_KEY",
    "NVIDIA_API_KEY": "LYA NVIDIA_API_KEY",
}
_session = ""
_cache = {}
_lock = threading.RLock()


def _command():
    executable = shutil.which("bw")
    if executable:
        return [executable]
    script = shutil.which("bw.ps1")
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if script and shell:
        return [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", script]
    return []


def _run(args, *, session="", extra_env=None, timeout=15):
    command = _command()
    if not command:
        return ""
    env = os.environ.copy()
    env.pop("BW_SESSION", None)
    if session:
        env["BW_SESSION"] = session
    if extra_env:
        env.update(extra_env)
    options = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "timeout": timeout,
        "env": env,
    }
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run([*command, *args], **options)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def take_environment_session():
    """Adopt and remove a caller-provided session from this process environment."""
    session = os.environ.pop("BW_SESSION", "").strip()
    if session:
        set_session(session)
    return bool(session)


def status():
    """Return only the CLI's safe status label; never expose account metadata."""
    import json

    raw = _run(["status", "--nointeraction"], timeout=10)
    try:
        return json.loads(raw).get("status", "")
    except (TypeError, ValueError):
        return ""


def unlock(master_password):
    """Unlock the CLI without putting the password in argv, files, or logs."""
    if not master_password:
        return ""
    raw = _run(
        ["unlock", "--passwordenv", "LYA_BW_MASTER_PASSWORD", "--raw", "--nointeraction"],
        extra_env={"LYA_BW_MASTER_PASSWORD": master_password},
        timeout=60,
    )
    return raw.strip()


def set_session(session):
    global _session
    with _lock:
        _session = (session or "").strip()


def sync():
    """Pull the current encrypted vault before LYA reads any provider item."""
    with _lock:
        if not _session:
            return False
        command = _command()
        if not command:
            return False
        env = os.environ.copy()
        env.pop("BW_SESSION", None)
        env["BW_SESSION"] = _session
        options = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": 45,
            "env": env,
        }
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            return subprocess.run(
                [*command, "sync", "--nointeraction"], **options
            ).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False


def get_password(name):
    """Fetch only an allowlisted item's password, cached for this LYA process."""
    item = _ITEMS.get(name)
    if not item:
        return ""
    with _lock:
        if name in _cache:
            return _cache[name]
        if not _session:
            return ""
        raw = _run(
            ["get", "password", item, "--raw", "--nointeraction"],
            session=_session,
        )
        value = raw.rstrip("\r\n")
        if value:
            _cache[name] = value
        return value


def clear():
    """Forget the session and cached provider values when LYA exits."""
    global _session
    with _lock:
        _session = ""
        _cache.clear()
