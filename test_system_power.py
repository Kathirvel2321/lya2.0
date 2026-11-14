"""Tests for basic spoken power actions - restart, sleep."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.capabilities import system_power


class MatcherTests(unittest.TestCase):
    def test_restart_phrases(self):
        for text in ("restart", "restart now", "reboot", "restart my laptop",
                     "restart the computer", "reboot this pc", "restart now please",
                     "restart, please", "LYA restart"):
            self.assertEqual(system_power(text.casefold()), "restart", text)

    def test_sleep_phrases(self):
        for text in ("sleep", "sleep now", "go to sleep", "take a nap",
                     "put the laptop to sleep", "LYA sleep", "sleep, please"):
            self.assertEqual(system_power(text.casefold()), "sleep", text)

    def test_negations_do_not_trigger(self):
        for text in ("don't restart", "should I restart?", "why did it sleep",
                     "how to restart a phone", "did you sleep well",
                     "the song 'sleep now'", "no restart"):
            self.assertIsNone(system_power(text.casefold()), text)

    def test_quoting_does_not_trigger(self):
        self.assertIsNone(system_power("he said 'restart'"))

    def test_shutdown_deliberately_absent(self):
        self.assertIsNone(system_power("shut down"))
        self.assertIsNone(system_power("shutdown my laptop"))

    def test_device_executes_fixed_actions(self):
        from skills import device
        with mock.patch.object(device.subprocess, "Popen") as popen:
            self.assertIn("Restarting", device.system_power("restart"))
            self.assertEqual(popen.call_args[0][0][:2], ["shutdown", "/r"])
        with mock.patch.object(device.subprocess, "Popen") as popen:
            self.assertIn("sleep", device.system_power("sleep").lower())
            self.assertEqual(popen.call_args[0][0][0], "rundll32.exe")

    def test_device_refuses_unknown(self):
        from skills import device
        self.assertIn("Unknown", device.system_power("format c:"))


if __name__ == "__main__":
    unittest.main()
