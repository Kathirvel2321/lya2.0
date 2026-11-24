"""Kill switch for the LYA agent loop.

Two stop mechanisms, both writing/existing as the same file (data/LYA_KILL):
  1. The owner creates the file manually.
  2. The global hotkey Ctrl+Alt+Shift+K creates it, via ctypes
     RegisterHotKey in a daemon thread (no extra dependency).

stopped() is checked before EVERY agent step. stop() always terminates
promptly and cleanly; the loop never hangs.
"""
from __future__ import annotations

import ctypes
import logging
import threading
from pathlib import Path

logger = logging.getLogger("lya_agent.killswitch")

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_K = 0x4B
WM_HOTKEY = 0x0312
HOTKEY_ID = 0xB007


class KillSwitch:
    def __init__(self, flag_path: Path):
        self.flag_path = Path(flag_path)
        self._stop_reason: str | None = None
        self._lock = threading.Lock()
        self._hotkey_thread: threading.Thread | None = None

    # ---- state -----------------------------------------------------------
    def stopped(self) -> bool:
        """True when the flag file exists OR the hotkey thread signalled."""
        with self._lock:
            if self._stop_reason is not None:
                return True
        return self.flag_path.exists()

    def reason(self) -> str:
        with self._lock:
            if self._stop_reason:
                return self._stop_reason
        return "kill flag file exists" if self.flag_path.exists() else ""

    def request_stop(self, reason: str) -> None:
        """Called by the hotkey thread. Also writes the flag file so other
        processes see the stop."""
        with self._lock:
            if self._stop_reason is None:
                self._stop_reason = reason
        try:
            self.flag_path.parent.mkdir(parents=True, exist_ok=True)
            self.flag_path.write_text(reason, encoding="utf-8")
        except OSError as exc:
            logger.warning("could not write kill flag: %s", exc)

    def clear(self) -> None:
        """Remove the flag (owner decides to continue)."""
        try:
            self.flag_path.unlink(missing_ok=True)
        except OSError:
            pass
        with self._lock:
            self._stop_reason = None

    # ---- hotkey ------------------------------------------------------------
    def start_hotkey(self) -> None:
        """Install Ctrl+Alt+Shift+K as a global hotkey in a daemon thread."""
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_loop, name="lya-kill-hotkey", daemon=True)
        self._hotkey_thread.start()

    def _hotkey_loop(self) -> None:
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID,
                                     MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_K):
            logger.warning("global hotkey could not be registered; the flag "
                           "file remains the stop mechanism")
            return
        msg = ctypes.wintypes.MSG() if hasattr(ctypes, "wintypes") else None
        from ctypes import wintypes  # local import: ctypes.wintypes on win only
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                logger.info("kill hotkey pressed")
                self.request_stop("kill hotkey Ctrl+Alt+Shift+K pressed")
                # Do not break the loop immediately: keep pumping so a second
                # press is not lost, but the main loop will exit on the next
                # stopped() check within milliseconds.
                break
        user32.UnregisterHotKey(None, HOTKEY_ID)


