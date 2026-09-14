"""Step 8: Core Skills & Device Execution Capabilities Test Suite
=============================================================
Tests:
  1. Device open_app strict allowlist, non-shell execution, and reject unknown apps
  2. Device volume commands and parameter validation
  3. Device screenshot creation within sandboxed directory
  4. FolderBrowser root boundary enforcement, paging, file inspection, and navigation
  5. Reminder natural language time parsing across all formats
  6. Reminder encrypted SQLite CRUD, chronological sorting, due_now, and cancellation
  7. Skill forge draft generation, syntax validation, discard, and activation lockout
  8. Assistant.handle() end-to-end command routing and permission gating
"""
import datetime
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from skills import device, files, reminder, forge
from security.policy import Session


class DeviceSkillsTests(unittest.TestCase):
    def test_open_app_allowlist_and_safety(self):
        """open_app only allows fixed allowlisted executables and never runs arbitrary commands."""
        with patch("subprocess.Popen") as mock_popen:
            # Allowlisted apps
            res = device.open_app("calculator")
            self.assertIn("Launch requested for calculator", res)
            mock_popen.assert_called_once_with(["calc.exe"])

            mock_popen.reset_mock()
            res = device.open_app("Notepad")
            self.assertIn("Launch requested for Notepad", res)
            mock_popen.assert_called_once_with(["notepad.exe"])

            mock_popen.reset_mock()
            res = device.open_app("file explorer")
            self.assertIn("Launch requested for file explorer", res)
            mock_popen.assert_called_once_with(["explorer.exe"])

            mock_popen.reset_mock()
            res = device.open_app("chrome")
            self.assertIn("Launch requested for chrome", res)
            mock_popen.assert_called_once_with(["chrome.exe"])

            # Disallowed apps / command injection attempts must be rejected
            mock_popen.reset_mock()
            res = device.open_app("cmd")
            self.assertIn("Supported apps", res)
            mock_popen.assert_not_called()

            res = device.open_app("calc.exe & notepad.exe")
            self.assertIn("Supported apps", res)
            mock_popen.assert_not_called()

            res = device.open_app("powershell")
            self.assertIn("Supported apps", res)
            mock_popen.assert_not_called()

    def test_volume_actions(self):
        """volume only accepts up, down, mute and handles execution gracefully."""
        mock_pag = MagicMock()
        with patch.object(device, "pyautogui", mock_pag):
            res = device.volume("up")
            self.assertEqual(res, "Volume up.")
            mock_pag.press.assert_called_once_with("volumeup")

            mock_pag.reset_mock()
            res = device.volume("down")
            self.assertEqual(res, "Volume down.")
            mock_pag.press.assert_called_once_with("volumedown")

            mock_pag.reset_mock()
            res = device.volume("mute")
            self.assertEqual(res, "Volume mute.")
            mock_pag.press.assert_called_once_with("volumemute")

            # Invalid input
            mock_pag.reset_mock()
            res = device.volume("max")
            self.assertIn("Say volume up, volume down, or volume mute", res)
            mock_pag.press.assert_not_called()

    def test_screenshot_sandboxed(self):
        """screenshot creates the output directory and saves timestamped image."""
        mock_pag = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(device, "pyautogui", mock_pag):
                res = device.screenshot(output_dir=tmp)
                self.assertIn("Screenshot saved to", res)
                mock_pag.screenshot.assert_called_once()
                saved_path = mock_pag.screenshot.call_args[0][0]
                self.assertTrue(saved_path.startswith(os.path.abspath(tmp)))
                self.assertTrue(saved_path.endswith(".png"))


class FolderBrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name).resolve()
        # Populate structure
        for i in range(5):
            (self.root / f"folder_{i}").mkdir()
        (self.root / "notes.txt").write_text("Secret notes", encoding="utf-8")
        (self.root / "sub_script.py").write_text("print('hello')", encoding="utf-8")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_boundary_enforcement(self):
        """FolderBrowser strictly forbids directory traversal outside root."""
        browser = files.FolderBrowser(root=self.root)
        with self.assertRaises(PermissionError):
            browser._inside(self.root.parent)
        with self.assertRaises(PermissionError):
            browser._inside(self.root / ".." / "outside")

    def test_listing_and_paging(self):
        """Listing returns page sliced entries with accurate pagination metadata."""
        browser = files.FolderBrowser(root=self.root, page_size=3)
        res = browser.listing()
        self.assertEqual(res["page"], 1)
        self.assertEqual(len(res["entries"]), 3)
        self.assertTrue(res["more"])

        # Scroll to page 2
        res2 = browser.scroll(1)
        self.assertEqual(res2["page"], 2)
        self.assertGreaterEqual(len(res2["entries"]), 1)

        # Scroll back
        res3 = browser.scroll(-1)
        self.assertEqual(res3["page"], 1)

    def test_open_folder_and_file_inspection(self):
        """Opening a folder enters it; opening a file returns metadata without executing."""
        browser = files.FolderBrowser(root=self.root, page_size=10)
        browser.listing()

        # Open folder by name
        res = browser.open("folder_0")
        self.assertEqual(browser.current, self.root / "folder_0")
        self.assertEqual(res["entries"], [])

        # Go back to root
        browser.back()
        self.assertEqual(browser.current, self.root)

        # Open file returns metadata, not execution
        file_res = browser.open("notes.txt")
        self.assertEqual(file_res["file"], "notes.txt")
        self.assertEqual(file_res["bytes"], len("Secret notes"))
        self.assertIn("File details only", file_res["message"])


_real_datetime = datetime.datetime


class FakeDateTime(_real_datetime):
    _current_now = _real_datetime(2026, 9, 10, 12, 0, 0)

    @classmethod
    def now(cls, tz=None):
        return cls._current_now


class ReminderSkillsTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmp_dir.name) / "test_reminders.db")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_time_hint_natural_language_parsing(self):
        """_time_hint parses relative, weekday, and explicit calendar dates."""
        fixed_now = datetime.datetime(2026, 9, 10, 12, 0, 0)
        FakeDateTime._current_now = fixed_now
        with patch("skills.reminder.datetime.datetime", FakeDateTime):
            # 1. Relative minutes and hours
            t1, what1 = reminder._time_hint("remind me to check oven in 30 minutes")
            self.assertEqual(t1, fixed_now + datetime.timedelta(minutes=30))
            self.assertEqual(what1, "check oven")

            t2, what2 = reminder._time_hint("remind me to walk dog in 2 hrs")
            self.assertEqual(t2, fixed_now + datetime.timedelta(hours=2))
            self.assertEqual(what2, "walk dog")

            # 2. Tomorrow
            t3, what3 = reminder._time_hint("remind me to call John tomorrow at 5pm")
            self.assertEqual(t3, datetime.datetime(2026, 9, 11, 17, 0, 0))
            self.assertIn("call John", what3)

            # 3. Next weekday (Thursday Sept 10 -> Next Monday is Sept 14)
            t4, what4 = reminder._time_hint("remind me to submit code next monday at 9am")
            self.assertEqual(t4, datetime.datetime(2026, 9, 14, 9, 0, 0))
            self.assertIn("submit code", what4)

            # 4. Explicit calendar date (5 june at 6pm -> 2027-06-05)
            t5, what5 = reminder._time_hint("remind me to attend wedding on 5 june at 6pm")
            self.assertEqual(t5, datetime.datetime(2027, 6, 5, 18, 0, 0))
            self.assertIn("attend wedding", what5)

    def test_encrypted_crud_and_chronological_ordering(self):
        """Reminders are stored encrypted in SQLite and list_all orders chronologically."""
        fixed_now = datetime.datetime(2026, 9, 10, 12, 0, 0)
        FakeDateTime._current_now = fixed_now
        with patch("skills.reminder.datetime.datetime", FakeDateTime):
            # Add later reminder first
            reminder.add("remind me to dentist tomorrow at 4pm", db_path=self.db_path)
            # Add earlier reminder second
            reminder.add("remind me to team standup tomorrow at 10am", db_path=self.db_path)

        # Direct database inspection: raw SQLite values must be ciphertext
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT what, when_iso FROM reminders").fetchall()
        conn.close()
        self.assertEqual(len(rows), 2)
        for w, t in rows:
            self.assertNotIn("dentist", w)
            self.assertNotIn("team standup", w)
            self.assertNotIn("2026-09-11", t)

        # Decrypted list_all must be sorted chronologically
        all_rems = reminder.list_all(db_path=self.db_path)
        self.assertEqual(len(all_rems), 2)
        self.assertEqual(all_rems[0][1], "team standup")  # 10am
        self.assertEqual(all_rems[1][1], "dentist")       # 4pm

        # due_now check
        due_past = datetime.datetime(2026, 9, 11, 11, 0, 0)
        FakeDateTime._current_now = due_past
        with patch("skills.reminder.datetime.datetime", FakeDateTime):
            fired = reminder.due_now(db_path=self.db_path)
            self.assertEqual(len(fired), 1)
            self.assertEqual(fired[0][1], "team standup")

            # Calling due_now again should not re-fire
            fired_again = reminder.due_now(db_path=self.db_path)
            self.assertEqual(len(fired_again), 0)

        # Cancel remaining reminder
        msg = reminder.cancel("dentist", db_path=self.db_path)
        self.assertIn("Cancelled 1 reminder", msg)
        self.assertEqual(len(reminder.list_all(db_path=self.db_path)), 1)
        reminder.cancel("team standup", db_path=self.db_path)
        self.assertEqual(len(reminder.list_all(db_path=self.db_path)), 0)


class SkillForgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.orig_draft = forge.DRAFT
        self.orig_meta = forge.META
        forge.DRAFT = str(Path(self.tmp_dir.name) / "forge_draft.py")
        forge.META = str(Path(self.tmp_dir.name) / "forge_meta.json")

    def tearDown(self):
        forge.DRAFT = self.orig_draft
        forge.META = self.orig_meta
        self.tmp_dir.cleanup()

    def test_create_valid_skill_draft(self):
        """create writes draft and metadata when match and reply are present."""
        sample_code = (
            "'''Sample test skill'''\n"
            "def match(text): return 'ping' in text.lower()\n"
            "def reply(text, say=None, ask=None): return 'pong'\n"
        )
        with patch.object(forge, "_groq", return_value=sample_code):
            res = forge.create("ping pong responder")
            self.assertIn("SKILL DRAFTED", res)
            self.assertTrue(os.path.exists(forge.DRAFT))
            self.assertEqual(Path(forge.DRAFT).read_text(encoding="utf-8"), sample_code)

            meta = forge._meta()
            self.assertEqual(meta.get("pending_desc"), "ping pong responder")

    def test_create_rejects_missing_functions_or_syntax_error(self):
        """create rejects code missing match/reply or containing syntax errors."""
        bad_code = "print('no match or reply function')"
        with patch.object(forge, "_groq", return_value=bad_code):
            res = forge.create("broken skill")
            self.assertIn("discarded it", res)
            self.assertFalse(os.path.exists(forge.DRAFT))

        syntax_error_code = "def match(text:\n    return True\ndef reply(text): pass"
        with patch.object(forge, "_groq", return_value=syntax_error_code):
            res = forge.create("syntax error skill")
            self.assertIn("syntax error", res)
            self.assertFalse(os.path.exists(forge.DRAFT))

    def test_activation_disabled_and_discard(self):
        """activate returns safety block statement; discard deletes draft."""
        self.assertIn("Activation is disabled", forge.activate())

        Path(forge.DRAFT).write_text("placeholder")
        self.assertTrue(os.path.exists(forge.DRAFT))
        msg = forge.discard()
        self.assertIn("Draft discarded", msg)
        self.assertFalse(os.path.exists(forge.DRAFT))


class AssistantSkillsIntegrationTests(unittest.TestCase):
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

    def test_open_app_routing(self):
        with patch("skills.device.open_app", return_value="Launch requested for calculator.") as mock_open:
            res = self.app.handle("open calculator")
            self.assertEqual(res, "Launch requested for calculator.")
            mock_open.assert_called_once_with("calculator")

    def test_volume_routing(self):
        with patch("skills.device.volume", return_value="Volume up.") as mock_vol:
            res = self.app.handle("volume up")
            self.assertEqual(res, "Volume up.")
            mock_vol.assert_called_once_with("up")

    def test_screenshot_routing(self):
        with patch("skills.device.screenshot", return_value="Screenshot saved.") as mock_ss:
            res = self.app.handle("screenshot")
            self.assertEqual(res, "Screenshot saved.")
            self.assertTrue(self.app.private_output)
            mock_ss.assert_called_once()

    def test_reminders_routing(self):
        with patch("skills.reminder.add", return_value="Got it. I'll remind you.") as mock_add:
            res = self.app.handle("remind me to check tests in 1 hour")
            self.assertEqual(res, "Got it. I'll remind you.")
            self.assertTrue(self.app.private_output)
            mock_add.assert_called_once_with("remind me to check tests in 1 hour")

    def test_skill_forge_routing(self):
        with patch("skills.forge.create", return_value="SKILL DRAFTED") as mock_create:
            res = self.app.handle("create skill battery alert")
            self.assertEqual(res, "SKILL DRAFTED")
            mock_create.assert_called_once_with("battery alert")

        res_act = self.app.handle("confirm skill")
        self.assertIn("Automatic code activation is disabled", res_act)

    def test_what_time_is_it_routing(self):
        res = self.app.handle("what time is it")
        self.assertIn(str(datetime.datetime.now().year), res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
