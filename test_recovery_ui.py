"""Native UI + disk recovery drill with fake profiles, disposable keys, no network."""
import os
import json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtTest import QTest
from brain import notes
from security import vault
from security.policy import Session
from security.approval import ApprovalGate
from storage import recovery, store
from desktop.recovery import RecoveryDialog

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class RecoveryInterfaceChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lya-recovery-ui-")
        self.addCleanup(self.tmp.cleanup)
        key_patch = patch.object(vault, "_F", Fernet(Fernet.generate_key()))
        key_patch.start()
        self.addCleanup(key_patch.stop)
        self.db = Path(self.tmp.name) / "source.enc"
        self.now = 2000000000.0
        self.pid = store.create_person("Fake owner", "admin", db_path=self.db)
        self.current = Session("admin", "Fixture", "session1", self.pid, self.now + 1000)
        self.mid = notes.save(self.pid, "Synthetic project", "Fixture only", "permanent", db_path=self.db, now=self.now)["id"]
        self.path = Path(self.tmp.name) / "selected.lya-notes"
        self.approvals = []
        def approve(challenge):
            self.approvals.append(challenge)
            return challenge
        self.gate = ApprovalGate(approve, wall_clock=lambda: self.now)
        self.dialog = RecoveryDialog(get_session=lambda: self.current, approve=self.gate,
                                     db_path=self.db, clock=lambda: self.now)
        self.dialog.show()
        APP.processEvents()

    def tearDown(self):
        self.dialog.cancel_operation()
        self.dialog.pool.waitForDone(3000)
        APP.processEvents()
        self.dialog.reject()
        self.dialog.deleteLater()
        APP.processEvents()

    def settle(self):
        for _ in range(500):
            APP.processEvents()
            if not self.dialog.busy:
                return
            QTest.qWait(10)
        self.fail("Recovery worker did not complete")

    def options(self):
        return dict(get_session=lambda: self.current, approve=self.gate, db_path=self.db,
                    clock=lambda: self.now)

    def ready_backup(self):
        self.dialog.load_notes()
        self.settle()
        self.assertEqual(self.dialog.notes.count(), 1)
        self.dialog.notes.item(0).setCheckState(Qt.CheckState.Checked)
        self.dialog.generate_key()
        key = self.dialog.key.text()
        self.dialog.confirm_key.setText(key)
        self.dialog.custody.setChecked(True)
        self.assertTrue(self.dialog.save.isEnabled())
        return key

    def save_backup(self):
        key = self.ready_backup()
        with (patch('desktop.recovery.QFileDialog.getSaveFileName', return_value=(str(self.path), '')),
              patch('desktop.recovery.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes)):
            self.dialog.save_backup()
        self.settle()
        self.assertTrue(self.path.is_file())
        return key

    def empty_destination(self):
        self.db = Path(self.tmp.name) / "fresh.enc"
        vault._F = Fernet(Fernet.generate_key())
        self.pid = store.create_person("Fresh fake owner", "admin", db_path=self.db)
        self.current = Session("admin", "Fresh", "session2", self.pid, self.now + 1000)
        self.dialog.db_path = self.db
        self.dialog.update_controls()
        self.dialog.tabs.setCurrentIndex(1)

    def test_real_ui_file_to_new_key_restore_drill(self):
        key = self.save_backup()
        self.assertNotIn(b"Fixture only", self.path.read_bytes())
        self.assertEqual(self.dialog.key.text(), '')
        self.assertEqual(self.dialog.confirm_key.text(), '')
        self.assertEqual(json.loads(self.approvals[-1].parameters)['destination'], str(self.path.resolve()))
        self.empty_destination()
        self.dialog.archive.setText(str(self.path))
        self.dialog.restore_key.setText(key)
        self.dialog.inspect_archive()
        self.settle()
        self.assertIn('1 unexpired', self.dialog.preview_text.text())
        self.assertFalse(self.dialog.restore.isEnabled())
        self.dialog.restore_consent.setChecked(True)
        with patch('desktop.recovery.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            self.dialog.restore_backup()
        self.settle()
        self.assertIn('Restored 1 notes', self.dialog.status.text())
        self.assertEqual(self.dialog.restore_key.text(), '')
        with store.store_connection(self.db, read_only=True) as db:
            value = db.execute("SELECT value_enc FROM memories WHERE person_id=?", (self.pid,)).fetchone()[0]
            self.assertEqual(vault.decrypt_text(value), 'Fixture only')

    def test_guest_cannot_list_generate_or_read_files(self):
        self.current = Session()
        self.dialog.update_controls()
        with patch('storage.recovery.list_notes') as read, patch('storage.recovery.new_recovery_key') as generate:
            self.dialog.load_notes()
            self.dialog.generate_key()
        read.assert_not_called()
        generate.assert_not_called()
        self.assertFalse(self.dialog.tabs.isEnabled())
        self.assertNotIn('1 available notes', self.dialog.status.text())
        self.assertEqual(self.dialog.notes.count(), 0)

    def test_project_note_survives_the_native_file_restore_journey(self):
        store.forget(self.pid, "Synthetic project", db_path=self.db)
        self.mid = notes.save(self.pid, "Synthetic project", "Fixture only", "permanent",
                              project_id="atlas", db_path=self.db, now=self.now)["id"]
        self.test_real_ui_file_to_new_key_restore_drill()
        self.assertEqual(notes.retrieve(self.pid, db_path=self.db, now=self.now), [])
        restored = notes.retrieve(self.pid, project_id="atlas", db_path=self.db, now=self.now)
        self.assertEqual(restored[0]["value"], "Fixture only")

    def test_default_gate_denies_even_with_session(self):
        self.dialog.approve = None
        self.dialog.load_notes()
        self.settle()
        self.assertIn('Permission denied', self.dialog.status.text())
        self.assertEqual(self.dialog.notes.count(), 0)

    def test_key_custody_and_confirmation_are_required(self):
        self.ready_backup()
        self.dialog.confirm_key.setText('wrong')
        self.assertFalse(self.dialog.save.isEnabled())
        self.dialog.confirm_key.setText(self.dialog.key.text())
        self.dialog.custody.setChecked(False)
        self.assertFalse(self.dialog.save.isEnabled())

    def test_expiry_clears_visible_labels_and_keys(self):
        self.ready_backup()
        self.now += 1001
        self.dialog.update_controls()
        self.assertEqual(self.dialog.notes.count(), 0)
        self.assertEqual(self.dialog.key.text(), '')
        self.assertFalse(self.dialog.tabs.isEnabled())

    def test_wrong_key_and_nonempty_profile_block_restore(self):
        key = self.save_backup()
        self.dialog.tabs.setCurrentIndex(1)
        self.dialog.archive.setText(str(self.path))
        self.dialog.restore_key.setText(recovery.new_recovery_key().decode())
        self.dialog.inspect_archive()
        self.settle()
        self.assertIsNone(self.dialog.preview)
        self.dialog.restore_key.setText(key)
        self.dialog.inspect_archive()
        self.settle()
        self.assertFalse(self.dialog.preview['empty'])
        self.dialog.restore_consent.setChecked(True)
        self.assertFalse(self.dialog.restore.isEnabled())

    def test_preview_change_resets_confirmation_and_rejects_replaced_archive(self):
        key = self.save_backup()
        self.empty_destination()
        self.dialog.archive.setText(str(self.path))
        self.dialog.restore_key.setText(key)
        self.dialog.inspect_archive()
        self.settle()
        digest = self.dialog.preview['digest']
        self.dialog.restore_consent.setChecked(True)
        self.dialog.restore_key.setText(recovery.new_recovery_key().decode())
        self.assertIsNone(self.dialog.preview)
        self.assertFalse(self.dialog.restore_consent.isChecked())
        before = self.db.read_bytes()
        self.path.write_bytes(self.path.read_bytes() + b'changed')
        with self.assertRaises(ValueError):
            recovery.restore_file(self.path, key.encode(), digest, **self.options())
        self.assertEqual(before, self.db.read_bytes())

    def test_close_while_working_requests_cancel_and_drops_preview(self):
        entered, release = threading.Event(), threading.Event()
        def waiting(**options):
            entered.set()
            release.wait(3)
            self.assertTrue(options['cancelled']())
            return [{'id': 1, 'label': 'Late private label', 'retention': 'permanent', 'expires_at': None}]
        with patch('storage.recovery.list_notes', side_effect=waiting):
            self.dialog.load_notes()
            self.assertTrue(entered.wait(1))
            self.dialog.reject()
            self.assertTrue(self.dialog.close_pending)
            release.set()
            self.settle()
        self.assertEqual(self.dialog.notes.count(), 0)
        self.assertFalse(self.dialog.isVisible())

    def test_file_write_failure_and_destination_race_do_not_clobber(self):
        key = recovery.new_recovery_key()
        with patch('storage.recovery.os.fsync', side_effect=OSError('disk full')), self.assertRaises(OSError):
            recovery.export_file([self.mid], key, self.path, **self.options())
        self.assertFalse(self.path.exists())
        self.assertEqual(list(Path(self.tmp.name).glob('.lya-backup-*')), [])
        original_rename = recovery.os.rename
        def race(source, destination):
            Path(destination).write_bytes(b'pre-existing fixture')
            return original_rename(source, destination)
        with patch('storage.recovery.os.rename', side_effect=race), self.assertRaises(FileExistsError):
            recovery.export_file([self.mid], key, self.path, **self.options())
        self.assertEqual(self.path.read_bytes(), b'pre-existing fixture')
        self.assertEqual(list(Path(self.tmp.name).glob('.lya-backup-*')), [])

    def test_publish_denies_session_expiry_after_encryption(self):
        before_fsync = recovery.os.fsync
        def expire(fd):
            before_fsync(fd)
            self.current = replace(self.current, verified_until=0)
        with patch('storage.recovery.os.fsync', side_effect=expire), self.assertRaises(PermissionError):
            recovery.export_file([self.mid], recovery.new_recovery_key(), self.path, **self.options())
        self.assertFalse(self.path.exists())
        self.assertEqual(list(Path(self.tmp.name).glob('.lya-backup-*')), [])


if __name__ == '__main__':
    unittest.main()
