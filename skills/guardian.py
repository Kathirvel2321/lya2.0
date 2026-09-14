"""LYA's conscience — the Ultron safety layer & security guardian.
================================================================
Responsibilities:
  1. Dangerous command screening and execution gating.
  2. Silent duress flag signaling, detection, and reset.
  3. Action audit logging (encrypted log file + person-scoped SQLite).
  4. Proactive safety feedback on high-risk operations.
"""
import datetime
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import vault
from storage import store

DANGEROUS = [
    "format", "del /", "rm -rf", "rmdir /", "rmdir /s", "shutdown", "reg delete",
    "diskpart", "cipher /w", "vssadmin delete", "bcdedit",
    "drop table", "drop database", "encodedcommand", "iex (new-object",
    "downloadstring", "invoke-expression", "net user", "net localgroup",
    "takeown", "icacls /grant"
]

_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DURESS_FILE = os.path.join(_DIR, "security", "duress_flag.lya")
ACTION_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lya_actions.log.lya")


def is_dangerous(command: str) -> bool:
    """Return True if command contains dangerous system disruption patterns."""
    if not command:
        return False
    low = command.lower()
    return any(d in low for d in DANGEROUS)


def guard(command: str, action, verified: bool = False):
    """Gated execution: dangerous commands require verified identity."""
    if not is_dangerous(command):
        res = action()
        log_action(command, allowed=True, actor="guest" if not verified else "owner", detail="standard command")
        return True, res
    if verified:
        res = action()
        log_action(command, allowed=True, actor="owner", detail="verified dangerous command executed")
        return True, f"Verified. {res}"
    log_action(command, allowed=False, actor="unverified", detail="blocked dangerous command")
    return False, "That is a dangerous command and requires verified administrator identity. Command blocked."


def correct_user(text: str) -> str | None:
    """Proactively warn user before destructive operations."""
    if not text:
        return None
    low = text.lower()
    notes = {
        "del ": "Heads up: that deletes files permanently. Sure you want it? Say 'confirm' to proceed.",
        "delete": "Heads up: that deletes things permanently. Sure you want it? Say 'confirm' to proceed.",
        "rmdir": "Heads up: that deletes directories permanently. Sure you want it? Say 'confirm' to proceed.",
        "rm -rf": "Heads up: that deletes directories permanently. Sure you want it? Say 'confirm' to proceed.",
        "shutdown": "You'll lose unsaved work. Say 'confirm' if you really mean it.",
        "format": "Formatting will erase data irreversibly. Command is blocked by default.",
        "reg delete": "Registry changes can destabilize Windows. Command is blocked by default.",
    }
    for k, msg in notes.items():
        if k in low:
            return msg
    return None


# ---------------- DURESS ALARM SUBSYSTEM ----------------

def raise_duress(who: str = "escalation", detail: str | None = None) -> bool:
    """Activate silent duress alarm without alerting the potential coercer."""
    data = {
        "active": True,
        "who": who,
        "t": time.time(),
        "detail": detail or "Duress phrase spoken during authentication challenge.",
    }
    try:
        os.makedirs(os.path.dirname(DURESS_FILE), exist_ok=True)
        with open(DURESS_FILE, "wb") as f:
            f.write(vault.encrypt(json.dumps(data).encode()))
        log_action("DURESS_ALARM_RAISED", allowed=True, actor=who, detail=data["detail"])
        return True
    except Exception as e:
        print(f"[LYA][GUARDIAN] Failed to record duress flag: {e}", file=sys.stderr)
        return False


def check_duress() -> tuple[bool, dict | None]:
    """Check whether a silent duress flag is currently active."""
    if not os.path.exists(DURESS_FILE):
        return False, None
    try:
        with open(DURESS_FILE, "rb") as f:
            data = json.loads(vault.decrypt(f.read()))
        return bool(data.get("active", False)), data
    except Exception as e:
        # Fails closed: corrupted or unreadable duress file is treated as alarm active
        return True, {"active": True, "error": f"corrupted duress flag: {e}"}


def clear_duress() -> bool:
    """Clear active duress alarm (administrator reset)."""
    try:
        if os.path.exists(DURESS_FILE):
            os.remove(DURESS_FILE)
        log_action("DURESS_ALARM_CLEARED", allowed=True, actor="owner", detail="Duress alarm reset")
        return True
    except Exception as e:
        print(f"[LYA][GUARDIAN] Failed to clear duress flag: {e}", file=sys.stderr)
        return False


# ---------------- ENCRYPTED AUDIT LOGGING ----------------

def log_action(cmd: str, allowed: bool, actor: str = "owner", detail: str = ""):
    """Record an audit event to both encrypted log file and person-scoped SQLite."""
    now_iso = datetime.datetime.now().isoformat()
    outcome_str = "ALLOWED" if allowed else "BLOCKED"

    # 1. SQLite structured audit log
    try:
        store.record_audit(action_type=cmd, outcome=f"{outcome_str}: {detail}" if detail else outcome_str, person_id=actor)
    except Exception:
        pass

    # 2. Encrypted action log file
    try:
        os.makedirs(os.path.dirname(ACTION_LOG_FILE), exist_ok=True)
        entry = f"{now_iso} | {outcome_str} | {actor} | {cmd} | {detail}\n"
        history = ""
        if os.path.exists(ACTION_LOG_FILE):
            try:
                with open(ACTION_LOG_FILE, "rb") as f:
                    history = vault.decrypt(f.read()).decode("utf-8", errors="replace")
            except Exception:
                history = "[PREVIOUS LOG CORRUPTED]\n"
        with open(ACTION_LOG_FILE, "wb") as f:
            f.write(vault.encrypt((history + entry).encode("utf-8")))
    except Exception as e:
        print(f"[LYA][GUARDIAN] Failed to write action log: {e}", file=sys.stderr)


def get_audit_log(limit: int = 50) -> list[dict]:
    """Retrieve recent decrypted audit entries in reverse chronological order."""
    try:
        events = store.list_audit_events(limit=limit)
        if events:
            return events
    except Exception:
        pass

    # Fallback to encrypted file
    if not os.path.exists(ACTION_LOG_FILE):
        return []
    try:
        with open(ACTION_LOG_FILE, "rb") as f:
            history = vault.decrypt(f.read()).decode("utf-8", errors="replace")
        lines = [l.strip() for l in history.splitlines() if l.strip()]
        out = []
        for line in lines[-limit:][::-1]:
            parts = line.split(" | ")
            if len(parts) >= 4:
                out.append({
                    "time": parts[0],
                    "outcome": parts[1],
                    "person_id": parts[2],
                    "action_type": parts[3],
                })
            else:
                out.append({"raw": line})
        return out
    except Exception:
        return []
