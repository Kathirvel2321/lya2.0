"""LYA's Autonomous Resource Governor & System Health Watcher
=============================================================
Protects the user's laptop from resource strain:
  1. Process RAM working set monitoring (<100MB target, 150MB warning threshold).
  2. Battery & AC power status monitoring (low battery throttling).
  3. Disk free space tracking.
  4. Emergency Kill Switch (file-based zero-latency circuit breaker).
"""
import ctypes
import os
import shutil
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KILL_FILE = str(ROOT / "KILL_SWITCH")

_TARGET_RAM_MB = 100.0
_WARNING_RAM_MB = 150.0
_MIN_BATTERY_PCT = 10


def is_killed() -> bool:
    """Return True if emergency kill switch is engaged."""
    return os.path.exists(KILL_FILE)


def engage_kill_switch(reason: str = "User triggered emergency stop") -> str:
    """Engage emergency kill switch file, freezing autonomous tasks."""
    try:
        with open(KILL_FILE, "w", encoding="utf-8") as f:
            f.write(f"KILLED | {time.time()} | {reason}\n")
        try:
            from skills.guardian import log_action
            log_action("KILL_SWITCH_ENGAGED", allowed=True, actor="owner", detail=reason)
        except Exception:
            pass
        return "🛑 Emergency kill switch ENGAGED. Autonomous execution and worker tasks stopped."
    except Exception as e:
        return f"Could not engage kill switch: {e}"


def release_kill_switch() -> str:
    """Release emergency kill switch, restoring normal execution."""
    try:
        if os.path.exists(KILL_FILE):
            os.remove(KILL_FILE)
        try:
            from skills.guardian import log_action
            log_action("KILL_SWITCH_RELEASED", allowed=True, actor="owner", detail="Manual release")
        except Exception:
            pass
        return "✅ Emergency kill switch RELEASED. Normal operation restored."
    except Exception as e:
        return f"Could not release kill switch: {e}"


def get_process_memory_mb() -> float:
    """Return current process WorkingSetSize in Megabytes."""
    # Windows native via pywin32
    try:
        import win32process, win32api
        proc = win32api.GetCurrentProcess()
        info = win32process.GetProcessMemoryInfo(proc)
        return round(info.get("WorkingSetSize", 0) / (1024 * 1024), 2)
    except Exception:
        pass

    # Unix / Posix fallback
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)
    except Exception:
        return 0.0


def get_battery_status() -> dict:
    """Return battery percentage and AC line status on Windows without external packages."""
    if os.name == "nt":
        class _SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong),
                ("BatteryFullLifeTime", ctypes.c_ulong),
            ]
        try:
            status = _SYSTEM_POWER_STATUS()
            ok = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
            if ok:
                pct = int(status.BatteryLifePercent)
                # 255 indicates unknown battery status
                return {
                    "battery_pct": pct if 0 <= pct <= 100 else None,
                    "ac_online": status.ACLineStatus == 1,
                    "available": True,
                }
        except Exception:
            pass
    return {"battery_pct": None, "ac_online": True, "available": False}


def get_disk_free_gb(path: str = ".") -> float:
    """Return free disk space in Gigabytes."""
    try:
        usage = shutil.disk_usage(path)
        return round(usage.free / (1024 * 1024 * 1024), 2)
    except Exception:
        return 0.0


def get_health() -> dict:
    """Comprehensive health snapshot of LYA and host device."""
    ram_mb = get_process_memory_mb()
    bat = get_battery_status()
    disk_free = get_disk_free_gb()
    threads = threading.active_count()
    killed = is_killed()

    bat_pct = bat.get("battery_pct")
    ac_online = bat.get("ac_online", True)

    ram_warning = ram_mb > _WARNING_RAM_MB
    battery_warning = (bat_pct is not None) and (bat_pct < _MIN_BATTERY_PCT) and (not ac_online)

    ok = (not killed) and (not ram_warning) and (not battery_warning)

    messages = []
    if killed:
        messages.append("EMERGENCY KILL SWITCH ENGAGED")
    if ram_warning:
        messages.append(f"High RAM: {ram_mb} MB (exceeds {_WARNING_RAM_MB} MB limit)")
    if battery_warning:
        messages.append(f"Low battery: {bat_pct}% (on battery power)")
    if not messages:
        messages.append("Optimal health. Zero device strain.")

    return {
        "ok": ok,
        "killed": killed,
        "ram_mb": ram_mb,
        "ram_warning": ram_warning,
        "battery_pct": bat_pct,
        "battery_warning": battery_warning,
        "ac_online": ac_online,
        "disk_free_gb": disk_free,
        "threads": threads,
        "status_message": "; ".join(messages),
    }


def format_health_report() -> str:
    """Return human-readable system status report for assistant reply."""
    h = get_health()
    bat_str = f"{h['battery_pct']}% {'(Charging / AC)' if h['ac_online'] else '(On Battery)'}" if h['battery_pct'] is not None else "AC Desktop"
    status_icon = "🛑" if h["killed"] else ("⚠️" if not h["ok"] else "💚")

    lines = [
        f"{status_icon} SYSTEM HEALTH & RESOURCE GOVERNOR",
        f"  • Status: {h['status_message']}",
        f"  • RAM Footprint: {h['ram_mb']} MB (target: <100 MB)",
        f"  • Battery Power: {bat_str}",
        f"  • Disk Free: {h['disk_free_gb']} GB",
        f"  • Active Threads: {h['threads']}",
        f"  • Kill Switch: {'ACTIVE (Blocked)' if h['killed'] else 'Disengaged'}",
    ]
    return "\n".join(lines)
