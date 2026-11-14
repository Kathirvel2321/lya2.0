"""
Laptop Listener Service for phone-command module.
Windows laptop, Python 3.11+.
No paid services. No raw shell execution anywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import urlsplit

from dotenv import load_dotenv
import mss
import mss.tools
from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Setup & Logging (Console + RotatingFileHandler 1MB, 3 backups)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "listener.log"

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler],
)
logger = logging.getLogger("phone_command_listener")

load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
CONFIG_PATH = BASE_DIR / "config.json"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY is missing in .env.")
    sys.exit(1)

# Initialize Supabase client with the service role key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# Single-Instance Lock
# ---------------------------------------------------------------------------
def acquire_instance_lock():
    """Acquires a single-instance lock file. Exits if already running."""
    lock_path = BASE_DIR / "listener.lock"
    try:
        lock_file = open(lock_path, "a+")
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_file
    except (OSError, IOError):
        logger.error("Another instance of phone-command listener is already running. Exiting.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Retry with Backoff Helper
# ---------------------------------------------------------------------------
def retry_with_backoff(operation_name: str, func, *args, **kwargs) -> None:
    """Retries a function with backoff (2s, 4s, up to 30s) until it succeeds."""
    delay = 2.0
    while True:
        try:
            func(*args, **kwargs)
            return
        except Exception as e:
            logger.warning(
                "Operation '%s' failed: %s. Retrying in %.1fs...",
                operation_name,
                e,
                delay,
            )
            time.sleep(delay)
            delay = min(delay * 2.0, 30.0)


# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------
def load_config() -> dict[str, dict[str, str]]:
    if not CONFIG_PATH.exists():
        logger.warning("config.json not found. Using empty allowances.")
        return {"apps": {}, "sites": {}, "scripts": {}}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "apps": data.get("apps", {}),
            "sites": data.get("sites", {}),
            "scripts": data.get("scripts", {}),
        }
    except Exception as e:
        logger.error("Failed to parse config.json: %s", e)
        return {"apps": {}, "sites": {}, "scripts": {}}


# ---------------------------------------------------------------------------
# Allowed Actions Publisher
# ---------------------------------------------------------------------------
def publish_allowed_actions(config: dict[str, dict[str, str]]) -> None:
    """Publishes available actions into allowed_actions table on startup/periodically."""
    actions = [
        {"id": "ping", "category": "system", "label": "Ping Laptop"},
        {"id": "screenshot", "category": "system", "label": "Take Screenshot"},
    ]
    for name in config.get("apps", {}).keys():
        actions.append({
            "id": f"open_app:{name}",
            "category": "apps",
            "label": f"Open {name.capitalize()}",
        })
    for name in config.get("sites", {}).keys():
        actions.append({
            "id": f"open_site:{name}",
            "category": "sites",
            "label": f"Visit {name.capitalize()}",
        })
    for name in config.get("scripts", {}).keys():
        actions.append({
            "id": f"run_script:{name}",
            "category": "scripts",
            "label": f"Run {name.capitalize()}",
        })

    supabase.table("allowed_actions").delete().neq("id", "none").execute()
    now_iso = datetime.now(timezone.utc).isoformat()
    for item in actions:
        item["updated_at"] = now_iso
    supabase.table("allowed_actions").upsert(actions).execute()
    logger.info("Published %d allowed action(s) to allowed_actions table.", len(actions))


# ---------------------------------------------------------------------------
# Startup Reconciliation & Storage Cleanup
# ---------------------------------------------------------------------------
def reconcile_interrupted_commands() -> None:
    """On startup, set any running rows to failed: interrupted, with a log entry."""
    res = supabase.table("commands").select("*").eq("status", "running").execute()
    running_commands = res.data or []
    now_iso = datetime.now(timezone.utc).isoformat()
    for cmd in running_commands:
        cmd_id = str(cmd.get("id"))
        action = str(cmd.get("action", ""))
        supabase.table("commands").update({
            "status": "failed: interrupted",
            "result": "Process terminated while command was running",
            "finished_at": now_iso,
        }).eq("id", cmd_id).execute()

        supabase.table("command_log").insert({
            "command_id": cmd_id,
            "action": action,
            "status": "failed: interrupted",
            "timestamp": now_iso,
        }).execute()
        logger.info("Marked previously running command %s as 'failed: interrupted'", cmd_id)


def cleanup_old_screenshots() -> None:
    """Deletes screenshots older than 60 minutes from private storage."""
    try:
        files = supabase.storage.from_("screenshots").list()
        if not files or not isinstance(files, list):
            return
        now = datetime.now(timezone.utc)
        to_delete = []
        for f in files:
            name = f.get("name")
            if not name or name == ".emptyFolderPlaceholder":
                continue
            created_str = f.get("created_at") or f.get("updated_at")
            if created_str:
                try:
                    dt = datetime.fromisoformat(str(created_str).replace("Z", "+00:00"))
                    if (now - dt).total_seconds() > 3600:
                        to_delete.append(name)
                except Exception:
                    pass
        if to_delete:
            supabase.storage.from_("screenshots").remove(to_delete)
            logger.info("Cleaned up %d old screenshot(s): %s", len(to_delete), to_delete)
    except Exception as e:
        logger.warning("Failed screenshot cleanup: %s", e)


# ---------------------------------------------------------------------------
# Command Execution Logic
# ---------------------------------------------------------------------------
def update_command_status(command_id: str, action: str, status: str, result: str | None) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        supabase.table("commands").update({
            "status": status,
            "result": result,
            "finished_at": now_iso,
        }).eq("id", command_id).execute()

        supabase.table("command_log").insert({
            "command_id": command_id,
            "action": action,
            "status": status,
            "timestamp": now_iso,
        }).execute()
        logger.info("Command %s updated: status=%s", command_id, status)
    except Exception as e:
        logger.error("Failed to update status for command %s: %s", command_id, e)


def execute_action(action: str, config: dict[str, dict[str, str]]) -> tuple[str, str]:
    """
    Executes the action strictly looking up in config.
    Returns: (status, result)
    """
    # 1. Ping
    if action == "ping":
        return "done", f"pong from {os.environ.get('COMPUTERNAME', 'Windows Laptop')}"

    # 2. Screenshot (Direct memory bytes with mss, no temp file)
    if action == "screenshot":
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                img = sct.grab(monitor)
                png_bytes = mss.tools.to_png(img.rgb, img.size)

            filename = f"screenshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}.png"

            supabase.storage.from_("screenshots").upload(
                path=filename,
                file=png_bytes,
                file_options={"content-type": "image/png"},
            )
            return "done", filename
        except Exception as e:
            logger.error("Screenshot capture or upload failed: %s", e)
            return "failed", f"screenshot failed: {str(e)[:300]}"

    # 3. open_app:<name>
    if action.startswith("open_app:"):
        app_name = action.split(":", 1)[1].strip()
        app_path = config.get("apps", {}).get(app_name)
        if not app_path or not Path(app_path).exists():
            return "rejected: not allowed", f"app '{app_name}' not configured or path does not exist"
        try:
            # shell=False - no raw shell execution
            subprocess.Popen([str(Path(app_path).resolve())], shell=False)
            return "done", f"launched app: {app_name}"
        except Exception as e:
            return "failed", f"failed to open app {app_name}: {str(e)[:300]}"

    # 4. open_site:<name>
    if action.startswith("open_site:"):
        site_name = action.split(":", 1)[1].strip()
        site_url = config.get("sites", {}).get(site_name)
        if not site_url:
            return "rejected: not allowed", f"site '{site_name}' not in allowed config"
        parsed = urlsplit(site_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return "rejected: not allowed", "invalid url scheme"
        try:
            if sys.platform == "win32":
                os.startfile(site_url)
            else:
                import webbrowser
                webbrowser.open(site_url)
            return "done", f"opened site: {site_url}"
        except Exception as e:
            return "failed", f"failed to open site {site_name}: {str(e)[:300]}"

    # 5. run_script:<name> (Only .exe, .bat, and .cmd extensions accepted)
    if action.startswith("run_script:"):
        script_name = action.split(":", 1)[1].strip()
        script_path_str = config.get("scripts", {}).get(script_name)
        if not script_path_str:
            return "rejected: not allowed", f"script '{script_name}' not configured"

        path = Path(script_path_str)
        allowed_extensions = {".exe", ".bat", ".cmd"}
        if path.suffix.lower() not in allowed_extensions:
            return "rejected: not allowed", f"script extension '{path.suffix}' not allowed (must be .exe, .bat, or .cmd)"

        if not path.exists():
            return "rejected: not allowed", f"script '{script_name}' path does not exist"

        try:
            # shell=False, timeout=30
            proc = subprocess.run(
                [str(path.resolve())],
                shell=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            raw_output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
            truncated_output = raw_output.strip()[:2000]
            status = "done" if proc.returncode == 0 else "failed"
            return status, truncated_output or f"Process exited with code {proc.returncode}"
        except subprocess.TimeoutExpired:
            return "failed", "execution timed out (30s limit)"
        except Exception as e:
            return "failed", f"script execution error: {str(e)[:300]}"

    # Any other action
    return "rejected: not allowed", f"unrecognized action: {action}"


# ---------------------------------------------------------------------------
# Polling Worker Loop (2-second interval, RPC claim)
# ---------------------------------------------------------------------------
def poll_and_execute_command(config: dict[str, dict[str, str]]) -> bool:
    """
    Calls claim_next_command RPC to atomically claim the next pending command.
    Returns True if a command was claimed and processed, False if queue was empty.
    """
    try:
        res = supabase.rpc("claim_next_command").execute()
        rows = res.data
        if not rows:
            return False

        cmd = rows[0] if isinstance(rows, list) else rows
        if not isinstance(cmd, dict) or not cmd.get("id"):
            return False

        command_id = str(cmd["id"])
        action = str(cmd.get("action", ""))
        status = str(cmd.get("status", ""))

        logger.info("Claimed command %s: action=%s, status=%s", command_id, action, status)

        # If the row was already marked rejected: expired by claim_next_command, write log entry and skip execution
        if status == "rejected: expired":
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                supabase.table("command_log").insert({
                    "command_id": command_id,
                    "action": action,
                    "status": status,
                    "timestamp": now_iso,
                }).execute()
                logger.info("Recorded audit log for expired command %s", command_id)
            except Exception as e:
                logger.error("Failed to insert log for expired command %s: %s", command_id, e)
            return True

        # Execute action (client-side timestamp checks removed)
        new_status, result = execute_action(action, config)
        update_command_status(command_id, action, new_status, result)
        return True
    except Exception as e:
        logger.error("Error calling claim_next_command RPC: %s", e)
        return False


def main() -> None:
    # Single-instance lock
    _lock_handle = acquire_instance_lock()

    logger.info("Starting LYA Phone-Command Listener on Windows...")
    config = load_config()

    # Retry startup routines with backoff (2s, 4s, up to 30s) until they succeed
    retry_with_backoff("publish_allowed_actions", publish_allowed_actions, config)
    retry_with_backoff("reconcile_interrupted_commands", reconcile_interrupted_commands)

    # Initial cleanup on startup
    cleanup_old_screenshots()
    last_periodic_monotonic = time.monotonic()

    logger.info("Listener is active. Polling interval: 2.0s.")
    try:
        while True:
            current_config = load_config()
            # Drain any pending commands returned by claim_next_command
            while poll_and_execute_command(current_config):
                pass

            # Cleanup old screenshots and re-publish allowed actions every 10 minutes (600s)
            if time.monotonic() - last_periodic_monotonic >= 600.0:
                cleanup_old_screenshots()
                retry_with_backoff("publish_allowed_actions", publish_allowed_actions, current_config)
                last_periodic_monotonic = time.monotonic()

            time.sleep(2.0)
    except KeyboardInterrupt:
        logger.info("Listener shutting down gracefully.")


if __name__ == "__main__":
    main()
