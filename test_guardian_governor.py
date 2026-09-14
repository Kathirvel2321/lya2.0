"""Step 9: Autonomous Guardian & System Health Governor Test Suite
===============================================================
Tests:
  1. Dangerous command screening and pattern detection
  2. Guardian guard execution gating (verified vs unverified)
  3. Proactive safety feedback (correct_user)
  4. Silent duress flag signaling, fail-closed detection, and clearing
  5. Action audit logging (encrypted file + SQLite synchronization)
  6. Resource governor hardware metrics (RAM, battery, disk space)
  7. Emergency kill switch engagement, autonomous suspension, and release
  8. Hardening self-audit with duress and kill switch indicators
  9. Assistant.handle() command integration and emergency brake routing
"""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skills import guardian, governor, harden
from security.policy import Session
from security import vault
from storage import store


class GuardianSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

        # Isolate duress file and action log
        self.orig_duress_file = guardian.DURESS_FILE
        self.orig_log_file = guardian.ACTION_LOG_FILE
        guardian.DURESS_FILE = str(self.tmp_path / "duress_flag.lya")
        guardian.ACTION_LOG_FILE = str(self.tmp_path / "lya_actions.log.lya")

    def tearDown(self):
        guardian.DURESS_FILE = self.orig_duress_file
        guardian.ACTION_LOG_FILE = self.orig_log_file
        self.tmp_dir.cleanup()

    def test_dangerous_command_detection(self):
        """Dangerous commands are correctly flagged; benign commands pass."""
        dangerous_samples = [
            "format c: /fs:ntfs",
            "del /s /q c:\\users",
            "rm -rf /var/log",
            "rmdir /s /q C:\\Windows",
            "shutdown /s /t 0",
            "reg delete HKLM\\Software\\Policies",
            "diskpart /s script.txt",
            "cipher /w:C:",
            "vssadmin delete shadows /all",
            "bcdedit /set {default} bootstatuspolicy ignoreallfailures",
            "drop table users",
            "drop database production",
            "powershell -encodedcommand d2hvYW1p",
            "takeown /f C:\\Windows",
        ]
        for cmd in dangerous_samples:
            self.assertTrue(guardian.is_dangerous(cmd), f"Failed to detect dangerous command: {cmd}")

        safe_samples = [
            "open calculator",
            "volume up",
            "show folders",
            "what time is it",
            "remind me to call Mom",
            "who are you",
            "use theme halo",
        ]
        for cmd in safe_samples:
            self.assertFalse(guardian.is_dangerous(cmd), f"Benign command falsely flagged: {cmd}")

    def test_guard_execution_gate(self):
        """Dangerous commands require verified identity; unverified calls are blocked."""
        executed = []
        action = lambda: executed.append(True) or "Action ran"

        # 1. Benign command passes unverified
        ok, msg = guardian.guard("open calculator", action, verified=False)
        self.assertTrue(ok)
        self.assertEqual(msg, "Action ran")
        self.assertEqual(len(executed), 1)

        # 2. Dangerous command blocked when unverified
        executed.clear()
        ok, msg = guardian.guard("format C:", action, verified=False)
        self.assertFalse(ok)
        self.assertIn("dangerous command", msg)
        self.assertEqual(len(executed), 0)

        # 3. Dangerous command allowed when verified
        executed.clear()
        ok, msg = guardian.guard("format C:", action, verified=True)
        self.assertTrue(ok)
        self.assertIn("Verified. Action ran", msg)
        self.assertEqual(len(executed), 1)

    def test_correct_user_proactive_warnings(self):
        """correct_user returns helpful pushback on destructive user intents."""
        self.assertIsNotNone(guardian.correct_user("delete all my project files"))
        self.assertIsNotNone(guardian.correct_user("shutdown the system now"))
        self.assertIsNotNone(guardian.correct_user("format the backup flash drive"))
        self.assertIsNone(guardian.correct_user("hello what is the weather today"))

    def test_silent_duress_subsystem(self):
        """Duress flag is created encrypted, detected silently, fails closed on tamper, and resets cleanly."""
        # Initial state
        active, _ = guardian.check_duress()
        self.assertFalse(active)

        # Raise silent duress
        ok = guardian.raise_duress(who="escalation_test", detail="Coercion suspected")
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(guardian.DURESS_FILE))

        # Check duress
        active, data = guardian.check_duress()
        self.assertTrue(active)
        self.assertEqual(data.get("who"), "escalation_test")
        self.assertIn("Coercion suspected", data.get("detail"))

        # Fails closed on corrupted duress flag
        with open(guardian.DURESS_FILE, "wb") as f:
            f.write(b"not_valid_ciphertext")
        active, err_data = guardian.check_duress()
        self.assertTrue(active)
        self.assertIn("corrupted", str(err_data))

        # Clear duress
        ok = guardian.clear_duress()
        self.assertTrue(ok)
        active, _ = guardian.check_duress()
        self.assertFalse(active)

    def test_action_audit_logging(self):
        """Actions are logged to encrypted log file and readable via get_audit_log."""
        guardian.log_action("run_diagnostic", allowed=True, actor="admin", detail="routine check")
        guardian.log_action("format D:", allowed=False, actor="guest", detail="blocked format")

        self.assertTrue(os.path.exists(guardian.ACTION_LOG_FILE))
        # Decrypted retrieval
        with open(guardian.ACTION_LOG_FILE, "rb") as f:
            raw = f.read()
        self.assertNotIn(b"run_diagnostic", raw)
        self.assertNotIn(b"blocked format", raw)

        # Decrypted retrieval
        logs = guardian.get_audit_log(limit=10)
        self.assertGreaterEqual(len(logs), 2)


class GovernorHealthTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.orig_kill_file = governor.KILL_FILE
        governor.KILL_FILE = str(Path(self.tmp_dir.name) / "KILL_SWITCH")

    def tearDown(self):
        governor.KILL_FILE = self.orig_kill_file
        self.tmp_dir.cleanup()

    def test_resource_governor_metrics(self):
        """Governor returns process memory, disk free, and battery status."""
        mem = governor.get_process_memory_mb()
        self.assertIsInstance(mem, float)
        self.assertGreater(mem, 0.0)
        self.assertLess(mem, 150.0, "Working set exceeds reasonable assistant footprint")

        disk = governor.get_disk_free_gb()
        self.assertIsInstance(disk, float)
        self.assertGreater(disk, 0.0)

        bat = governor.get_battery_status()
        self.assertIn("battery_pct", bat)
        self.assertIn("ac_online", bat)

        health = governor.get_health()
        self.assertIn("ok", health)
        self.assertIn("ram_mb", health)
        self.assertIn("battery_pct", health)
        self.assertIn("status_message", health)

        report = governor.format_health_report()
        self.assertIn("SYSTEM HEALTH & RESOURCE GOVERNOR", report)
        self.assertIn("RAM Footprint", report)
        self.assertIn("Battery Power", report)

    def test_emergency_kill_switch_lifecycle(self):
        """Kill switch freezes execution when engaged and restores when released."""
        self.assertFalse(governor.is_killed())

        msg_engage = governor.engage_kill_switch("Unit test emergency stop")
        self.assertIn("ENGAGED", msg_engage)
        self.assertTrue(governor.is_killed())
        self.assertTrue(os.path.exists(governor.KILL_FILE))

        # Health reflects killed status
        health = governor.get_health()
        self.assertFalse(health["ok"])
        self.assertTrue(health["killed"])
        self.assertIn("KILL SWITCH", health["status_message"])

        msg_release = governor.release_kill_switch()
        self.assertIn("RELEASED", msg_release)
        self.assertFalse(governor.is_killed())
        self.assertFalse(os.path.exists(governor.KILL_FILE))


class HardenAuditTests(unittest.TestCase):
    def test_self_audit(self):
        """harden.audit checks security locks and flags anomalies."""
        report = harden.audit()
        self.assertIn("LYA SELF-AUDIT", report)
        self.assertIn("DPAPI-bound vault key", report)
        self.assertIn("Hard rules active", report)


class AssistantSafetyRoutingTests(unittest.TestCase):
    def setUp(self):
        from main import Assistant
        self.face = MagicMock()
        self.app = Assistant.__new__(Assistant)
        self.app.face = self.face
        self.app.build = False
        self.app.session = Session("admin", "Kathirvel")
        self.app.permit = lambda action, task: True
        self.app.browser = None
        self.app.browse_until = 0
        self.app.pending_lesson = None
        self.app._reminder_started = False
        self.app.cancelled = threading.Event()
        self.app.identify = lambda: None

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.orig_kill_file = governor.KILL_FILE
        governor.KILL_FILE = str(Path(self.tmp_dir.name) / "KILL_SWITCH")

    def tearDown(self):
        governor.KILL_FILE = self.orig_kill_file
        self.tmp_dir.cleanup()

    def test_system_health_and_battery_routing(self):
        res1 = self.app.handle("system health")
        self.assertIn("SYSTEM HEALTH & RESOURCE GOVERNOR", res1)

        res2 = self.app.handle("battery status")
        self.assertIn("SYSTEM HEALTH & RESOURCE GOVERNOR", res2)

    def test_security_audit_routing(self):
        res = self.app.handle("is lya secure")
        self.assertIn("LYA SELF-AUDIT", res)

    def test_dangerous_command_blocked_in_assistant(self):
        res = self.app.handle("format c:")
        self.assertIn("formatting will erase data irreversibly", res.lower())

        res2 = self.app.handle("del /s /q c:\\users")
        self.assertIn("permanently", res2.lower())

    def test_kill_switch_command_flow(self):
        # Engage kill switch
        res = self.app.handle("emergency stop")
        self.assertIn("kill switch ENGAGED", res)
        self.assertTrue(governor.is_killed())

        # Commands blocked while killed
        res_blocked = self.app.handle("open calculator")
        self.assertIn("Emergency kill switch is engaged", res_blocked)

        # Release kill switch
        res_resume = self.app.handle("release kill switch")
        self.assertIn("kill switch RELEASED", res_resume)
        self.assertFalse(governor.is_killed())


if __name__ == "__main__":
    unittest.main(verbosity=2)
