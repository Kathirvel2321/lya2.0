"""Fake keys, synthetic vectors/devices and temporary stores; no real enrollment."""
from dataclasses import replace
import json
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch

from test_passkeys import SyntheticPasskeys
from security.policy import Session
from security.owner_profiles import FACE_MODEL, VOICE_MODEL, checked_vector, matches
from storage import store


def profiles():
    return {'face': [[1.0]+[0.0]*127 for _ in range(3)],
            'voice': [[1.0]+[0.0]*255 for _ in range(3)]}


class ProfileStoreChecks(SyntheticPasskeys, unittest.TestCase):
    def save(self, session, data=None, **kwargs):
        credential = store.get_owner_passkey(self.db)['credential']
        return store.save_owner_profiles(session, credential, data or profiles(), consent=True, db_path=self.db, **kwargs)

    def test_atomic_encrypted_local_profiles_consent_and_no_overwrite(self):
        session = self.enroll()
        self.assertEqual(store.owner_profiles(session, self.db), {'face': [], 'voice': []})
        with self.assertRaises(PermissionError):
            store.owner_profiles(session, self.db, expected_credential='a-different-credential')
        self.save(session)
        self.assertEqual(store.owner_profiles(session, self.db), profiles())
        self.assertNotIn(json.dumps(profiles()['face'][0]).encode(), self.db.read_bytes())
        with store.store_connection(self.db, read_only=True) as db:
            self.assertEqual(db.execute("SELECT outcome FROM audit_events WHERE action_type='owner_profile_consent'").fetchall(),
                             [('local_face_voice_v1',)])
        original = self.db.read_bytes()
        with self.assertRaises(PermissionError):
            self.save(session)
        self.assertEqual(original, self.db.read_bytes())
        if __import__('os').name == 'nt':
            import win32security
            descriptor = win32security.GetFileSecurity(str(self.db), win32security.DACL_SECURITY_INFORMATION)
            self.assertTrue(descriptor.GetSecurityDescriptorDacl())
            sids = [win32security.ConvertSidToStringSid(descriptor.GetSecurityDescriptorDacl().GetAce(i)[2])
                    for i in range(descriptor.GetSecurityDescriptorDacl().GetAceCount())]
            self.assertNotIn('S-1-1-0', sids)
            self.assertNotIn('S-1-5-32-545', sids)

    def test_no_consent_wrong_credential_guest_expired_and_revoked_deny(self):
        session = self.enroll()
        original = self.db.read_bytes()
        credential = store.get_owner_passkey(self.db)['credential']
        for proof, key, consent in ((Session(), credential, True),
                (replace(session, verified_until=time.time()-1), credential, True),
                (replace(session, person_id='another-owner'), credential, True),
                (session, 'changed-public-key', True), (session, credential, False)):
            with self.subTest(proof=proof.role, consent=consent):
                with self.assertRaises(PermissionError):
                    store.save_owner_profiles(proof, key, profiles(), consent=consent, db_path=self.db)
                self.assertEqual(original, self.db.read_bytes())
        with store.store_connection(self.db) as db:
            db.execute('UPDATE people SET active=0')
        with self.assertRaises(PermissionError):
            store.save_owner_profiles(session, credential, profiles(), consent=True, db_path=self.db)

    def test_bad_vectors_inconsistent_samples_and_encryption_failure_save_nothing(self):
        session = self.enroll()
        original = self.db.read_bytes()
        for vector in ([0.0]*256, [float('nan')]+[0.0]*255, [True]+[0.0]*255, [1.0], [0.0,1.0]+[0.0]*254):
            bad = profiles()
            bad['voice'][2] = vector
            with self.assertRaises(ValueError):
                self.save(session, bad)
            self.assertEqual(original, self.db.read_bytes())
        from security import vault
        with patch.object(vault, 'encrypt_text', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError):
                self.save(session)
        self.assertEqual(original, self.db.read_bytes())
        self.assertEqual(store.owner_profiles(session, self.db), {'face': [], 'voice': []})

    def test_session_expires_during_save_atomic_rollback(self):
        session = self.enroll()
        original = self.db.read_bytes()
        real = store._profile_owner
        calls = []
        def expires(db, proof, expected=None):
            calls.append(True)
            return real(db, replace(proof, verified_until=time.time()-1) if len(calls)>1 else proof, expected)
        with patch.object(store, '_profile_owner', side_effect=expires):
            with self.assertRaises(PermissionError):
                self.save(session)
        self.assertEqual(original, self.db.read_bytes())

    def test_recognition_never_replaces_phone_or_private_action_approval(self):
        session = self.enroll()
        self.save(session)
        stored = store.owner_profiles(session, self.db)
        self.assertIs(matches(stored['voice'][0], stored['voice'], VOICE_MODEL), True)
        self.assertIs(matches(stored['face'][0], stored['face'], FACE_MODEL), True)
        self.assertFalse(matches([0.,1.]+[0.]*126, stored['face'], FACE_MODEL))
        from security.approval import ApprovalGate
        self.assertFalse(ApprovalGate()('memory_read', 'synthetic private request', session))
        self.assertFalse(ApprovalGate(lambda _: True)('memory_read', 'synthetic private request', session))
        with self.assertRaises(PermissionError):
            store.owner_profiles(Session(role='friend', person_id=session.person_id), self.db)


class ProfileUIChecks(SyntheticPasskeys, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication([])
        self.app.setQuitOnLastWindowClosed(False)
        speech = patch('desktop.setup_speech.SetupSpeech.say', autospec=True,
                       side_effect=lambda speech, *_: setattr(speech, 'cancelled', False))
        speech.start()
        self.addCleanup(speech.stop)

    def dialog(self, **kwargs):
        from desktop.owner_setup import OwnerSetupDialog
        dialog = OwnerSetupDialog(db_path=self.db, reduced_motion=True, **kwargs)
        self.addCleanup(dialog.reject)
        dialog.show()
        self.app.processEvents()
        return dialog
    def fake_capture(self):
        from PySide6.QtCore import QObject, Signal
        class FakeCapture(QObject):
            ready = Signal()
            sample = Signal(str, int)
            preview = Signal(object)
            tracking = Signal(object)
            meter = Signal(float)
            failed = Signal()
            stopped = Signal()
            retry = Signal(str)
            hint = Signal(str)
            def __init__(self, session, parent):
                super().__init__(parent)
                self.samples = {'face': [], 'voice': []}
                self.started, self.closing = False, False
            def start(self):
                self.started = True
                self.ready.emit()
            def capture(self, kind, index):
                self.samples[kind].append(profiles()[kind][index])
                self.sample.emit(kind, index)
                if len(self.samples['voice']) == 3:
                    self.stop(clear=False)
            def stop(self, *, clear=True):
                self.closing = True
                if clear:
                    self.samples = {'face': [], 'voice': []}
                self.stopped.emit()
        return FakeCapture

    def prepare(self, *, alive=False):
        session = self.enroll()
        listener = Mock()
        listener.voice_thread = Mock() if alive else None
        if alive:
            listener.voice_thread.is_alive.return_value = True
        listener.cloud_voice, listener.quitting = True, False
        dialog = self.dialog(profile_setup=True, listener=listener, capture_factory=self.fake_capture())
        # Simulate only a genuine signed phone result; no button/text can supply this in production.
        dialog.open_browser = lambda _: True
        dialog.advance()
        ceremony = dialog.ceremony
        self.ceremonies.append(ceremony)
        ceremony.complete(self.response(ceremony))
        authenticated = []
        dialog.authenticated.connect(authenticated.append)
        dialog.check_result()
        return dialog, listener, dialog.profile_session, authenticated

    def test_phone_then_separate_consent_pause_capture_review_and_atomic_commit(self):
        d, listener, session, authenticated = self.prepare()
        self.assertEqual(d.stage, 'profile_consent')
        self.assertFalse(authenticated)
        self.assertIsNone(d.capture_worker)
        d.handle_voice('I agree')
        listener.stop_voice.assert_called_once()
        self.assertTrue(d.private_capture)
        self.assertEqual(d.stage, 'face')
        for _ in range(6):
            d.guidance_finished()
            self.app.processEvents()
        self.assertEqual(d.stage, 'profile_review')
        self.assertFalse(d.private_capture)
        self.assertEqual(store.owner_profiles(session, self.db), {'face': [], 'voice': []})
        d.handle_voice('save my profiles')
        self.assertEqual(authenticated, [session])
        self.assertEqual(store.owner_profiles(session, self.db), profiles())
        self.assertTrue(d.closed)

    def test_online_listener_must_exit_before_models_or_sensors_start(self):
        d, listener, _, authenticated = self.prepare(alive=True)
        d.handle_voice('I agree')
        self.assertEqual(d.stage, 'pausing')
        self.assertIsNone(d.capture_worker)
        self.assertFalse(authenticated)
        listener.voice_thread.is_alive.return_value = False
        d.wait_listener()
        self.assertTrue(d.capture_worker.started)
        d.reject()
        listener.start_voice.assert_called_once_with(True)
        self.assertFalse(authenticated)

    def test_returning_signed_owner_does_not_recapture_saved_profiles(self):
        session = self.enroll()
        credential = store.get_owner_passkey(self.db)['credential']
        store.save_owner_profiles(session, credential, profiles(), consent=True, db_path=self.db)
        listener = Mock(voice_thread=None, cloud_voice=False, quitting=False)
        d = self.dialog(profile_setup=True, listener=listener, open_browser=lambda _: True,
                        capture_factory=lambda *_: self.fail('Returning sign-in must not open sensors'))
        authenticated = []
        d.authenticated.connect(authenticated.append)
        self.assertEqual(d.stage, 'phone')
        d.advance()
        ceremony = d.ceremony
        self.ceremonies.append(ceremony)
        ceremony.complete(self.response(ceremony))
        d.check_result()
        self.assertTrue(d.closed)
        self.assertEqual(len(authenticated), 1)
        self.assertEqual(authenticated[0].person_id, session.person_id)
        self.assertNotEqual(authenticated[0].id, session.id)
        self.assertIsNone(d.capture_worker)
        listener.stop_voice.assert_not_called()
        self.assertEqual(store.owner_profiles(authenticated[0], self.db), profiles())

    def test_cancel_hide_failure_and_expired_review_never_save_or_unlock(self):
        for reason in ('cancel', 'hide', 'failure', 'expired'):
            # Each scenario uses one fresh signed proof for the same synthetic phone owner.
            if reason == 'cancel':
                self.enroll()
            listener = Mock(voice_thread=None, cloud_voice=False, quitting=False)
            d = self.dialog(profile_setup=True, listener=listener, capture_factory=self.fake_capture(), open_browser=lambda _:True)
            d.advance()
            ceremony = d.ceremony
            self.ceremonies.append(ceremony)
            ceremony.complete(self.response(ceremony))
            d.check_result()
            session = d.profile_session
            authenticated = []
            d.authenticated.connect(authenticated.append)
            d.advance()
            if reason == 'cancel':
                d.reject()
            elif reason == 'hide':
                d.hide()
                self.app.processEvents()
            elif reason == 'failure':
                d.capture_worker.failed.emit()
            else:
                for _ in range(6):
                    d.guidance_finished()
                    self.app.processEvents()
                d.profile_session = replace(session, verified_until=time.time()-1)
                d.save_profiles()
            self.assertFalse(authenticated)
            self.assertEqual(store.owner_profiles(session, self.db), {'face': [], 'voice': []})
            self.assertFalse(any(d.capture_worker.samples.values()))
            self.assertIsNone(d.mark.preview)
            d.reject()

    def test_better_controls_and_no_voice_guidance_no_capture(self):
        d, _, _, _ = self.prepare()
        self.assertEqual(d.next.width(), 56)
        self.assertEqual(d.cancel.width(), 44)
        self.assertEqual(d.next.iconSize().width(), 24)
        self.assertEqual(d.next.text(), '')
        self.assertTrue(d.next.accessibleName())
        d.advance()
        d.voice_unavailable()
        d.guidance_finished()
        self.app.processEvents()
        self.assertEqual(d.stage, 'failed')
        self.assertFalse(any(d.capture_worker.samples.values()))

    def test_failure_reason_is_spoken_instead_of_only_hidden_in_body(self):
        d, _, session, authenticated = self.prepare()
        d.advance()
        d.capture_worker.failure_reason = 'The speech sample was too faint for a reliable voice profile.'
        d.capture_worker.failed.emit()
        self.assertIn('too faint',d.prompt)
        self.assertIn('phone credential remains registered',d.prompt)
        self.assertFalse(authenticated)
        self.assertEqual(store.owner_profiles(session,self.db),{'face':[],'voice':[]})

    def test_recoverable_sample_retry_keeps_phone_and_completed_views_without_restarting(self):
        d, listener, session, authenticated = self.prepare()
        d.advance()
        d.guidance_finished()
        self.app.processEvents()
        worker = d.capture_worker
        self.assertEqual(d.capture_step,1)
        for code in ('face_pose','face_blur'):
            worker.retry.emit(code)
            self.assertIs(d.capture_worker,worker)
            self.assertIs(d.profile_session,session)
            self.assertEqual(d.capture_step,1)
            self.assertEqual(len(worker.samples['face']),1)
            self.assertIsNone(d.ceremony)
            self.assertTrue(d.private_capture)
            self.assertIn('completed samples are kept',d.prompt)
            self.assertFalse(authenticated)
        worker.hint.emit('Hold still — capturing this view.')
        self.assertIn('Hold still',d.scan.feedback)
        listener.start_voice.assert_not_called()
        for _ in range(5):
            d.guidance_finished()
            self.app.processEvents()
        self.assertEqual(d.stage,'profile_review')
        d.handle_voice('save my profiles')
        self.assertEqual(store.owner_profiles(session,self.db),profiles())
        self.assertEqual(authenticated,[session])

    def test_retry_does_not_extend_expired_proof_or_run_after_close(self):
        d, _, session, authenticated = self.prepare()
        d.advance()
        d.profile_session = replace(session,verified_until=time.time()-1)
        d.capture_worker.retry.emit('face_pose')
        self.assertEqual(d.stage,'profile_refresh')
        self.assertFalse(d.private_capture)
        d.reject()
        d.retry_capture('face_pose')
        self.assertTrue(d.closed)
        self.assertFalse(authenticated)

    def test_profile_expiry_explains_failure_without_extending_phone_authority(self):
        d, _, session, authenticated = self.prepare()
        d.advance()
        d.profile_session = replace(session,verified_until=time.time()-1)
        d.expired()
        self.assertEqual(d.stage,'profile_refresh')
        self.assertIn('phone proof expired',d.prompt)
        self.assertFalse(authenticated)
        self.assertFalse(any(d.capture_worker.samples.values()))
        self.assertLess(d.profile_session.verified_until,time.time())
        self.assertEqual(d.resume_samples,{'face':[],'voice':[]})
        self.assertEqual(store.owner_profiles(session,self.db),{'face':[],'voice':[]})

    def test_expired_after_face_resumes_voice_only_after_same_owner_signed_phone_proof(self):
        d, listener, session, authenticated = self.prepare()
        d.advance()
        for _ in range(3):
            d.guidance_finished()
            self.app.processEvents()
        self.assertEqual(d.stage,'voice')
        d.profile_session = replace(session,verified_until=time.time()-1)
        old_worker = d.capture_worker
        d.expired()
        self.assertEqual(d.stage,'profile_refresh')
        self.assertFalse(d.private_capture)
        self.assertTrue(old_worker.closing)
        self.assertEqual(len(d.resume_samples['face']),3)
        self.assertEqual(d.resume_samples['voice'],[])
        self.assertFalse(authenticated)
        d.handle_voice('save my profiles')
        self.assertEqual(store.owner_profiles(session,self.db),{'face':[],'voice':[]})
        d.handle_voice('continue with phone')
        ceremony = d.ceremony
        self.ceremonies.append(ceremony)
        ceremony.complete(self.response(ceremony))
        d.check_result()
        self.assertEqual(d.capture_step,3)
        self.assertEqual(d.stage,'voice')
        self.assertEqual(d.capture_worker.samples['face'],profiles()['face'])
        self.assertIsNone(d.resume_samples)
        with patch.object(listener,'start_voice') as restart:
            old_worker.stopped.emit()
            restart.assert_not_called()
        for _ in range(3):
            d.guidance_finished()
            self.app.processEvents()
        self.assertEqual(d.stage,'profile_review')
        d.handle_voice('save my profiles')
        self.assertEqual(len(authenticated),1)
        self.assertNotEqual(authenticated[0].id,session.id)
        self.assertEqual(store.owner_profiles(authenticated[0],self.db),profiles())

    def test_expiry_resume_cancel_deadline_and_different_owner_or_credential_fail_closed(self):
        from fido2.webauthn import AttestedCredentialData
        self.enroll()
        for mode in ('cancel','deadline','person','credential'):
            with self.subTest(mode=mode):
                # Reuse the same synthetic registered owner, never a real store.
                d = self.dialog(profile_setup=True,listener=Mock(voice_thread=None,cloud_voice=False,quitting=False),
                                capture_factory=self.fake_capture(),open_browser=lambda _:True)
                d.advance()
                ceremony = d.ceremony
                self.ceremonies.append(ceremony)
                ceremony.complete(self.response(ceremony))
                d.check_result()
                session = d.profile_session
                authenticated = []
                d.authenticated.connect(authenticated.append)
                d.advance()
                d.capture_worker.samples = profiles()
                d.capture_step = 6
                d.stage = 'profile_review'
                d.profile_session = replace(session,verified_until=time.time()-1)
                d.expired()
                self.assertEqual(d.stage,'profile_refresh')
                if mode=='cancel':
                    d.hide()
                    self.app.processEvents()
                else:
                    d.advance()
                    ceremony = d.ceremony
                    self.ceremonies.append(ceremony)
                    ceremony.complete(self.response(ceremony))
                    if mode=='deadline':d.resume_until=time.monotonic()-1
                    elif mode=='person':ceremony.result=replace(ceremony.result,person_id='different-owner')
                    else:ceremony.credential=AttestedCredentialData.create(bytes(16),b'different-credential',self.credential.public_key)
                    d.check_result()
                    self.assertEqual(d.stage,'failed')
                self.assertIsNone(d.resume_samples)
                self.assertFalse(any(d.capture_worker.samples.values()))
                self.assertFalse(authenticated)
                self.assertEqual(store.owner_profiles(session,self.db),{'face':[],'voice':[]})
                d.reject()

    def test_resume_keeps_completed_voice_samples_and_final_review_needs_no_capture(self):
        d, _, session, authenticated = self.prepare()
        d.advance()
        for _ in range(4):
            d.guidance_finished()
            self.app.processEvents()
        self.assertEqual(d.capture_step,4)
        d.profile_session = replace(session,verified_until=time.time()-1)
        d.expired()
        d.advance()
        ceremony = d.ceremony
        self.ceremonies.append(ceremony)
        ceremony.complete(self.response(ceremony))
        d.check_result()
        self.assertEqual(d.capture_step,4)
        self.assertEqual(len(d.capture_worker.samples['voice']),1)
        for _ in range(2):
            d.guidance_finished()
            self.app.processEvents()
        self.assertEqual(d.stage,'profile_review')
        d.profile_session = replace(d.profile_session,verified_until=time.time()-1)
        d.expired()
        d.advance()
        ceremony = d.ceremony
        self.ceremonies.append(ceremony)
        ceremony.complete(self.response(ceremony))
        d.check_result()
        self.assertEqual(d.stage,'profile_review')
        self.assertFalse(d.capture_worker.started)
        self.assertEqual(d.capture_worker.samples,profiles())
        d.advance()
        self.assertEqual(len(authenticated),1)
        self.assertEqual(store.owner_profiles(authenticated[0],self.db),profiles())

    def test_partial_face_group_restarts_only_after_fresh_proof(self):
        d, _, session, authenticated = self.prepare()
        d.advance()
        for _ in range(2):
            d.guidance_finished()
            self.app.processEvents()
        d.profile_session = replace(session,verified_until=time.time()-1)
        d.expired()
        self.assertEqual(d.resume_samples,{'face':[],'voice':[]})
        d.advance()
        ceremony = d.ceremony
        self.ceremonies.append(ceremony)
        ceremony.complete(self.response(ceremony))
        d.check_result()
        self.assertEqual(d.stage,'face')
        self.assertEqual(d.capture_step,0)
        self.assertFalse(authenticated)

    def test_resuming_waits_for_previous_worker_exit_and_ignores_its_late_signals(self):
        from PySide6.QtCore import QProcess
        d, listener, session, _ = self.prepare()
        d.advance()
        for _ in range(3):
            d.guidance_finished()
            self.app.processEvents()
        old_worker = d.capture_worker
        old_worker.process = Mock()
        old_worker.process.state.return_value = QProcess.ProcessState.Running
        d.profile_session = replace(session,verified_until=time.time()-1)
        d.expired()
        d.advance()
        ceremony = d.ceremony
        self.ceremonies.append(ceremony)
        ceremony.complete(self.response(ceremony))
        d.check_result()
        self.assertEqual(d.stage,'pausing')
        self.assertIs(d.capture_worker,old_worker)
        with patch.object(listener,'start_voice') as restart:
            old_worker.stopped.emit()
            restart.assert_not_called()
        old_worker.process.state.return_value = QProcess.ProcessState.NotRunning
        d.wait_listener()
        self.assertEqual(d.stage,'voice')
        self.assertIsNot(d.capture_worker,old_worker)
        with patch.object(listener,'start_voice') as restart:
            old_worker.stopped.emit()
            restart.assert_not_called()

    def test_face_stage_expands_only_after_consent_and_restores_for_voice(self):
        from PySide6.QtGui import QImage
        d, _, _, _ = self.prepare()
        compact = d.geometry()
        self.assertFalse(d.scan.isVisible())
        d.advance()
        self.assertTrue(d.scan.isVisible())
        self.assertFalse(d.mark.isVisible())
        self.assertFalse(d.next.isVisible())
        self.assertFalse(d.repeat.isVisible())
        self.assertTrue(d.cancel.isVisible())
        self.assertGreater(d.width(), compact.width())
        self.assertTrue(d.screen().availableGeometry().contains(d.geometry()))
        image = QImage(320, 240, QImage.Format.Format_RGB32)
        image.fill(0)
        d.capture_worker.preview.emit(image)
        d.capture_worker.tracking.emit(dict(faces=1, box=[.2,.1,.5,.8], points=[[.4,.4]]*5))
        self.assertIsNotNone(d.scan.image)
        self.assertEqual(d.scan.tracking['faces'], 1)
        for width, height in ((320,280), (1000,600), (1280,760)):
            d.resize(width, height)
            self.app.processEvents()
            self.assertTrue(d.scan.rect().contains(d.scan.camera_rect().toAlignedRect()))
            self.assertFalse(d.grab().isNull())
        for _ in range(3):
            d.guidance_finished()
            self.app.processEvents()
        self.assertEqual(d.stage, 'voice')
        self.assertFalse(d.scan.isVisible())
        self.assertTrue(d.mark.isVisible())
        self.assertTrue(d.next.isVisible())
        self.assertTrue(d.repeat.isVisible())
        self.assertEqual(d.geometry(), compact)
        self.assertIsNone(d.scan.image)
        self.assertIsNone(d.scan.tracking)

    def test_hidden_face_stage_clears_frames_tracking_and_animation(self):
        from PySide6.QtGui import QImage
        d, _, session, authenticated = self.prepare()
        d.advance()
        d.scan.timer.start()
        d.show_preview(QImage(320, 240, QImage.Format.Format_RGB32))
        d.show_tracking(dict(faces=0, box=[], points=[]))
        d.hide()
        self.app.processEvents()
        self.assertFalse(d.scan.timer.isActive())
        self.assertIsNone(d.scan.image)
        self.assertIsNone(d.scan.tracking)
        d.show_preview(QImage(320, 240, QImage.Format.Format_RGB32))
        d.show_tracking(dict(faces=0, box=[], points=[]))
        self.assertIsNone(d.scan.image)
        self.assertIsNone(d.scan.tracking)
        self.assertFalse(authenticated)
        self.assertEqual(store.owner_profiles(session, self.db), {'face': [], 'voice': []})

    def test_capture_waits_for_successful_current_guidance_and_tray_cannot_restart_hearing(self):
        d, _, _, _ = self.prepare()
        d.advance()
        d.guidance_finished()
        d.speech.request += 1
        self.app.processEvents()
        self.assertFalse(any(d.capture_worker.samples.values()))
        d.speech.busy = True
        d.guidance_finished()
        self.app.processEvents()
        self.assertFalse(any(d.capture_worker.samples.values()))
        d.speech.busy = False
        from experience import OrbDesktop
        desktop = OrbDesktop(self.app, reduced_motion=True)
        desktop.brain.db_path = self.db
        self.addCleanup(desktop.quit)
        desktop.owner_dialog = Mock(private_capture=True)
        with patch('app.Desktop.start_voice') as start:
            desktop.start_voice(True)
            start.assert_not_called()
            desktop.owner_dialog.private_capture = False
            desktop.start_voice(True)
            start.assert_called_once_with(True)


class WorkerBoundaryChecks(unittest.TestCase):
    def test_actual_child_retries_quality_and_mismatch_without_skipping_or_reloading(self):
        import tempfile
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from desktop.owner_biometrics import OwnerCapture,ROOT
        app = QApplication.instance() or QApplication([])
        worker = OwnerCapture(Session(role='admin',person_id='synthetic',id='synthetic',verified_until=time.time()+30))
        self.addCleanup(worker.stop)
        retries,events,failures,stopped = [],[],[],[]
        worker.ready.connect(lambda:worker.capture('face',0))
        def retry(code):
            retries.append(code)
            kind='face' if len(worker.samples['face'])<3 else 'voice'
            worker.capture(kind,len(worker.samples[kind]))
        def captured(kind,index):
            events.append((kind,index))
            if len(events)<6:
                kind='face' if len(worker.samples['face'])<3 else 'voice'
                worker.capture(kind,len(worker.samples[kind]))
        worker.retry.connect(retry)
        worker.sample.connect(captured)
        worker.failed.connect(lambda:failures.append(worker.failure_reason))
        worker.stopped.connect(lambda:stopped.append(True))
        with tempfile.TemporaryDirectory(prefix='lya-retry-pipe-') as temp:
            script=Path(temp)/'synthetic_capture.py'
            script.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\n'
                'from security import owner_capture as worker\n'
                'class FakeCapture:\n'
                '    def __init__(self): self.calls={}\n'
                '    def sample(self,kind,index,n):\n'
                '        key=(kind,index); self.calls[key]=self.calls.get(key,0)+1\n'
                '        if self.calls[key]==1 and index==0: raise RuntimeError("face_pose" if kind=="face" else "voice_quiet")\n'
                '        if self.calls[key]==1 and index in (1,2): return [0.,1.]+[0.]*(n-2)\n'
                '        return [1.]+[0.]*(n-1)\n'
                '    def face_sample(self,index,valid): return self.sample("face",index,128)\n'
                '    def voice_sample(self,valid): return self.sample("voice",worker_test_index(),256)\n'
                'def worker_test_index():\n'
                '    return min(2,len([k for k,v in capture.calls.items() if k[0]=="voice" and v>=2]))\n'
                'capture=FakeCapture()\nworker.Capture=lambda:capture\nworker.run(float(sys.argv[1]),int(sys.argv[2]))\n',encoding='utf-8')
            original_start=worker.process.start
            with patch.object(worker.process,'start',side_effect=lambda python,args:original_start(python,[str(script),*args[1:]])):
                worker.start()
            until=time.monotonic()+10
            while not stopped and time.monotonic()<until:QTest.qWait(25)
            worker.process.waitForFinished(1000)
        self.assertTrue(stopped)
        self.assertFalse(failures)
        self.assertEqual(retries,['face_pose','face_mismatch','face_mismatch','voice_quiet','voice_mismatch','voice_mismatch'])
        self.assertEqual(events,[('face',0),('face',1),('face',2),('voice',0),('voice',1),('voice',2)])
        self.assertEqual(worker.samples,profiles())
        app.processEvents()

    def test_actual_child_protocol_resumes_voice_without_a_camera_command(self):
        import tempfile
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from desktop.owner_biometrics import OwnerCapture,ROOT
        app = QApplication.instance() or QApplication([])
        worker = OwnerCapture(Session(role='admin',person_id='synthetic',id='synthetic',verified_until=time.time()+30))
        self.addCleanup(worker.stop)
        worker.samples['face'] = profiles()['face']
        events,failures,stopped = [],[],[]
        worker.ready.connect(lambda:worker.capture('voice',0))
        def captured(kind,index):
            events.append((kind,index))
            if index<2:worker.capture('voice',index+1)
        worker.sample.connect(captured)
        worker.failed.connect(lambda:failures.append(worker.failure_reason))
        worker.stopped.connect(lambda:stopped.append(True))
        with tempfile.TemporaryDirectory(prefix='lya-resume-pipe-') as temp:
            script = Path(temp)/'synthetic_capture.py'
            script.write_text('import sys\nsys.path.insert(0,'+repr(str(ROOT))+')\n'
                'from security import owner_capture as worker\n'
                'class FakeCapture:\n'
                '    def face_sample(self,*_): raise AssertionError("Camera must not open on voice resume")\n'
                '    def voice_sample(self,*_): return [1.0]+[0.0]*255\n'
                'worker.Capture=FakeCapture\nworker.run(float(sys.argv[1]),int(sys.argv[2]))\n',encoding='utf-8')
            original_start = worker.process.start
            def start(python,args):
                return original_start(python,[str(script),*args[1:]])
            with patch.object(worker.process,'start',side_effect=start):
                worker.start()
            until = time.monotonic()+10
            while not stopped and time.monotonic()<until:QTest.qWait(25)
            worker.process.waitForFinished(1000)
        self.assertTrue(stopped)
        self.assertFalse(failures)
        self.assertEqual(events,[('voice',0),('voice',1),('voice',2)])
        self.assertEqual(worker.initial_step,3)
        self.assertEqual(worker.samples,profiles())
        app.processEvents()

    def test_expired_worker_preserves_only_completed_samples_until_native_pause_decision(self):
        from PySide6.QtWidgets import QApplication
        from desktop.owner_biometrics import OwnerCapture
        app = QApplication.instance() or QApplication([])
        worker = OwnerCapture(Session(role='admin',person_id='synthetic',id='synthetic',verified_until=time.time()-1))
        self.addCleanup(worker.stop)
        worker.samples['face'] = profiles()['face']
        worker.abort()
        self.assertEqual(worker.failure_code,'expired')
        self.assertEqual(worker.samples['face'],profiles()['face'])
        self.assertTrue(worker.closing)
        worker.stop()
        self.assertFalse(any(worker.samples.values()))
        app.processEvents()

    def test_voice_prepares_vad_before_stream_and_measures_speech_not_waiting_silence(self):
        import sys
        import numpy as np
        from security import owner_capture
        from audio import voice
        capture = owner_capture.Capture.__new__(owner_capture.Capture)
        capture.preprocess = Mock(return_value=np.full(32000,.004,dtype=np.float32))
        capture.voice = Mock()
        capture.voice.embed_utterance.return_value = np.array(profiles()['voice'][0])
        class Stream:
            opened = False
            offset = 0
            closed = False
            blocks = []
            def __enter__(self):
                self.opened = True
                return self
            def __exit__(self,*_):
                self.closed = True
            def read(self,n):
                # A hesitant start must not dilute an otherwise usable two-second sample.
                chunk = np.full((n,1),.004 if 170 <= self.offset < 190 else 0.,dtype=np.float32)
                self.offset += 1
                self.blocks.append(chunk)
                return chunk,False
        stream = Stream()
        class Vad:
            def __init__(self,*_):
                if stream.opened:
                    raise AssertionError('VAD initialization must precede microphone acquisition.')
            def is_speech(self,pcm,_):
                return any(pcm)
        with patch.dict(sys.modules,{'webrtcvad':Mock(Vad=Vad)}), \
             patch.object(voice,'_input_device',return_value=17), patch.object(owner_capture,'emit'):
            result = capture.voice_sample(lambda:True,stream_factory=lambda **_:stream)
        self.assertEqual(result,profiles()['voice'][0])
        self.assertTrue(stream.closed)
        self.assertEqual(stream.offset,200)
        self.assertEqual(capture.preprocess.call_count,1)

    def test_camera_preview_is_bounded_but_not_limited_to_two_frames_a_second(self):
        import base64
        import cv2
        import numpy as np
        from security import owner_capture
        capture = owner_capture.Capture.__new__(owner_capture.Capture)
        capture.detector = Mock()
        capture.detector.detect.return_value = (None,None)
        camera = Mock()
        camera.isOpened.return_value = True
        ticks = [0.]
        def read():
            ticks[0] += .12
            return True,np.zeros((480,640,3),dtype=np.uint8)
        camera.read.side_effect = read
        with patch.object(owner_capture,'emit') as emit, \
             patch.object(owner_capture.time,'monotonic',side_effect=lambda:ticks[0]), \
             patch.object(owner_capture.time,'sleep'):
            with self.assertRaises(RuntimeError):
                capture.face_sample(0,lambda:camera.read.call_count<6,camera_factory=lambda:camera)
        previews = [c.kwargs for c in emit.call_args_list if c.args==('preview',)]
        self.assertGreaterEqual(len(previews),5)
        self.assertLessEqual(len(previews),6)
        decoded = cv2.imdecode(np.frombuffer(base64.b64decode(previews[0]['image']),np.uint8),cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape[:2],(480,640))
        camera.release.assert_called_once()

    def test_camera_explains_quality_gate_and_still_requires_sharp_aligned_views(self):
        import numpy as np
        from security import owner_capture
        good_face=[150.,80.,200.,300.,200.,180.,300.,180.,250.,230.,215.,300.,285.,300.,.99]
        sharp=np.repeat(((np.indices((480,640)).sum(axis=0)%2)*100+60).astype(np.uint8)[:,:,None],3,axis=2)
        for mode,code in (('missing','face_missing'),('multiple','face_multiple'),('position','face_position'),
                          ('pose','face_pose'),('light','face_light'),('blur','face_blur'),('good',None)):
            with self.subTest(mode=mode):
                capture=owner_capture.Capture.__new__(owner_capture.Capture)
                face=good_face[:]
                if mode=='position':face[0]=0.
                if mode=='pose':face[8]=290.
                capture.detector=Mock()
                capture.detector.detect.return_value=(None,None if mode=='missing' else [face,face] if mode=='multiple' else [face])
                capture.face=Mock()
                capture.face.feature.return_value=np.array(profiles()['face'][0])
                frame=np.zeros_like(sharp) if mode=='light' else np.full_like(sharp,100) if mode=='blur' else sharp
                ticks=[0.]
                camera=Mock()
                camera.isOpened.return_value=True
                def read():
                    ticks[0]+=2.
                    return True,frame
                camera.read.side_effect=read
                with patch.object(owner_capture.time,'monotonic',side_effect=lambda:ticks[0]), \
                     patch.object(owner_capture.time,'sleep'),patch.object(owner_capture,'emit') as emit:
                    if code:
                        with self.assertRaisesRegex(RuntimeError,code):
                            capture.face_sample(0,lambda:True,camera_factory=lambda:camera)
                        capture.face.feature.assert_not_called()
                        self.assertIn(unittest.mock.call('hint',code=code),emit.call_args_list)
                    else:
                        self.assertEqual(capture.face_sample(0,lambda:True,camera_factory=lambda:camera),profiles()['face'][0])
                        self.assertEqual(capture.face.feature.call_count,3)
                camera.release.assert_called_once()

    def test_voice_silence_clipping_and_overflow_still_fail_closed_and_close_stream(self):
        import sys
        import numpy as np
        from security import owner_capture
        from audio import voice
        class Vad:
            def __init__(self,*_):pass
            def is_speech(self,pcm,_):return any(pcm)
        for mode,code in (('silent','voice_no_speech'),('clipped','voice_clipped'),('overflow','audio_overflow')):
            with self.subTest(mode=mode):
                capture = owner_capture.Capture.__new__(owner_capture.Capture)
                capture.preprocess,capture.voice = Mock(),Mock()
                class Stream:
                    count = 0
                    closed = False
                    def __enter__(self):return self
                    def __exit__(self,*_):self.closed=True
                    def read(self,n):
                        self.count += 1
                        return np.full((n,1),1. if mode=='clipped' else 0.,dtype=np.float32),mode=='overflow'
                stream = Stream()
                with patch.dict(sys.modules,{'webrtcvad':Mock(Vad=Vad)}), \
                     patch.object(voice,'_input_device',return_value=17), patch.object(owner_capture,'emit'):
                    with self.assertRaisesRegex(RuntimeError,code):
                        capture.voice_sample(lambda:True,stream_factory=lambda **_:stream)
                self.assertTrue(stream.closed)
                capture.preprocess.assert_not_called()
                capture.voice.embed_utterance.assert_not_called()

    def test_camera_loop_emits_tracking_and_releases_without_saving_frames(self):
        import numpy as np
        from security import owner_capture
        capture = owner_capture.Capture.__new__(owner_capture.Capture)
        face = [64.,48.,320.,384.,128.,192.,320.,192.,224.,240.,160.,336.,288.,336.,.99]
        capture.detector = Mock()
        capture.detector.detect.return_value = (None,[face])
        camera = Mock()
        camera.isOpened.return_value = True
        camera.read.return_value = (True,np.zeros((480,640,3),dtype=np.uint8))
        valid = Mock(side_effect=[True,True,True,False])
        with patch.object(owner_capture,'emit') as emit, patch.object(owner_capture.time,'sleep'):
            with self.assertRaises(RuntimeError):
                capture.face_sample(0,valid,camera_factory=lambda:camera)
        camera.release.assert_called_once()
        packet = emit.call_args_list[0]
        self.assertEqual(packet.args, ('preview',))
        self.assertEqual(packet.kwargs['tracking'], owner_capture.face_tracking([face]))
        self.assertIn('image', packet.kwargs)

    def test_preview_coordinates_mirror_the_same_camera_frame(self):
        from security.owner_capture import face_tracking
        face = [64.,48.,320.,384., 128.,192., 320.,192., 224.,240., 160.,336., 288.,336., .99]
        data = face_tracking([face])
        self.assertEqual(data['faces'], 1)
        for actual, expected in zip(data['box'], [.4,.1,.5,.8]):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(data['points'][0], [.8,.4])
        self.assertEqual(data['points'][2], [.65,.5])
        for faces, count in ((None,0), ([],0), ([face,face,face],2)):
            self.assertEqual(face_tracking(faces), dict(faces=count,box=[],points=[]))

    def test_tracking_packets_reject_false_counts_unbounded_and_nonfinite_points(self):
        import base64
        from PySide6.QtCore import QBuffer, QByteArray
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QApplication
        from desktop.owner_biometrics import OwnerCapture
        app = QApplication.instance() or QApplication([])
        worker = OwnerCapture(Session(role='admin', person_id='synthetic', id='synthetic', verified_until=time.time()+60))
        self.addCleanup(worker.stop)
        worker.pending = ('face',0)
        image = QImage(320,240,QImage.Format.Format_RGB32)
        image.fill(0)
        raw = QByteArray()
        buffer = QBuffer(raw)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer,'JPG')
        packet = dict(kind='preview', image=base64.b64encode(bytes(raw)).decode('ascii'))
        good = dict(faces=1, box=[.2,.1,.5,.8], points=[[.4,.4]]*5)
        received = []
        worker.tracking.connect(received.append)
        for invalid in (None, dict(good,faces=True), dict(good,faces=3), dict(good,box=[.9,.1,.5,.8]),
                        dict(good,points=[[float('nan'),.4]]*5), dict(good,points=[[1.1,.4]]*5),
                        dict(good,points=[[.4,.4]]*6), dict(good,faces=0), dict(good,depth=1)):
            with self.assertRaises(ValueError):
                worker.handle_packet(dict(packet,tracking=invalid))
        self.assertFalse(received)
        worker.handle_packet(dict(packet,tracking=good))
        self.assertEqual(received, [good])
        large = QImage(640,480,QImage.Format.Format_RGB32)
        large.fill(0)
        raw.clear()
        buffer.seek(0)
        large.save(buffer,'JPG')
        worker.handle_packet(dict(packet,image=base64.b64encode(bytes(raw)).decode('ascii'),tracking=good))
        self.assertEqual(received,[good,good])
        worker.stop()
        self.assertIsNone(received[-1])
        app.processEvents()

    def test_no_network_child_process_or_plaintext_file_write(self):
        from security.owner_capture import guard
        for event, args in [('socket.connect', ()), ('subprocess.Popen', ()),
                            ('open', ('synthetic.wav','wb',0)), ('open', ('data',None,2))]:
            with self.assertRaises(PermissionError):
                guard(event,args)
        guard('open', ('model.onnx','rb',0))

    def test_strict_vector_and_pipe_packets(self):
        from PySide6.QtWidgets import QApplication
        from desktop.owner_biometrics import OwnerCapture
        app = QApplication.instance() or QApplication([])
        worker = OwnerCapture(Session(role='admin', person_id='synthetic', id='synthetic', verified_until=time.time()+60))
        self.addCleanup(worker.stop)
        worker.pending = ('voice',0)
        for data in ({'kind':'sample','profile':'voice','index':False,'vector':profiles()['voice'][0]},
                {'kind':'meter','level':float('nan')}, {'kind':'sample','profile':'face','index':0,'vector':profiles()['face'][0]},
                {'kind':'done'}, {'kind':'preview','image':'invalid'}):
            with self.assertRaises(ValueError):
                worker.handle_packet(data)
        self.assertFalse(any(worker.samples.values()))
        worker.handle_packet({'kind':'sample','profile':'voice','index':0,'vector':profiles()['voice'][0]})
        self.assertEqual(len(worker.samples['voice']), 1)
        with self.assertRaises(ValueError):
            checked_vector([0.0]*128, FACE_MODEL)
        app.processEvents()

    def test_worker_errors_are_fixed_categories_and_never_raw_device_text(self):
        from PySide6.QtWidgets import QApplication
        from desktop.owner_biometrics import OwnerCapture
        app = QApplication.instance() or QApplication([])
        worker = OwnerCapture(Session(role='admin',person_id='synthetic',id='synthetic',verified_until=time.time()+60))
        self.addCleanup(worker.stop)
        failures = []
        worker.failed.connect(lambda:failures.append(worker.failure_reason))
        for packet in (dict(kind='error',code='native path or secret'),dict(kind='error',code=['voice_quiet']),
                       dict(kind='error',code='voice_quiet',detail='private device text')):
            with self.assertRaises(ValueError):worker.handle_packet(packet)
        self.assertFalse(failures)
        worker.handle_packet(dict(kind='error',code='voice_quiet'))
        self.assertEqual(len(failures),1)
        self.assertIn('too faint',failures[0])
        self.assertTrue(worker.closing)
        self.assertFalse(any(worker.samples.values()))
        app.processEvents()

    def test_synthetic_camera_releases_on_lease_loss_and_mic_never_reads_after_loss(self):
        import numpy as np
        from security.owner_capture import Capture
        capture = Capture.__new__(Capture)
        camera = Mock()
        camera.isOpened.return_value = True
        with self.assertRaises(RuntimeError):
            capture.face_sample(0, lambda:False, camera_factory=lambda:camera)
        camera.isOpened.assert_not_called()
        camera.release.assert_not_called()
        stream = Mock()
        stream.__enter__ = Mock(return_value=stream)
        stream.__exit__ = Mock(return_value=False)
        with self.assertRaises(RuntimeError):
            capture.voice_sample(lambda:False, stream_factory=lambda **_:stream)
        stream.read.assert_not_called()
        stream.__enter__.assert_not_called()


if __name__ == '__main__':
    unittest.main()
