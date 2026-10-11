"""Synthetic keys, faces/devices and temporary stores; no owner collection or launches."""
from dataclasses import replace
from pathlib import Path
import time
import unittest
from unittest.mock import Mock,patch
from test_passkeys import SyntheticPasskeys
from test_owner_profiles import profiles
from security.visitors import Visitors
from storage import store,visitors
from brain.workflow import Brain


def vector(index=0):
    return [1. if i==index else 0. for i in range(128)]


class VisitorChecks(SyntheticPasskeys,unittest.TestCase):
    def owner(self,enabled=False):
        session=self.enroll()
        store.save_owner_profiles(session,store.get_owner_passkey(self.db)['credential'],profiles(),
            consent=True,db_path=self.db,startup_recognition=enabled)
        return session

    def guest(self):
        return Brain(client=lambda _:'Public answer',db_path=self.db)

    def test_consent_required_and_reads_preserve_store(self):
        owner=self.owner()
        before=self.db.read_bytes()
        self.assertEqual(visitors.recognition_people(self.db),[])
        self.assertEqual(before,self.db.read_bytes())
        visitors.set_enabled(owner,True,self.db)
        before=self.db.read_bytes()
        self.assertEqual(visitors.recognition_people(self.db)[0]['person_id'],owner.person_id)
        self.assertEqual(before,self.db.read_bytes())
        visitors.set_enabled(owner,False,self.db)
        self.assertEqual(visitors.recognition_people(self.db),[])

    def test_public_owner_question_needs_no_approval_and_private_context_never_leaks(self):
        owner=self.owner(True)
        store.remember(owner.person_id,'private fixture','SYNTHETIC_OWNER_ONLY',db_path=self.db)
        calls=[]
        brain=Brain(owner,approve=lambda *a:self.fail('Public text must not ask for phone proof'),
                    client=lambda messages:calls.append(messages) or 'Public answer',db_path=self.db)
        self.assertEqual(brain.respond('Write an assignment about the moon.').text,'Public answer')
        self.assertNotIn('SYNTHETIC_OWNER_ONLY',str(calls))
        brain.approve=lambda *a:False
        self.assertEqual(brain.respond('using my memory explain private fixture').route,'blocked')
        brain.bind_session(replace(owner,verified_until=time.time()-1))
        self.assertEqual(brain.respond('Explain the stars.').text,'Public answer')
        self.assertIsNone(brain.session.person_id)

    def test_owner_tone_is_personal_without_sending_identity_or_private_data(self):
        owner=self.owner(True)
        calls=[]
        brain=Brain(owner,client=lambda messages:calls.append(messages) or 'Hello, {LYA_OWNER_NAME}.',db_path=self.db)
        self.assertEqual(brain.respond('Explain the stars.').text,'Hello, '+owner.person+'.')
        self.assertIn('phone-verified owner',calls[-1][0]['content'])
        self.assertIn('placeholder {LYA_OWNER_NAME}',calls[-1][0]['content'])
        self.assertNotIn(owner.person_id,str(calls))
        self.assertNotIn(owner.person,str(calls))
        brain.bind_session(replace(owner,verified_until=time.time()-1))
        brain.respond('Explain the stars.')
        self.assertNotIn('CONVERSATION STYLE:',calls[-1][0]['content'])
        brain.visitors.observe(vector(),visitors.recognition_people(self.db))
        brain.respond('Explain the stars.')
        self.assertIn('does not verify owner authority',calls[-1][0]['content'])
        self.assertFalse(brain._identified())
        self.assertEqual(brain.respond('show my saved data').route,'blocked')
        brain.visitors.end_presence()
        brain.respond('Explain the stars.')
        self.assertNotIn('CONVERSATION STYLE:',calls[-1][0]['content'])

    def test_saved_data_summary_requires_owner_approval_and_never_exports_templates(self):
        owner=self.owner(True)
        before=self.db.read_bytes()
        summary=store.owner_profile_summary(owner,self.db)
        self.assertEqual(summary['face'],3)
        self.assertEqual(summary['voice'],3)
        self.assertTrue(summary['consent'])
        self.assertEqual(before,self.db.read_bytes())
        self.assertNotIn('credential',summary)
        self.assertNotIn('embedding',summary)
        brain=Brain(owner,approve=lambda *a:False,client=lambda _:self.fail('Summary must stay local'),db_path=self.db)
        self.assertEqual(brain.respond('show my saved data').route,'blocked')
        brain.approve=lambda *a:True
        answer=brain.respond('show my saved data')
        self.assertEqual(answer.route,'local')
        self.assertIn('Face profiles: 3 of 3',answer.text)
        self.assertIn(str(self.db),answer.text)
        self.assertNotIn(str(profiles()['face'][0]),answer.text)
        with self.assertRaises(PermissionError):store.owner_profile_summary(replace(owner,verified_until=time.time()-1),self.db)

    def test_three_levels_never_make_face_an_owner_session(self):
        owner=self.owner(True)
        friend=visitors.register(owner,'Synthetic friend',vector(1),self.db)
        brain=self.guest()
        original=brain.session
        for face,pid in ((vector(),owner.person_id),(vector(1),friend),(vector(2),None)):
            person=brain.visitors.observe(face,visitors.recognition_people(self.db))
            self.assertEqual(person['person_id'] if person else None,pid)
            self.assertEqual(brain.session,original)
            self.assertFalse(brain._identified())
            self.assertEqual(brain.respond('recall anything').route,'blocked')
            with patch('skills.limited_apps.launch',return_value='Opened calculator.') as launch:
                self.assertEqual(brain.respond('open calculator').route,'limited-app' if pid else 'blocked')
                self.assertEqual(launch.called,pid is not None)
            self.assertEqual(brain.respond('Write an assignment about the moon.').text,'Public answer')
        self.assertNotIn(b'Synthetic friend',self.db.read_bytes())

    def test_unknown_cannot_register_disable_remove_or_inject_apps(self):
        self.owner(True)
        brain=self.guest()
        brain.visitors.observe(vector(2),visitors.recognition_people(self.db))
        before=self.db.read_bytes()
        with patch('skills.limited_apps.launch') as launch:
            for text in ('register friend Unknown','remove friend Someone','disable startup recognition',
                         'open youtube && cmd.exe','open terminal','open file explorer'):
                self.assertEqual(brain.respond(text).route,'blocked',text)
            launch.assert_not_called()
        self.assertEqual(before,self.db.read_bytes())
        with self.assertRaises(PermissionError):visitors.save_summary(brain.session,brain.visitors.counts,self.db)

    def test_owner_explicitly_registers_unknown_and_cannot_remove_admin(self):
        owner=self.owner(True)
        brain=Brain(owner,approve=lambda *a:True,client=lambda _:'public',db_path=self.db)
        self.assertEqual(brain.respond('register friend Alice').route,'blocked')
        brain.visitors.observe(vector(1),visitors.recognition_people(self.db))
        self.assertEqual(brain.respond('register friend Alice').route,'local')
        self.assertIsNone(brain.visitors.pending)
        self.assertEqual(len(visitors.recognition_people(self.db)),2)
        self.assertEqual(brain.respond('remove friend '+owner.person).route,'blocked')
        self.assertEqual(brain.respond('remove friend Alice').route,'local')
        self.assertEqual(len(visitors.recognition_people(self.db)),1)

    def test_refused_changed_or_expired_observation_never_registers(self):
        owner=self.owner(True)
        brain=Brain(owner,approve=lambda *a:False,client=lambda _:'public',db_path=self.db)
        brain.visitors.observe(vector(1),visitors.recognition_people(self.db))
        self.assertEqual(brain.respond('register friend Alice').route,'blocked')
        def change(*args):
            brain.visitors.observe(vector(2),visitors.recognition_people(self.db))
            return True
        brain.approve=change
        self.assertEqual(brain.respond('register friend Alice').route,'blocked')
        self.assertEqual(len(visitors.recognition_people(self.db)),1)
        brain.visitors.pending['until']=time.time()-1
        self.assertEqual(brain.respond('register friend Alice').route,'blocked')
        self.assertIsNone(brain.visitors.pending)

    def test_revoked_or_disabled_recognition_never_launches(self):
        owner=self.owner(True)
        visitors.register(owner,'Alice',vector(1),self.db)
        brain=self.guest()
        brain.visitors.observe(vector(1),visitors.recognition_people(self.db))
        visitors.remove(owner,'Alice',self.db)
        with patch('skills.limited_apps.launch') as launch:
            self.assertEqual(brain.respond('open youtube').route,'blocked')
            launch.assert_not_called()
        brain.visitors.observe(vector(),visitors.recognition_people(self.db))
        visitors.set_enabled(owner,False,self.db)
        with patch('skills.limited_apps.launch') as launch:
            self.assertEqual(brain.respond('open calculator').route,'blocked')
            launch.assert_not_called()

    def test_summary_is_explicit_encrypted_counts_only_and_owner_bound(self):
        owner=self.owner(True)
        brain=self.guest()
        before=self.db.read_bytes()
        brain.respond('Write an assignment about synthetic confidential-string.')
        self.assertEqual(before,self.db.read_bytes())
        self.assertEqual(brain.visitors.counts['requests'],1)
        self.assertFalse(store.recall(owner.person_id,db_path=self.db))
        for invalid in (dict(requests=True,limited_apps=0,blocked=0),dict(brain.visitors.counts,raw_text='secret')):
            with self.assertRaises(ValueError):visitors.save_summary(owner,invalid,self.db)
        visitors.save_summary(owner,brain.visitors.counts,self.db)
        saved=store.recall(owner.person_id,db_path=self.db)
        self.assertEqual(len(saved),1)
        self.assertEqual(saved[0]['kind'],'private')
        self.assertNotIn('confidential-string',saved[0]['value'])
        with self.assertRaises(PermissionError):
            visitors.save_summary(replace(owner,verified_until=time.time()-1),brain.visitors.counts,self.db)


class FamiliarBoundaryChecks(unittest.TestCase):
    def test_ambiguity_expiry_caps_and_no_transcripts(self):
        now=[100.]
        state=Visitors(lambda:now[0])
        person=dict(person_id='synthetic',display_name='Fixture',role='admin',samples=[vector()])
        self.assertIsNone(state.observe(vector(),[person,dict(person,person_id='other')]))
        now[0]+=601
        with self.assertRaises(PermissionError):state.material()
        self.assertIsNotNone(state.observe(vector(),[person]))
        now[0]+=301
        self.assertIsNone(state.current())
        for _ in range(1100):state.record('requests')
        self.assertEqual(state.counts['requests'],1000)
        with self.assertRaises(ValueError):state.record('raw transcript')
        state.discard()
        self.assertFalse(any(state.counts.values()))

    def test_snapshot_cancellation_and_exact_bounded_capture(self):
        import numpy as np
        from security.familiar_capture import snapshot
        camera=Mock()
        with self.assertRaises(RuntimeError):snapshot(Mock(),Mock(),lambda:False,lambda:camera)
        camera.isOpened.assert_not_called()
        frame=np.ones((480,640,3),dtype=np.uint8)*100
        camera.isOpened.return_value=True
        camera.read.side_effect=lambda:(True,frame.copy())
        detector=Mock()
        detector.detect.return_value=(None,None)
        self.assertIsNone(snapshot(detector,Mock(),lambda:True,lambda:camera))
        self.assertEqual(camera.read.call_count,3)
        self.assertTrue(camera.release.called)
        self.assertEqual(detector.detect.call_count,1)

    def test_strict_worker_sequence_and_result_only_after_clean_exit(self):
        from PySide6.QtWidgets import QApplication
        from desktop.familiarity import FaceObservation
        app=QApplication.instance() or QApplication([])
        worker=FaceObservation()
        self.addCleanup(worker.stop)
        results=[]
        worker.result.connect(results.append)
        for data in ({'kind':'result','vector':vector()},{'kind':'camera','extra':1},[]):
            with self.assertRaises(ValueError):worker.packet(data)
        worker.packet(dict(kind='camera'))
        for bad in ([float('nan')]+[0.]*127,[0.]*128):
            with self.assertRaises(ValueError):worker.packet(dict(kind='result',vector=bad))
        worker.packet(dict(kind='result',vector=vector()))
        self.assertFalse(results)
        worker.finished(0,None)
        self.assertEqual(results,[vector()])
        self.assertIsNone(worker.vector)

    def test_launcher_has_fixed_urls_guest_mode_and_no_shell(self):
        from skills.limited_apps import launch
        with patch('skills.limited_apps.subprocess.Popen') as popen,patch.object(Path,'is_file',return_value=True):
            launch('youtube')
            command=popen.call_args.args[0]
            self.assertIn('--guest',command)
            self.assertEqual(command[-1],'https://www.youtube.com/')
            self.assertFalse(popen.call_args.kwargs.get('shell',False))
            with self.assertRaises(ValueError):launch('youtube;cmd.exe')


class FamiliarUIChecks(SyntheticPasskeys,unittest.TestCase):
    def setUp(self):
        super().setUp()
        from PySide6.QtWidgets import QApplication
        self.app=QApplication.instance() or QApplication([])
        self.app.setQuitOnLastWindowClosed(False)

    def desktop(self):
        from desktop.experience import OrbDesktop
        d=OrbDesktop(self.app,reduced_motion=True)
        d.brain.db_path=self.db
        self.addCleanup(d.quit)
        return d

    def test_startup_once_and_disabled_consent_no_worker(self):
        d=self.desktop()
        with patch('desktop.familiarity.FaceObservation.start') as start:
            d.start_intro()
            d.start_intro()
            self.app.processEvents()
            start.assert_not_called()
        owner=self.enroll()
        store.save_owner_profiles(owner,store.get_owner_passkey(self.db)['credential'],profiles(),consent=True,db_path=self.db,startup_recognition=True)
        d.startup_observation_done=False
        with patch('desktop.familiarity.FaceObservation.start') as start:
            d.start_intro()
            d.start_intro()
            self.app.processEvents()
            start.assert_called_once()
        d.startup_observation_done=False
        with patch('desktop.familiarity.FaceObservation.start') as start:
            d.start_intro()
            d.orb.hide()
            self.app.processEvents()
            start.assert_not_called()

    def test_observation_greets_without_owner_binding(self):
        owner=self.enroll()
        store.save_owner_profiles(owner,store.get_owner_passkey(self.db)['credential'],profiles(),consent=True,db_path=self.db,startup_recognition=True)
        d=self.desktop()
        original=d.brain.session
        d.orb.show()
        with patch.object(d,'speak_reply') as speak:
            d.show_camera_badge()
            self.assertTrue(d.camera_badge.isVisible())
            d.observed_person(vector(),visitors.recognition_people(self.db))
            self.assertEqual(d.brain.session,original)
            self.assertIsNone(d.camera_badge)
            self.assertIn(owner.person,d.greeting.text())
            speak.assert_called_once()

    def test_one_choice_review_save_discard_and_expiry(self):
        from desktop.familiarity import VisitorReview
        owner=self.enroll()
        d=self.desktop()
        d.brain.bind_session(owner)
        d.passkey_session_id=owner.id
        d.brain.visitors.record('requests')
        dialog=VisitorReview(d)
        self.addCleanup(dialog.reject)
        before=self.db.read_bytes()
        dialog.choose(False)
        self.assertFalse(any(d.brain.visitors.counts.values()))
        self.assertEqual(before,self.db.read_bytes())
        d.brain.visitors.record('requests')
        dialog=VisitorReview(d)
        self.addCleanup(dialog.reject)
        dialog.choose(True)
        self.assertEqual(len(store.recall(owner.person_id,db_path=self.db)),1)
        self.assertFalse(any(d.brain.visitors.counts.values()))
        d.brain.visitors.record('requests')
        dialog=VisitorReview(d)
        self.addCleanup(dialog.reject)
        d.brain.bind_session(replace(owner,verified_until=time.time()-1))
        dialog.choose(True)
        self.assertEqual(d.brain.visitors.counts['requests'],1)
        self.assertEqual(len(store.recall(owner.person_id,db_path=self.db)),1)


if __name__=='__main__':unittest.main()
