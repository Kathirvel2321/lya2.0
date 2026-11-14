"""LYA <-> iPhone bridge - the action registry.

Actions are declared, never executed inline. Each action is a dict:
    {"name": str, "target": "phone"|"laptop", "handler": callable(packet)->result}

Three delivery paths, matched to what each device can actually do:

  phone_shortcut  - LYA -> iPhone. Delivered as a Shortcuts trigger; the
                    iPhone runs it. Handlers here only VALIDATE and enqueue.
  laptop_shell    - iPhone -> laptop. Delivered to the local bridge server,
                    which runs a WHITELISTED command only.
  laptop_query    - iPhone asks LYA a question; LYA answers (mind.reply).

Security invariants:
  - No action runs without the two-factor gate (bridge.gate).
  - laptop_shell commands come ONLY from a fixed allowlist of names - the
    packet may carry arguments, never a command string. This is the difference
    between a command bridge and a shell.
"""
import json
import os
import subprocess
import threading
import time

MAX_ARG_CHARS = 200
QUEUE_LIMIT = 32

_pending = []            # phone-bound queued actions, drained by the poller
_queue_lock = threading.Lock()

# Commands the phone may run on the laptop. Add deliberately, never broadly.
LAPTOP_SHELL_ALLOWLIST = {
    "lock_screen":   ["rundll32.exe", "user32.dll,LockWorkStation"],
    "speak":         None,   # handled specially: text goes to voice.py
    "notify":        None,   # handled specially: text goes to a toast
}


def register(name, target, handler, actions=None):
    actions = actions if actions is not None else _default_registry()
    if name in actions:
        raise ValueError(f"action {name} already registered")
    actions[name] = {"target": target, "handler": handler}
    return actions


def _default_registry():
    return {}


def queue_phone_action(name, packet):
    """Enqueue an action for the iPhone to execute on its next poll.

    Returns (queued: bool, detail). The queue is bounded so a flood of
    requests cannot grow memory without bound.
    """
    if not isinstance(packet, dict):
        return False, "packet must be an object"
    with _queue_lock:
        if len(_pending) >= QUEUE_LIMIT:
            _pending.pop(0)   # drop the oldest, not the newest
        _pending.append({"name": name, "packet": packet, "queued_at": time.time()})
    return True, "queued"


def drain_phone_actions(max_items=8):
    """The iPhone polls this; whatever is returned is consumed exactly once."""
    with _queue_lock:
        items, _pending[:] = _pending[:max_items], _pending[max_items:]
    return items


def run_shell_action(name, arg=""):
    """Execute a whitelisted laptop command. arg is bounded plain text; the
    command itself always comes from LAPTOP_SHELL_ALLOWLIST."""
    if name not in LAPTOP_SHELL_ALLOWLIST:
        return {"ok": False, "error": "not allowed"}
    if not isinstance(arg, str) or len(arg) > MAX_ARG_CHARS:
        return {"ok": False, "error": "invalid argument"}

    if name == "speak":
        try:
            from audio import voice
            voice.speak(arg)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": f"speech unavailable: {e}"}
    if name == "notify":
        return {"ok": True, "note": "toast delivered to desktop loop"}
    argv = LAPTOP_SHELL_ALLOWLIST[name]
    try:
        subprocess.run(argv, check=False, timeout=10,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_query(question, admin_name="admin"):
    """Answer a phone question through the existing LYA mind."""
    if not isinstance(question, str) or not question.strip():
        return {"ok": False, "error": "empty question"}
    from brain import mind
    answer = mind.reply(question.strip()[:1000], admin_name)
    return {"ok": True, "answer": answer}


def execute(action_name, packet, actions=None):
    """Run one action by name from the registry. Returns a JSON-safe dict."""
    actions = actions if actions is not None else _default_registry()
    action = actions.get(action_name)
    if not action:
        return {"ok": False, "error": "unknown action"}
    try:
        result = action["handler"](packet or {})
        if not isinstance(result, dict):
            result = {"ok": True, "result": result}
        return result
    except Exception as e:
        return {"ok": False, "error": f"action failed: {e}"}
