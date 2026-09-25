"""Fake-process tests: no Windows prompt, capture or real profile writes."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from unittest.mock import Mock, patch
from PySide6.QtCore import QProcess, QAbstractAnimation
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from desktop.registration import RegistrationDialog

app = QApplication.instance() or QApplication([])


class RegistrationScreenTests(unittest.TestCase):
    def setUp(self):
        self.dialog = RegistrationDialog(speech_enabled=False)
        self.dialog.process = Mock()
        self.dialog.process.state.return_value = QProcess.ProcessState.NotRunning

    def tearDown(self):
        self.dialog.reject()
        self.dialog.deleteLater()
        app.processEvents()

    def ready(self):
        self.dialog.name.setText("Test Owner")
        self.dialog.consent.setChecked(True)

    def test_no_consent_no_prompt(self):
        self.dialog.name.setText("Test Owner")
        self.dialog.start_verification()
        self.dialog.process.start.assert_not_called()

    def test_missing_helper_is_clear(self):
        self.ready()
        with patch("desktop.registration.HELPER") as helper:
            helper.is_file.return_value = False
            self.dialog.start_verification()
        self.dialog.process.start.assert_not_called()
        self.assertIn("missing", self.dialog.status.text())

    def test_verified_does_not_claim_enrollment(self):
        self.ready()
        self.dialog.active = True
        self.dialog.proof_nonce = "A" * 32
        self.dialog.process.readAllStandardOutput.return_value = b"Verified:" + b"A" * 32
        with patch("storage.store.get_primary_admin", return_value=None):
            self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
        self.assertIn("Windows verified", self.dialog.status.text())
        self.assertIn("profile: not created", self.dialog.summary.text())
        self.assertEqual(self.dialog.verified_name, "Test Owner")

    def test_windows_only_sign_in_rejects_other_admin_provenance(self):
        self.ready()
        self.dialog.active = True
        self.dialog.proof_nonce = 'A' * 32
        self.dialog.process.readAllStandardOutput.return_value = b'Verified:' + b'A' * 32
        with patch('storage.store.get_primary_admin', return_value={
                'person_id': 'fake-admin', 'display_name': 'Test Owner', 'device_only': False}):
            self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
        self.assertIn('denied', self.dialog.status.text())
        self.assertEqual(self.dialog.verified_until, 0)

    def test_ambiguous_admins_lock_sign_in(self):
        self.ready()
        self.dialog.active = True
        self.dialog.proof_nonce = 'A' * 32
        self.dialog.process.readAllStandardOutput.return_value = b'Verified:' + b'A' * 32
        with patch('storage.store.get_primary_admin', side_effect=RuntimeError('Multiple active admin profiles')):
            self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
        self.assertIn('owner review', self.dialog.status.text())
        self.assertEqual(self.dialog.verified_until, 0)

    def test_stale_or_unbound_helper_output_cannot_register(self):
        self.ready()
        self.dialog.active = True
        self.dialog.proof_nonce = "A" * 32
        self.dialog.process.readAllStandardOutput.return_value = b"Verified:" + b"B" * 32
        self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
        self.assertEqual(self.dialog.verified_until, 0)
        self.assertIn("remain a guest", self.dialog.status.text())

    def test_fresh_proof_creates_encrypted_profile_and_can_sign_in_again(self):
        from pathlib import Path
        import tempfile
        from cryptography.fernet import Fernet
        from security import vault
        from storage.store import get_primary_admin
        old_fernet, old_path = vault._F, vault.KEY_PATH
        with tempfile.TemporaryDirectory() as folder:
            try:
                vault._F = Fernet(Fernet.generate_key())
                vault.KEY_PATH = str(Path(folder) / 'unused-key')
                self.dialog.db_path = Path(folder) / 'identity.enc'
                self.ready()
                self.dialog.change_step(1)
                self.dialog.change_step(1)
                self.dialog.change_step(1)
                self.dialog.active = True
                self.dialog.proof_nonce = "A" * 32
                self.dialog.process.readAllStandardOutput.return_value = b"Verified:" + b"A" * 32
                self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
                self.dialog.profile_consent.setChecked(True)
                signed_in = []
                self.dialog.authenticated.connect(signed_in.append)
                self.dialog.create_admin()
                self.assertEqual(len(signed_in), 1)
                profile = get_primary_admin(self.dialog.db_path)
                self.assertEqual(signed_in[0].person_id, profile['person_id'])
                self.assertNotIn(b'Test Owner', self.dialog.db_path.read_bytes())
                self.assertEqual(self.dialog.name.text(), '')
                second = RegistrationDialog(speech_enabled=False, db_path=self.dialog.db_path)
                second.process = Mock()
                second.process.state.return_value = QProcess.ProcessState.NotRunning
                second.name.setText('Test Owner')
                second.active = True
                second.proof_nonce = 'B' * 32
                second.process.readAllStandardOutput.return_value = b'Verified:' + b'B' * 32
                again = []
                second.authenticated.connect(again.append)
                second.completed(0, QProcess.ExitStatus.NormalExit)
                self.assertEqual(again[0].person_id, profile['person_id'])
                second.reject()
                second.deleteLater()
            finally:
                vault._F, vault.KEY_PATH = old_fernet, old_path

    def test_crash_cannot_claim_verification(self):
        self.dialog.active = True
        self.dialog.process.readAllStandardOutput.return_value = b"Verified"
        self.dialog.completed(0, QProcess.ExitStatus.CrashExit)
        self.assertNotIn("Windows account verified", self.dialog.status.text())

    def test_cancel_discards_late_success(self):
        self.dialog.active = True
        self.dialog.reject()
        self.dialog.process.kill.assert_called_once()
        self.dialog.process.readAllStandardOutput.return_value = b"Verified"
        self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
        self.assertNotIn("Windows account verified", self.dialog.status.text())

    def test_timeout_stops_helper(self):
        self.dialog.active = True
        self.dialog.expired()
        self.dialog.process.kill.assert_called_once()
        self.assertIn("timed out", self.dialog.status.text())

    def test_policy_block_keeps_admin_locked(self):
        self.dialog.active = True
        self.dialog.process.errorString.return_value = 'Application Control policy blocked this file'
        self.dialog.failed(QProcess.ProcessError.FailedToStart)
        self.assertIn('Application Control', self.dialog.status.text())
        self.assertEqual(self.dialog.verified_until, 0)

    def test_verification_sweep_is_one_shot(self):
        self.ready()
        with patch('desktop.registration.HELPER') as helper:
            helper.is_file.return_value = True
            self.dialog.start_verification()
        self.assertEqual(len(self.dialog.proof_nonce), 32)
        self.assertEqual(self.dialog.process.start.call_args.args[1][-1], self.dialog.proof_nonce)
        self.assertEqual(self.dialog.scan.state(), QAbstractAnimation.State.Running)
        QTest.qWait(780)
        self.assertEqual(self.dialog.scan.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(self.dialog.scan_progress, -1)

    def test_running_helper_prevents_duplicate_start(self):
        self.ready()
        self.dialog.process.state.return_value = QProcess.ProcessState.Running
        self.dialog.start_verification()
        self.dialog.process.start.assert_not_called()

    def test_four_steps_require_name_and_never_claim_registered(self):
        self.dialog.change_step(1)
        self.assertEqual(self.dialog.pages.currentIndex(), 0)
        self.dialog.name.setText("Synthetic owner")
        for index in (1, 2, 3):
            self.dialog.change_step(1)
            self.assertEqual(self.dialog.pages.currentIndex(), index)
        self.dialog.face.setChecked(True)
        self.assertIn("capture not connected", self.dialog.summary.text())
        self.assertIn("Owner profile: not created", self.dialog.summary.text())
        self.assertFalse(self.dialog.next.isEnabled())
        self.dialog.process.start.assert_not_called()

    def test_availability_check_is_not_authentication(self):
        with patch("desktop.registration.HELPER") as helper:
            helper.is_file.return_value = True
            self.dialog.check_availability()
        self.assertEqual(self.dialog.process.start.call_args.args[1], ["check"])
        self.dialog.process.readAllStandardOutput.return_value = b"Available"
        self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
        self.assertEqual(self.dialog.verified_until, 0)
        self.assertIn("Availability alone does not verify", self.dialog.status.text())

    def test_missing_face_hardware_explains_pin_path(self):
        self.dialog.active, self.dialog.operation = True, "check"
        self.dialog.process.readAllStandardOutput.return_value = b"DeviceNotPresent"
        self.dialog.completed(0, QProcess.ExitStatus.NormalExit)
        self.assertIn("Windows Hello PIN", self.dialog.status.text())
        self.assertEqual(self.dialog.verified_until, 0)

    def test_settings_button_opens_only_signin_settings(self):
        with patch("desktop.registration.QDesktopServices.openUrl") as open_url:
            self.dialog.open_settings()
        self.assertEqual(open_url.call_args.args[0].toString(), "ms-settings:signinoptions")

    def test_animation_finishes_and_stops_and_missing_art_falls_back(self):
        self.assertLessEqual(self.dialog.animation.duration(), 1100)
        self.dialog.show()
        self.assertEqual(self.dialog.animation.state(), QAbstractAnimation.State.Running)
        QTest.qWait(2450)
        self.assertEqual(self.dialog.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertEqual(self.dialog.progress, 1)
        self.assertTrue(self.dialog.body.isVisible())
        self.assertIsNone(self.dialog.fade)
        self.assertFalse(self.dialog.skip.isVisible())
        self.dialog.sprite = QPixmap()
        self.assertFalse(self.dialog.grab().isNull())

    def test_step_rail_tracks_the_active_page(self):
        self.dialog.name.setText("Synthetic owner")
        self.dialog.change_step(1)
        self.assertEqual(self.dialog.current_step, 1)
        self.assertIn("02 OF 04", self.dialog.steps.text())
        self.assertEqual(self.dialog.next.text(), "Continue")

    def test_reduced_motion_and_skip_stop_all_animation(self):
        self.dialog.reduced_motion = True
        self.dialog.show()
        self.assertEqual(self.dialog.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertTrue(self.dialog.body.isVisible())
        self.dialog.reduced_motion = False
        self.dialog.hide()
        self.dialog.show()
        self.dialog.finish_intro()
        self.assertEqual(self.dialog.animation.state(), QAbstractAnimation.State.Stopped)

    def test_narration_is_local_cancellable_and_never_listens(self):
        self.dialog.speech = Mock()
        self.dialog.reduced_motion = True
        self.dialog.show()
        self.dialog.mute.setChecked(True)
        self.dialog.narrate()
        self.dialog.speech.say.assert_called_once_with("Hi. I'm LYA. What should I call you?")
        self.dialog.mute.setChecked(False)
        self.dialog.toggle_speech()
        self.dialog.speech.stop.assert_called()
        self.dialog.speech.say.reset_mock()
        self.dialog.narrate()
        self.dialog.speech.say.assert_not_called()
        self.dialog.reject()
        self.assertFalse(self.dialog.narration_timer.isActive())
        self.dialog.narrate()
        self.dialog.speech.say.assert_not_called()

    def test_close_clears_draft_name_preferences_and_verification(self):
        self.ready()
        self.dialog.face.setChecked(True)
        self.dialog.voice.setChecked(True)
        self.dialog.verified_name, self.dialog.verified_until = "Test Owner", 999999999999
        self.dialog.show()
        self.dialog.reject()
        self.assertEqual(self.dialog.name.text(), "")
        self.assertFalse(self.dialog.consent.isChecked())
        self.assertFalse(self.dialog.face.isChecked())
        self.assertFalse(self.dialog.voice.isChecked())
        self.assertEqual(self.dialog.verified_until, 0)
        self.assertEqual(self.dialog.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertFalse(self.dialog.timeout.isActive())


if __name__ == "__main__":
    unittest.main()
