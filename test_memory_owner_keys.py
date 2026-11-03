"""Generated native DPAPI keys, signed fake passkeys, temporary stores, offscreen Qt."""
from dataclasses import replace
import hashlib
import io
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication,QLineEdit
from brain import memory_owner_keys as keys
from security.approval import Challenge
from security.policy import Session
from storage import store
from test_passkeys import SyntheticPasskeys
from tools.memory_key_enrollment import EnrollmentWindow,main


class OwnerKeysChecks(SyntheticPasskeys,unittest.TestCase):
    def setUp(self):
        super().setUp();self.session=self.enroll();self.home=Path(self.tmp.name)/'new-keys'

    def proof(self,parameters=keys.PREPARE):
        challenge=Challenge('FAKE_OWNER_KEY_OPERATION',self.session,'memory_backup',parameters,time.monotonic()+120)
        c=self.ceremony(approval=challenge,approval_valid=lambda:True);c.complete(self.response(c));self.assertEqual(c.result,challenge)
        return c.result

    def prepare(self):return keys.prepare(self.home,self.proof(),db_path=self.db)

    def test_owner_keys_prepare_resume_and_encrypted_boundaries(self):
        view=self.prepare();saved={p.name:p.read_bytes() for p in self.home.iterdir()}
        self.assertFalse(view.custody_acknowledged);self.assertNotIn(view.unlock_key.decode(),repr(view))
        raw=keys._keys(self.home,(self.session.person_id,hashlib.sha256(store.get_owner_passkey(self.db)['credential'].encode()).hexdigest()))
        for blob in saved.values():
            for secret in (view.unlock_key,raw['storage_key'].encode(),raw['recovery_key'].encode(),self.session.person_id.encode()):
                self.assertNotIn(secret,blob)
        other=self.prepare();self.assertEqual(view,other)
        self.assertEqual(saved,{p.name:p.read_bytes() for p in self.home.iterdir()})

    def test_owner_keys_exact_proof_expiry_and_role_are_required(self):
        proof=self.proof()
        for bad in (None,True,replace(proof,action='memory_read'),replace(proof,parameters=keys.CONFIRM),
                    replace(proof,deadline=0),replace(proof,deadline=float('nan')),
                    replace(proof,session=replace(self.session,role='friend')),
                    replace(proof,session=replace(self.session,verified_until=0))):
            with self.assertRaises(PermissionError):keys.prepare(self.home,bad,db_path=self.db)
        self.assertFalse(self.home.exists())

    def test_owner_keys_confirm_requires_both_retrieved_copies_and_separate_action(self):
        view=self.prepare();saved=(self.home/'keys.dpapi').read_bytes();unlock=view.unlock_key.decode()
        proof=self.proof(keys.CONFIRM)
        for first,second in ((unlock,'wrong'),('wrong',unlock),('',unlock)):
            with self.assertRaises(ValueError):keys.confirm(self.home,proof,first,second,db_path=self.db)
            self.assertFalse((self.home/'custody.dpapi').exists())
        with self.assertRaises(PermissionError):keys.confirm(self.home,self.proof(),unlock,unlock,db_path=self.db)
        out=keys.confirm(self.home,proof,unlock,unlock,db_path=self.db)
        self.assertTrue(out['custody_acknowledged']);self.assertFalse(out['production_enabled'])
        self.assertFalse(out['external_copy_survival_verified']);self.assertTrue(self.prepare().custody_acknowledged)
        self.assertEqual((self.home/'keys.dpapi').read_bytes(),saved)

    def test_owner_keys_revocation_and_credential_change_cannot_claim_existing_keys(self):
        self.prepare();saved=(self.home/'keys.dpapi').read_bytes();proof=self.proof()
        with store.store_connection(self.db) as db:db.execute('UPDATE people SET active=0')
        with self.assertRaises(PermissionError):keys.prepare(self.home,proof,db_path=self.db)
        with store.store_connection(self.db) as db:
            db.execute('UPDATE people SET active=1');db.execute("UPDATE owner_passkeys SET credential='changed-fake-public-credential'")
        with self.assertRaises(ValueError):keys.prepare(self.home,proof,db_path=self.db)
        self.assertEqual((self.home/'keys.dpapi').read_bytes(),saved)

    def test_owner_keys_corrupt_missing_and_oversized_records_never_recreate(self):
        view=self.prepare();proof=self.proof();record=self.home/'keys.dpapi';saved=record.read_bytes()
        record.write_bytes(b'FAKE_BAD')
        with self.assertRaises(ValueError):keys.prepare(self.home,proof,db_path=self.db)
        record.write_bytes(saved);capsule=self.home/'capsule.enc';sealed=capsule.read_bytes();capsule.write_bytes(b'FAKE_BAD')
        with self.assertRaises(ValueError):keys.prepare(self.home,proof,db_path=self.db)
        with self.assertRaises(ValueError):keys.confirm(self.home,self.proof(keys.CONFIRM),view.unlock_key.decode(),view.unlock_key.decode(),db_path=self.db)
        capsule.write_bytes(sealed);record.unlink()
        with self.assertRaises(ValueError):keys.prepare(self.home,proof,db_path=self.db)
        self.assertFalse(record.exists());record.write_bytes(b'x'*(keys.LIMIT+1))
        with self.assertRaises(ValueError):keys.prepare(self.home,proof,db_path=self.db)

    def test_owner_keys_no_plaintext_fallback_or_incomplete_preflight_directory(self):
        proof=self.proof()
        with patch.object(keys,'_protect',side_effect=OSError('FAKE DPAPI unavailable')),self.assertRaises(OSError):
            keys.prepare(self.home,proof,db_path=self.db)
        self.assertFalse(self.home.exists())
        with patch.object(keys.sys,'platform','linux'),self.assertRaises(OSError):keys.prepare(self.home,proof,db_path=self.db)
        self.assertFalse(self.home.exists())

    def test_owner_keys_revoked_during_protection_leaves_only_protected_pending_state(self):
        proof=self.proof();original=keys._protect;calls=[0]
        def revoke(raw):
            calls[0]+=1;blob=original(raw)
            if calls[0]==2:
                with store.store_connection(self.db) as db:db.execute('UPDATE people SET active=0')
            return blob
        with patch.object(keys,'_protect',side_effect=revoke),self.assertRaises(PermissionError):keys.prepare(self.home,proof,db_path=self.db)
        self.assertTrue((self.home/'keys.dpapi').is_file());self.assertFalse((self.home/'custody.dpapi').exists())
        self.assertFalse((self.home/'capsule.enc').exists())

    def window(self):
        self.app=QApplication.instance() or QApplication([]);window=EnrollmentWindow(self.home,db_path=self.db)
        self.addCleanup(window.close);window.show();self.app.processEvents();return window

    def ui_prepare(self,window):
        with patch('webbrowser.open',return_value=True):
            window.start('prepare');window.ceremony.complete(self.response(window.ceremony));window.poll()
            window.ceremony.complete(self.response(window.ceremony));window.poll()

    def test_owner_keys_ui_signed_prepare_masks_secret_and_clears_on_close(self):
        window=self.window();self.ui_prepare(window)
        secret=window.unlock.text();self.assertEqual(len(secret),44)
        self.assertEqual(window.unlock.echoMode(),QLineEdit.EchoMode.Password)
        self.assertNotIn(secret,window.status.text()+window.reference.text())
        self.assertTrue(window.confirm_button.isEnabled());window.close();self.assertEqual(window.unlock.text(),'')

    def test_owner_keys_ui_signed_confirm_records_acknowledgement_and_keeps_production_off(self):
        window=self.window();self.ui_prepare(window);secret=window.unlock.text()
        window.vault.setText(secret);window.offline.setText(secret)
        with patch('webbrowser.open',return_value=True):
            window.start('confirm');window.ceremony.complete(self.response(window.ceremony));window.poll()
        self.assertTrue((self.home/'custody.dpapi').is_file());self.assertEqual(window.unlock.text(),'')
        self.assertEqual((window.vault.text(),window.offline.text()),('',''))
        self.assertIn('Production memory remains disconnected',window.status.text())

    def test_owner_keys_ui_wrong_proof_and_dependency_check_never_read_real_data(self):
        window=self.window()
        with patch('webbrowser.open',return_value=True):
            window.start('prepare');window.ceremony.result=True;window.ceremony.done.set();window.poll()
        self.assertFalse(self.home.exists());self.assertEqual(window.unlock.text(),'')
        with (patch.object(sys,'argv',['memory-key-setup','--check-only']),
                patch('sys.stdout',new_callable=io.StringIO) as stream,
                patch.object(store,'store_connection',side_effect=AssertionError('Must not inspect owner store'))):
            self.assertEqual(main(),0)
        self.assertIn('No owner store',stream.getvalue())


if __name__=='__main__':unittest.main()
