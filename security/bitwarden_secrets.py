"""Access LYA's provider items through the Bitwarden CLI."""
import base64
import json
import os
import shutil
import subprocess
import threading
from uuid import UUID


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


def _run(args, *, session="", extra_env=None, timeout=15, stdin=None):
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
    if stdin is not None:
        options["input"] = stdin
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
        session = (session or "").strip()
        if _session != session:
            _cache.clear()
            _session = session


def has_session():
    return bool(_session)


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


def save_nvidia_key(value, *, authorized):
    """Save one approved NVIDIA credential. CLI responses never leave this adapter."""
    if not value or len(value) > 2048 or any(char.isspace() or not char.isprintable() for char in value):
        return 'Enter a valid NVIDIA API key.'
    name = 'NVIDIA_API_KEY'
    title = _ITEMS[name]
    with _lock:
        if not authorized():
            return 'The phone approval expired or was cancelled.'
        if not _session or not sync():
            return 'Unlock Bitwarden in the LYA launcher and check that the vault can sync.'
        try:
            records = json.loads(_run(['list', 'items', '--search', title, '--nointeraction'], session=_session))
            if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
                raise ValueError
            matches = [item for item in records if item.get('name') == title]
            if len(matches) > 1:
                return 'More than one NVIDIA item has the same title. Resolve the duplicates in Bitwarden first.'
            if matches:
                item = matches[0]
                if (item.get('type') != 1 or item.get('organizationId') or item.get('deletedDate')
                        or not isinstance(item.get('login'), dict)):
                    return 'Use a personal Bitwarden Login item for NVIDIA.'
                item_id = str(UUID(item['id']))
                command = ['edit', 'item', item_id]
            else:
                item = json.loads(_run(['get', 'template', 'item', '--nointeraction'], session=_session))
                login = json.loads(_run(['get', 'template', 'item.login', '--nointeraction'], session=_session))
                item.update(name=title, type=1, login=login)
                command = ['create', 'item']
            item['login']['password'] = value
            payload = base64.b64encode(json.dumps(item).encode('utf-8')).decode('ascii')
        except (AttributeError, KeyError, TypeError, ValueError):
            return 'LYA could not prepare the NVIDIA item in Bitwarden.'
        if not authorized():
            return 'The phone approval expired or was cancelled.'
        _cache.pop(name, None)
        raw = _run([*command, '--nointeraction'], session=_session, stdin=payload, timeout=30)
        try:
            saved = json.loads(raw)
            if (saved['name'] == title and saved['type'] == 1 and saved['login']['password'] == value
                    and (not matches or saved['id'] == item_id)):
                _cache[name] = value
                return 'NVIDIA API key saved in Bitwarden.'
        except (KeyError, TypeError, ValueError):
            pass
        return 'LYA could not confirm the save. Check the NVIDIA item in Bitwarden before retrying.'


def clear():
    """Forget the session and cached provider values when LYA exits."""
    global _session
    with _lock:
        _session = ""
        _cache.clear()
