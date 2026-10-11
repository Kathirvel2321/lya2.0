"""Explicit operator retirement: fake keys/temp stores, no owner data or sensors."""
import os
import time
import unittest
from unittest.mock import patch

from brain.workflow import Brain
from security.policy import Session
from storage import store
from test_passkeys import SyntheticPasskeys
from tools import retire_legacy_owner as maintenance


class LegacyRetirementChecks(SyntheticPasskeys, unittest.TestCase):
    def seed(self):
        owner = store.register_device_admin('Old synthetic owner', self.db)
        duplicate = store.create_person('Old synthetic duplicate', 'admin', self.db)
        friend = store.create_person('Synthetic friend', 'friend', self.db)
        store.remember(owner, 'old project', 'synthetic old notes', db_path=self.db)
        store.remember(friend, 'friend project', 'synthetic friend notes', db_path=self.db)
        with store.store_connection(self.db) as db:
            for person_id in (owner, friend):
                db.execute('INSERT INTO face_templates(person_id,embedding_enc,model_version,quality,created_at) VALUES(?,?,?,?,?)',
                           (person_id, 'synthetic-cipher', 'synthetic', 1, 'synthetic'))
                db.execute('INSERT INTO voice_templates(person_id,embedding_enc,model_version,quality,created_at) VALUES(?,?,?,?,?)',
                           (person_id, 'synthetic-cipher', 'synthetic', 1, 'synthetic'))
                db.execute('INSERT INTO admin_recovery VALUES(?,?,?,NULL)',
                           (person_id, 'synthetic-hash', 'synthetic'))
            db.execute('INSERT INTO vault_items(person_id,label_enc,file_path_enc,created_at) VALUES(?,?,?,?)',
                       (owner, 'synthetic-label', 'synthetic-path', 'synthetic'))
        return owner, duplicate, friend

    def test_retire_backup_preserve_private_rows_revoke_and_fresh_enroll(self):
        owner, duplicate, friend = self.seed()
        original = self.db.read_bytes()
        self.assertTrue(maintenance.check(self.db)['legacy_owner_present'])
        result = maintenance.retire(self.db)
        self.assertTrue(result['changed'])
        self.assertEqual(result['backup'].read_bytes(), original)
        self.assertNotIn(b'Old synthetic owner', result['backup'].read_bytes())
        if os.name == 'nt':
            import win32security
            descriptor = win32security.GetFileSecurity(str(result['backup'].parent),
                                                       win32security.DACL_SECURITY_INFORMATION)
            self.assertTrue(descriptor.GetSecurityDescriptorControl()[0] & win32security.SE_DACL_PROTECTED)
            acl = descriptor.GetSecurityDescriptorDacl()
            self.assertEqual(acl.GetAceCount(), 2)
            self.assertIn('S-1-5-18', [win32security.ConvertSidToStringSid(acl.GetAce(i)[2]) for i in range(2)])
            file_acl = win32security.GetFileSecurity(str(result['backup']),
                win32security.DACL_SECURITY_INFORMATION).GetSecurityDescriptorDacl()
            self.assertEqual(file_acl.GetAceCount(), 2)
        with store.store_connection(result['backup'], read_only=True) as backup:
            self.assertEqual(backup.execute("SELECT COUNT(*) FROM people WHERE role='admin' AND active=1").fetchone()[0], 2)
            self.assertEqual(backup.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertIsNone(store.get_owner_passkey(self.db))
        for retired in (owner, duplicate):
            self.assertFalse(store.get_person(retired, self.db)['active'])
        self.assertTrue(store.get_person(friend, self.db)['active'])
        with store.store_connection(self.db, read_only=True) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM memories').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM vault_items').fetchone()[0], 1)
            for table in ('face_templates', 'voice_templates', 'admin_recovery'):
                self.assertEqual(db.execute(f'SELECT person_id FROM {table}').fetchall(), [(friend,)])
        brain = Brain(db_path=self.db, client=lambda _: self.fail('Unexpected inference'))
        brain.bind_session(Session('admin', 'Old synthetic owner', 'old-session', owner, time.time()+300))
        with self.assertRaises(PermissionError):
            brain._authorize('camera_view', 'open camera')
        after = self.db.read_bytes()
        self.assertFalse(maintenance.retire(self.db)['changed'])
        self.assertEqual(self.db.read_bytes(), after)
        new_session = self.enroll()
        self.assertNotIn(new_session.person_id, (owner, duplicate, friend))
        self.assertEqual(store.recall(new_session.person_id, 'old project', db_path=self.db), [])

    def test_backup_failure_never_changes_owner_store(self):
        self.seed()
        original = self.db.read_bytes()
        with patch.object(maintenance, 'protect_directory', side_effect=PermissionError('synthetic ACL failure')):
            with self.assertRaises(PermissionError):
                maintenance.retire(self.db)
        self.assertEqual(self.db.read_bytes(), original)
        self.assertTrue(maintenance.check(self.db)['legacy_owner_present'])

    def test_existing_phone_owner_refused_without_mutation(self):
        self.enroll()
        original = self.db.read_bytes()
        with self.assertRaises(PermissionError):
            maintenance.retire(self.db)
        self.assertEqual(self.db.read_bytes(), original)
        self.assertFalse((self.db.parent/'registration-archive').exists())

    def test_missing_store_is_not_created(self):
        with self.assertRaises(FileNotFoundError):
            maintenance.retire(self.db)
        self.assertFalse(self.db.exists())


if __name__ == '__main__':
    unittest.main()
