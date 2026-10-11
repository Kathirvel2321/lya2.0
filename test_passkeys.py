"""Synthetic WebAuthn keys/temp encrypted stores only; never opens owner sensors/browser."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).parent / 'desktop'))
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fido2.cose import ES256
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import AttestedCredentialData, AttestationObject, AuthenticatorData, CollectedClientData
from security import vault
from security.approval import ApprovalGate, Challenge
from security.passkeys import PasskeyCeremony
from storage import store


class SyntheticPasskeys:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / 'identity.enc'
        self.fake_key = patch.object(vault, '_F', Fernet(Fernet.generate_key()))
        self.fake_key.start()
        self.addCleanup(self.fake_key.stop)
        self.addCleanup(self.tmp.cleanup)
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential = AttestedCredentialData.create(bytes(16), b'synthetic-credential',
                            ES256.from_cryptography_key(self.key.public_key()))
        self.ceremonies = []
        self.addCleanup(lambda: [c.close() for c in self.ceremonies])

    def ceremony(self, **kwargs):
        c = PasskeyCeremony(db_path=self.db, **kwargs)
        self.ceremonies.append(c)
        return c

    def response(self, c, *, create=False, origin=None, challenge=None, rp='localhost',
                 flags=None, counter=0, key=None, handle=None, cross_origin=False):
        client = CollectedClientData.create('webauthn.create' if create else 'webauthn.get',
            challenge or websafe_decode(c.state['challenge']), origin or c.origin, cross_origin=cross_origin)
        auth = AuthenticatorData.create(hashlib.sha256(rp.encode()).digest(),
            flags if flags is not None else (0x4d if create else 0x0d), counter,
            self.credential if create else b'')
        response = dict(clientDataJSON=websafe_encode(bytes(client)))
        if create:
            response['attestationObject'] = websafe_encode(bytes(AttestationObject.create('none', auth, {})))
        else:
            response.update(authenticatorData=websafe_encode(bytes(auth)),
                signature=websafe_encode((key or self.key).sign(bytes(auth) + client.hash, ec.ECDSA(hashes.SHA256()))),
                userHandle=websafe_encode(c.user_handle if handle is None else handle))
        return dict(id=websafe_encode(self.credential.credential_id),
                    rawId=websafe_encode(self.credential.credential_id), type='public-key', response=response)

    def enroll(self, *, counter=0):
        c = self.ceremony(name='Synthetic owner')
        self.assertEqual(c.complete(self.response(c, create=True)), {'confirm': True})
        self.assertIsNone(store.get_primary_admin(self.db))
        self.assertEqual(c.complete(self.response(c, counter=counter)), {'verified': True})
        return c.result

    def request(self, c, path='/options', data=None, **headers):
        connection = http.client.HTTPConnection('127.0.0.1', c.http.server_port, timeout=3)
        base = {'Host': c.origin[7:], 'Origin': c.origin, 'X-LYA-Ceremony': c.token,
                'Content-Type': 'application/json'}
        base.update(headers)
        connection.request('POST', path, json.dumps({} if data is None else data), base)
        response = connection.getresponse()
        code, body = response.status, response.read()
        connection.close()
        return code, body

class PasskeyChecks(SyntheticPasskeys, unittest.TestCase):
    def test_enroll_confirm_signin_encrypted_public_storage(self):
        session = self.enroll()
        record = store.get_owner_passkey(self.db)
        self.assertEqual(record['person_id'], session.person_id)
        self.assertNotIn(b'Synthetic owner', self.db.read_bytes())
        self.assertNotIn(self.credential.credential_id, self.db.read_bytes())
        self.assertEqual(store.list_face_templates(session.person_id, self.db), [])
        self.assertEqual(store.list_voice_templates(session.person_id, self.db), [])
        c = self.ceremony()
        c.complete(self.response(c))
        self.assertEqual(c.result.person_id, session.person_id)
        self.assertNotEqual(c.result.id, session.id)
        self.assertTrue(290 < c.result.verified_until - time.time() <= 300)

    def test_bad_registration_never_creates_owner(self):
        for bad in ({'origin': 'https://evil.test'}, {'challenge': b'x'*32},
                    {'rp': 'evil.test'}, {'flags': 0x49}, {'flags': 0x4c}, {'cross_origin': True}):
            with self.subTest(bad=bad):
                c = self.ceremony()
                with self.assertRaises(Exception):
                    c.complete(self.response(c, create=True, **bad))
                self.assertIsNone(store.get_primary_admin(self.db))
                self.assertIsNone(c.result)
                self.assertTrue(c.done.is_set())

    def test_failed_confirmation_does_not_commit_public_key(self):
        c = self.ceremony()
        c.complete(self.response(c, create=True))
        wrong = ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(Exception):
            c.complete(self.response(c, key=wrong))
        self.assertIsNone(store.get_primary_admin(self.db))

    def test_registration_rejects_unoffered_algorithm_and_wrong_credential_id(self):
        c = self.ceremony()
        self.assertEqual(c.options_json()['publicKey']['pubKeyCredParams'], [{'type': 'public-key', 'alg': -7}])
        response = self.response(c, create=True)
        response['id'] = response['rawId'] = websafe_encode(b'different-id')
        with self.assertRaises(ValueError):
            c.complete(response)
        from fido2.cose import RS256
        from cryptography.hazmat.primitives.asymmetric import rsa
        self.credential = AttestedCredentialData.create(bytes(16), b'synthetic-rsa',
            RS256.from_cryptography_key(rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()))
        c = self.ceremony()
        with self.assertRaises(ValueError):
            c.complete(self.response(c, create=True))
        self.assertIsNone(store.get_primary_admin(self.db))

    def test_signin_rejects_forgery_wrong_origin_rp_challenge_uv_handle(self):
        self.enroll()
        for bad in ({'key': ec.generate_private_key(ec.SECP256R1())}, {'origin': 'http://localhost:1'},
                    {'rp': 'other'}, {'challenge': b'b'*32}, {'flags': 0x09},
                    {'flags': 0x0c}, {'handle': b'other-user'}, {'cross_origin': True}, {'flags': 0x15}):
            with self.subTest(bad=bad):
                c = self.ceremony()
                with self.assertRaises(Exception):
                    c.complete(self.response(c, **bad))
                self.assertIsNone(c.result)

    def test_expiry_cancellation_replay_fail_closed(self):
        c = self.ceremony()
        reply = self.response(c, create=True)
        c.deadline = time.monotonic() - 1
        with self.assertRaises(PermissionError):
            c.complete(reply)
        c.close()
        self.assertFalse(c.thread.is_alive())
        self.assertIsNone(store.get_primary_admin(self.db))
        self.enroll()
        c = self.ceremony()
        reply = self.response(c)
        c.complete(reply)
        with self.assertRaises(PermissionError):
            c.complete(reply)
        other = self.ceremony()
        with self.assertRaises(Exception):
            other.complete(reply)
        cancelled = self.ceremony()
        reply = self.response(cancelled)
        cancelled.close()
        with self.assertRaises(PermissionError):
            cancelled.complete(reply)

    def test_legacy_and_ambiguous_owners_cannot_be_claimed(self):
        before = store.register_device_admin('Legacy synthetic', self.db)
        original = self.db.read_bytes()
        with self.assertRaises(PermissionError):
            self.ceremony()
        self.assertEqual(self.db.read_bytes(), original)
        with store.store_connection(self.db) as db:
            db.execute("INSERT INTO people VALUES('another','Other','admin','now',1)")
        with self.assertRaises(PermissionError):
            self.ceremony()
        self.assertEqual(store.get_person(before, self.db)['display_name'], 'Legacy synthetic')

    def test_two_enrollments_cannot_overwrite_first_owner(self):
        first, second = self.ceremony(), self.ceremony()
        first.complete(self.response(first, create=True))
        second.complete(self.response(second, create=True))
        first.complete(self.response(first))
        with self.assertRaises(PermissionError):
            second.complete(self.response(second))
        self.assertEqual(store.get_primary_admin(self.db)['person_id'], first.result.person_id)

    def test_revoked_owner_and_counter_rollback_are_rejected(self):
        session = self.enroll(counter=1)
        c = self.ceremony()
        with self.assertRaises(PermissionError):
            c.complete(self.response(c, counter=1))
        c = self.ceremony()
        c.complete(self.response(c, counter=2))
        c = self.ceremony()
        with store.store_connection(self.db) as db:
            db.execute('UPDATE people SET active=0 WHERE person_id=?', (session.person_id,))
        with self.assertRaises(PermissionError):
            c.complete(self.response(c, counter=3))
        self.assertIsNone(c.result)

    def test_http_capability_origin_host_content_boundaries(self):
        c = self.ceremony()
        self.assertEqual(self.request(c)[0], 200)
        for headers in ({'Origin': 'https://evil.test'}, {'Host': 'evil.test'},
                        {'X-LYA-Ceremony': ''}, {'X-LYA-Ceremony': 'fake'}, {'X-LYA-Ceremony': 'é'},
                        {'Content-Type': 'text/plain'}, {'Transfer-Encoding': 'chunked'}):
            self.assertEqual(self.request(c, **headers)[0], 403)
        self.assertEqual(self.request(c, data=['bad'])[0], 400)
        oversized = http.client.HTTPConnection('127.0.0.1', c.http.server_port)
        oversized.putrequest('POST', '/options', skip_host=True)
        for header, value in {'Host': c.origin[7:], 'Origin': c.origin, 'X-LYA-Ceremony': c.token,
                              'Content-Type': 'application/json', 'Content-Length': '65537'}.items():
            oversized.putheader(header, value)
        oversized.endheaders()
        rejection = oversized.getresponse()
        self.assertEqual(rejection.status, 413)
        rejection.read()
        oversized.close()
        self.assertEqual(c.http.server_address[0], '127.0.0.1')
        connection = http.client.HTTPConnection('127.0.0.1', c.http.server_port)
        connection.request('GET', '/', headers={'Host': c.origin[7:]})
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
        self.assertIn("frame-ancestors 'none'", response.getheader('Content-Security-Policy'))
        page = response.read().decode()
        self.assertNotIn(c.token, page)
        self.assertNotIn(c.user_handle.hex(), page)
        self.assertNotIn('/art', page)
        self.assertNotIn('<img', page)
        self.assertIn('aria-label="Continue with phone"', page)
        self.assertIn('prefers-reduced-motion', page)
        connection.close()
        art = http.client.HTTPConnection('127.0.0.1', c.http.server_port)
        art.request('GET', '/art', headers={'Host': c.origin[7:]})
        response = art.getresponse()
        self.assertEqual(response.status, 404)
        response.read()
        art.close()
        self.assertEqual(self.request(c, path='/cancel', **{'X-LYA-Ceremony': 'wrong'})[0], 403)
        self.assertFalse(c.done.is_set())
        self.assertEqual(self.request(c, path='/cancel')[0], 200)
        self.assertTrue(c.done.is_set())
        self.assertIsNone(c.result)

    def test_exact_action_gate_needs_fresh_assertion_and_invalidates(self):
        session = self.enroll()
        proofs = []
        def verifier(challenge):
            c = self.ceremony(approval=challenge)
            proofs.append(self.response(c))
            self.assertIn(challenge.parameters, c.options_json()['context'])
            c.complete(proofs[-1])
            return c.result
        gate = ApprovalGate(verifier)
        self.assertTrue(gate('memory_write', 'remember private synthetic fact', session))
        def replay(challenge):
            c = self.ceremony(approval=challenge)
            c.complete(proofs[0])
            return c.result
        gate.verifier = replay
        self.assertFalse(gate('memory_write', 'remember DIFFERENT fact', session))
        def revoked(challenge):
            c = self.ceremony(approval=challenge)
            c.complete(self.response(c))
            gate.invalidate()
            return c.result
        gate.verifier = revoked
        self.assertFalse(gate('memory_read', 'recall synthetic', session))

    def test_cancelled_action_and_expiry_during_store_do_not_grant_access(self):
        session = self.enroll()
        challenge = Challenge('synthetic-nonce', session, 'memory_read', 'recall synthetic', time.monotonic()+60)
        c = self.ceremony(approval=challenge, approval_valid=lambda: False)
        with self.assertRaises(PermissionError):
            c.complete(self.response(c))
        self.assertIsNone(c.result)
        c = self.ceremony()
        real = store.accept_passkey_assertion
        def expires(*args):
            real(*args)
            c.deadline = time.monotonic()-1
        with patch.object(store, 'accept_passkey_assertion', side_effect=expires):
            with self.assertRaises(PermissionError):
                c.complete(self.response(c))
        self.assertIsNone(c.result)


class OwnerUIChecks(SyntheticPasskeys, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        self.app.setQuitOnLastWindowClosed(False)
        self.speech_patch = patch('desktop.setup_speech.SetupSpeech.say')
        self.say = self.speech_patch.start()
        self.addCleanup(self.speech_patch.stop)

    def dialog(self, **kwargs):
        from desktop.owner_setup import OwnerSetupDialog
        kwargs.setdefault('reduced_motion', True)
        dialog = OwnerSetupDialog(db_path=self.db, **kwargs)
        self.addCleanup(dialog.reject)
        dialog.show()
        self.app.processEvents()
        return dialog

    def test_voice_setup_name_confirmation_cancel_no_forms(self):
        from PySide6.QtWidgets import QLineEdit
        d = self.dialog(open_browser=lambda _: self.fail('Unexpected browser'))
        self.assertEqual(d.findChildren(QLineEdit), [])
        d.handle_voice('I agree')
        self.assertEqual(d.stage, 'name')
        d.handle_voice('My name is Synthetic buddy')
        self.assertEqual(d.stage, 'confirm_name')
        d.handle_voice('try again')
        self.assertEqual(d.stage, 'name')
        d.handle_voice('My name is Synthetic owner')
        d.handle_voice('yes, that is my name')
        self.assertEqual(d.stage, 'recovery')
        self.assertIn('separate', d.body.text())
        d.handle_voice('cancel')
        self.assertTrue(d.closed)
        self.assertFalse(d.isVisible())
        self.assertIsNone(store.get_primary_admin(self.db))

    def test_ui_real_crypto_result_and_closed_sensorless_ceremony(self):
        opened = []
        d = self.dialog(open_browser=lambda url: opened.append(url) or True)
        authenticated = []
        d.authenticated.connect(authenticated.append)
        d.advance()
        d.advance()
        d.advance()
        c = d.ceremony
        self.ceremonies.append(c)
        self.assertEqual(d.stage, 'waiting')
        c.complete(self.response(c, create=True))
        self.say.reset_mock()
        d.check_result()
        self.say.assert_called_once()
        self.assertIn('once more', self.say.call_args.args[0])
        d.check_result()
        self.say.assert_called_once()
        self.assertIsNone(store.get_primary_admin(self.db))
        c.complete(self.response(c))
        d.check_result()
        self.assertEqual(len(authenticated), 1)
        self.assertEqual(authenticated[0].person, 'Owner')
        self.assertFalse(c.thread.is_alive())
        self.assertTrue(d.closed)
        self.assertEqual(len(opened), 1)

    def test_hide_before_phone_stops_guidance_and_timers(self):
        from desktop.owner_setup import OwnerSetupDialog
        for stage in ('intro', 'name', 'recovery'):
            with self.subTest(stage=stage):
                d = OwnerSetupDialog(db_path=self.db, reduced_motion=False)
                self.addCleanup(d.reject)
                d.stage = stage
                self.say.reset_mock()
                d.show()
                d.hide()  # Hide before the queued first guidance can start.
                self.app.processEvents()
                self.assertTrue(d.closed)
                self.assertFalse(d.expire.isActive())
                self.assertFalse(d.mark.timer.isActive())
                self.say.assert_not_called()
                self.assertIsNone(store.get_primary_admin(self.db))

    def test_hide_cancels_and_legacy_screen_stays_locked(self):
        d = self.dialog(open_browser=lambda _: True)
        d.advance(); d.advance(); d.advance()
        c = d.ceremony
        d.hide()
        self.app.processEvents()
        self.assertTrue(c.done.is_set())
        self.assertIsNone(c.result)
        self.assertFalse(c.thread.is_alive())
        store.register_device_admin('Legacy synthetic', self.db)
        other = self.dialog()
        self.assertEqual(other.stage, 'blocked')
        self.assertFalse(other.next.isEnabled())

    def test_long_action_review_reaches_browser_and_minimize_cancels(self):
        from PySide6.QtCore import Qt
        session = self.enroll()
        challenge = Challenge('synthetic-long', session, 'memory_write', 'synthetic line\n'*200,
                              time.monotonic()+60)
        d = self.dialog(approval=challenge, open_browser=lambda _: True)
        self.assertIn(challenge.parameters, d.body.text())
        self.assertIn('Review the exact request in your browser', d.prompt)
        self.assertEqual(d.title.textFormat(), Qt.TextFormat.PlainText)
        d.advance()
        c = d.ceremony
        self.assertIn(challenge.parameters, c.options_json()['context'])
        from security.passkeys import PAGE
        self.assertIn('max-height:50vh;overflow:auto', PAGE)
        d.showMinimized()
        self.app.processEvents()
        self.assertTrue(d.closed)
        self.assertTrue(c.done.is_set())
        self.assertIsNone(c.result)

    def test_voice_only_particles_phases_accessibility_and_minimum_layout(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QLabel, QPushButton
        d = self.dialog()
        self.assertFalse(hasattr(d.mark, 'art'))
        self.assertEqual([label for label in d.findChildren(QLabel) if label.isVisible()], [])
        for button in d.findChildren(QPushButton):
            self.assertEqual(button.text(), '')
            self.assertTrue(button.accessibleName())
        self.assertEqual(d.accessibleDescription(), d.prompt)
        self.assertFalse(d.mark.timer.isActive())
        self.assertEqual(d.mark.mode, 'ready')
        ready = d.mark.grab().toImage()
        d.set_input_phase('hearing')
        self.assertEqual(d.mark.mode, 'hearing')
        self.assertEqual(d.mark.accessibleDescription(), 'hearing')
        d._speaking(True)
        self.assertEqual(d.mark.mode, 'speaking')
        self.assertNotEqual(ready, d.mark.grab().toImage())
        d._speaking(False)
        d.set_input_phase('transcribing')
        self.assertEqual(d.mark.mode, 'thinking')
        d.set_input_phase('listening')
        self.assertEqual(d.mark.mode, 'listening')
        d.resize(320, 280)
        self.app.processEvents()
        for button in (d.repeat, d.next, d.cancel):
            bottom = button.mapTo(d, QPoint(0, button.height())).y()
            self.assertLessEqual(bottom, d.height())
            self.assertGreaterEqual(button.mapTo(d, QPoint(0, 0)).x(), 0)
        d.handle_voice('I agree')
        self.assertIn('What should I call you', d.accessibleDescription())
        d.reject()
        self.assertFalse(d.mark.timer.isActive())
        moving = self.dialog(reduced_motion=False)
        self.assertTrue(moving.mark.timer.isActive())
        moving.hide()
        self.app.processEvents()
        self.assertFalse(moving.mark.timer.isActive())

    def test_registration_stays_on_screen_and_near_the_existing_lya_orb(self):
        from PySide6.QtCore import QPoint, Qt
        from experience import OrbDesktop
        desktop = OrbDesktop(self.app, reduced_motion=True)
        desktop.brain.db_path = self.db
        self.addCleanup(desktop.quit)
        area = self.app.primaryScreen().availableGeometry()
        desktop.orb.show()
        desktop.orb.move(area.right()-desktop.orb.width()-12, area.top()+12)
        desktop.open_owner_access()
        dialog = desktop.owner_dialog
        self.app.processEvents()
        self.assertTrue(area.contains(dialog.geometry()))
        self.assertLessEqual(dialog.geometry().right(), desktop.orb.x()-1)
        self.assertTrue(dialog.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        for width, height in ((320, 280), (460, 390), (600, 500)):
            dialog.resize(width, height)
            self.app.processEvents()
            self.assertGreater(dialog.mark.height(), 100)
            for button in (dialog.repeat, dialog.next, dialog.cancel):
                self.assertTrue(dialog.rect().contains(button.mapTo(dialog, QPoint(0, 0))))
                self.assertTrue(dialog.rect().contains(button.mapTo(dialog, QPoint(button.width()-1, button.height()-1))))
        dialog.reject()
        desktop.orb.hide()
        desktop.open_owner_access()
        self.app.processEvents()
        self.assertTrue(area.contains(desktop.owner_dialog.geometry()))

    def test_native_voice_dispatch_and_passkey_session_handoff(self):
        from experience import OrbDesktop
        desktop = OrbDesktop(self.app, reduced_motion=True)
        desktop.brain.db_path = self.db
        self.addCleanup(desktop.quit)
        with patch.object(desktop.speech, 'say'), patch('desktop.setup_speech.SetupSpeech.say'):
            desktop.command('register admin')
            self.assertTrue(desktop.owner_dialog.isVisible())
            desktop.on_voice('I agree')
            self.assertEqual(desktop.owner_dialog.stage, 'name')
            desktop.on_voice('open camera')
            self.assertFalse(hasattr(desktop, 'vision_dialog'))
            desktop.on_voice('cancel')
            session = self.enroll()
            desktop.on_passkey_authenticated(session)
            self.app.processEvents()
            self.assertEqual(desktop.brain.session, session)
            self.assertIsNotNone(desktop.brain.approve.verifier)
            self.assertIn('phone passkey', desktop.panel.answer.toPlainText())

    def test_native_worker_exact_approval_memory_and_camera_gate(self):
        from experience import OrbDesktop
        from PySide6.QtTest import QTest
        desktop = OrbDesktop(self.app, reduced_motion=True)
        desktop.brain.db_path = self.db
        self.addCleanup(desktop.quit)
        session = self.enroll()
        desktop.spoken = False
        desktop.on_passkey_authenticated(session)
        self.app.processEvents()
        self.assertEqual(desktop.brain._authorize('camera_view', 'open camera'), session.person_id)
        answer = []
        worker = threading.Thread(target=lambda: answer.append(desktop.brain.respond(
            'remember short Synthetic topic = Synthetic value')))
        with patch('desktop.owner_setup.webbrowser.open', return_value=True):
            # Default browser callable is bound at definition; replace start only for test.
            worker.start()
            for _ in range(80):
                self.app.processEvents()
                if desktop.passkey_approval.dialog is not None:
                    break
                QTest.qWait(10)
            dialog = desktop.passkey_approval.dialog
            self.assertIsNotNone(dialog)
            self.assertIn('remember short Synthetic topic = Synthetic value', dialog.body.text())
            dialog.open_browser = lambda _: True
            dialog.advance()
            c = dialog.ceremony
            self.ceremonies.append(c)
            c.complete(self.response(c))
            dialog.check_result()
            worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(answer), 1)
        self.assertIn('Saved note', answer[0].text)
        self.assertEqual(len(store.recall(session.person_id, '', db_path=self.db)), 1)
        # Cancellation invalidates the pending UI as well as the Brain's grant.
        desktop.passkey_approval.dialog = None
        answer.clear()
        worker = threading.Thread(target=lambda: answer.append(desktop.brain.respond('recall Synthetic topic')))
        worker.start()
        for _ in range(80):
            self.app.processEvents()
            if desktop.passkey_approval.dialog is not None:
                break
            QTest.qWait(10)
        desktop.brain.approve.invalidate()
        desktop.passkey_approval.dialog.check_approval()
        worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertNotIn('Synthetic value', answer[0].text)


if __name__ == '__main__':
    unittest.main()
