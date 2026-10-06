"""Isolated compact experience checks and synthetic previews; no live services."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QPainter, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from experience import OrbDesktop

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)
for font in ('segoeui.ttf', 'segoeuib.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)


class ExperienceChecks(unittest.TestCase):
    def test_system_dictation_prepares_composer_and_leaves_lya_microphone_off(self):
        with patch.object(self.d, 'start_voice') as start, \
             patch('sounddevice.RawInputStream', side_effect=AssertionError('unexpected recording')):
            self.d.prepare_system_dictation()
        start.assert_not_called()
        self.assertFalse(self.d.voice_action.isChecked())
        self.assertEqual(self.d.panel.mode, 'chat')
        self.assertTrue(self.d.panel.entry.isVisible())
        self.assertIn('PRESS ENTER', self.d.panel.footnote.text())

    def test_quit_waits_for_recovery_cancellation_without_blocking(self):
        self.d.command('open recovery')
        dialog = self.d.recovery_dialog
        dialog.busy = True  # Simulate an in-flight worker without touching any store.
        with patch.object(APP, 'quit') as quit_app:
            self.d.quit()
            self.assertTrue(dialog.cancelled.is_set())
            self.assertTrue(dialog.close_pending)
            quit_app.assert_not_called()
            dialog.signals.done.emit(None, 'Cancelled')
            quit_app.assert_called_once()

    def test_recovery_opens_locked_without_granting_session(self):
        before = self.d.brain.session
        self.d.command('open recovery')
        self.assertTrue(self.d.recovery_dialog.isVisible())
        self.assertFalse(self.d.recovery_dialog.tabs.isEnabled())
        self.assertFalse(self.d.recovery_dialog.busy)
        self.assertEqual(self.d.brain.session, before)
        self.d.command('restore notes')
        self.assertEqual(self.d.recovery_dialog.tabs.currentIndex(), 1)
        self.d.recovery_dialog.reject()

    def test_admin_setup_opens_without_granting_session(self):
        before = self.d.brain.session
        self.d.open_panel()
        with patch('storage.store.get_primary_admin', return_value=None), \
             patch('desktop.setup_speech.SetupSpeech.say'):
            self.d.command('register admin')
        self.assertFalse(self.d.panel.isVisible())
        self.d.open_panel()
        self.assertFalse(self.d.panel.isVisible())
        self.assertTrue(self.d.activation_dialog.isVisible())
        self.assertEqual(self.d.activation_dialog.act, 0)
        self.assertEqual(self.d.brain.session, before)
        self.d.activation_dialog.reject()

    def test_bare_voice_wake_opens_intro_instead_of_help(self):
        with patch.object(self.d, 'wake') as wake, patch.object(self.d, 'command') as command:
            self.d.on_voice('wake up lya')
        wake.assert_called_once_with()
        command.assert_not_called()

    def test_wake_preserves_warm_voice_and_gates_mic_for_whole_greeting(self):
        import wave
        from app import HERE
        from audio import voice
        from PySide6.QtCore import QProcess
        self.d.spoken = True
        self.d.speech.process = Mock()
        self.d.speech.process.state.return_value = QProcess.ProcessState.Running
        with patch('winsound.PlaySound') as play, patch.object(self.d.speech, 'say') as say:
            self.d.on_voice('wake up lya')
            self.d.speech.process.kill.assert_not_called()
            play.assert_called_once()
            self.assertTrue(voice._SPEAKING.is_set())
            with wave.open(str(HERE / 'assets' / 'wake-greeting.wav'), 'rb') as sound:
                duration = round(1000 * sound.getnframes() / sound.getframerate())
            self.assertEqual(self.d.wake_timer.interval(), duration + 100)
            self.d.command('time')
            self.assertFalse(self.d.wake_timer.isActive())
            self.assertFalse(voice._SPEAKING.is_set())
            self.d.speech.process.kill.assert_not_called()
            self.assertIn(':', self.d.panel.title_label.text())
            say.assert_called_once()
            self.assertIn(':', say.call_args.args[0])

    def test_voice_clock_answers_aloud_and_quiet_turn_stays_silent(self):
        self.d.spoken = True
        with patch.object(self.d.speech, 'say') as say:
            self.d.on_voice('what time is it')
            say.assert_called_once()
            self.assertIn(':', say.call_args.args[0])
            say.reset_mock()
            self.d.on_voice('what time is it', quiet=True)
            say.assert_not_called()
            self.assertFalse(self.d.quiet_reply)

    def test_voice_orb_tracks_listener_and_reply_and_stop_cancels_playback(self):
        from audio import voice
        d = self.d
        d.dock(False)
        d.on_voice_phase('listening')
        self.assertEqual(d.orb.voice_phase, 'listening')
        self.assertEqual(d.panel.state_label.text(), 'LISTENING')
        d.on_voice_phase('hearing')
        self.assertEqual(d.orb.voice_phase, 'hearing')
        d.on_voice_phase('transcribing')
        self.assertEqual(d.orb.voice_phase, 'thinking')
        self.assertEqual(d.panel.state_label.text(), 'THINKING')
        d._speaking_changed(True)
        d.on_voice_phase('listening')  # A queued capture event must not overwrite playback.
        self.assertEqual(d.orb.voice_phase, 'speaking')
        self.assertEqual(d.panel.state_label.text(), 'SPEAKING · SAY STOP')
        with patch.object(d.speech, 'stop') as stop:
            d.on_voice('stop', quiet=True)
        stop.assert_called()
        self.assertTrue(d.brain_cancel.is_set())
        self.assertFalse(d.panel.isVisible())
        d._speaking_changed(False)
        self.assertFalse(voice._SPEAKING.is_set())
        self.assertEqual(d.panel.state_label.text(), 'VOICE OFF')

    def test_uncertain_voice_shows_candidate_suggests_short_volume_command_and_pauses(self):
        d = self.d
        d.spoken = True
        before = list(d.transcript)
        with patch.object(d.speech, 'say') as say, patch.object(d.brain, 'respond') as respond:
            d.voice_signals.retry.emit('can you lower the volume', False)
            self.assertIn('Heard (uncertain): can you lower the volume', d.panel.answer.toPlainText())
            self.assertIn('No command was run', d.panel.answer.toPlainText())
            self.assertIn('volume down', say.call_args.args[0])
            d.voice_signals.retry.emit('', True)
            self.assertIn('wait for you to say Lya', say.call_args.args[0])
            self.assertNotIn('Heard (uncertain)', d.panel.answer.toPlainText())
            self.assertEqual(say.call_count, 2)
            respond.assert_not_called()
        self.assertEqual(d.transcript, before)

    def test_recognized_volume_question_reaches_native_brain_and_spoken_reply(self):
        from brain.workflow import Answer
        d = self.d
        d.spoken = True
        with patch.object(d.brain, 'respond', return_value=Answer('Volume down.', 'local-device')) as respond, \
             patch.object(d.speech, 'say') as say:
            d.on_voice('can you lower the volume')
            for _ in range(100):
                APP.processEvents()
                if not d.brain_busy:
                    break
                QTest.qWait(10)
        self.assertFalse(d.brain_busy)
        self.assertEqual(respond.call_args.args[0], 'can you lower the volume')
        d.panel.finish_spoken()  # The fake speaker has no real playback-completion callback.
        self.assertIn('Volume down.', d.panel.answer.toPlainText())
        say.assert_called_once()
        self.assertIn('Volume down.', say.call_args.args[0])

    def test_uncertain_retry_stays_silent_in_quiet_mode(self):
        from audio import voice
        self.d.spoken = True
        with patch.dict(voice.QUIET, {'on': True}), patch.object(self.d.speech, 'say') as say:
            self.d.voice_signals.retry.emit('synthetic unclear words', False)
        say.assert_not_called()
        self.assertIn('No command was run', self.d.panel.answer.toPlainText())

    def test_voice_thinking_uses_orb_without_status_box_then_displays_answer(self):
        from brain.workflow import Answer
        started, release = threading.Event(), threading.Event()
        def pending(text, cancelled):
            started.set()
            release.wait(3)
            return Answer('Synthetic reply.', 'local')
        with patch.object(self.d.brain, 'respond', side_effect=pending):
            self.d.on_voice('synthetic question')
            try:
                self.assertTrue(started.wait(3))
                self.assertFalse(self.d.panel.isVisible())
                self.assertEqual(self.d.orb.voice_phase, 'thinking')
            finally:
                release.set()
            for _ in range(100):
                APP.processEvents()
                if not self.d.brain_busy:
                    break
                QTest.qWait(10)
        self.assertTrue(self.d.panel.isVisible())
        self.assertIn('Synthetic reply.', self.d.panel.answer.toPlainText())

    def test_active_orb_keeps_motion_until_state_ends_and_respects_reduced_motion(self):
        d = self.d
        d.dock(False)
        d.orb.show()
        d.orb.set_reduced_motion(False)
        d.on_voice_phase('listening')
        d.orb.motion_until = 0
        d.orb.tick()
        self.assertTrue(d.orb.timer.isActive())
        d.orb.set_voice_phase('off')
        d.orb.tick()
        self.assertFalse(d.orb.timer.isActive())
        d.orb.set_reduced_motion(True)
        d.on_voice_phase('thinking')
        self.assertFalse(d.orb.timer.isActive())

    def test_verified_admin_handoff_updates_brain_without_phone_approval(self):
        from security.policy import Session
        import time
        session = Session('admin', 'Synthetic owner', 'fake-session',
                          'fake-person', time.time()+60)
        self.d.on_admin_authenticated(session)
        APP.processEvents()
        self.assertEqual(self.d.brain.session, session)
        self.assertEqual(self.d.orb.person, 'admin')
        self.assertIsNone(self.d.brain.approve.verifier)
        self.assertIn('separate phone approval', self.d.panel.answer.toPlainText())

    def test_only_current_completed_answer_is_spoken(self):
        from brain.workflow import Answer
        self.d.spoken = True
        self.d.pending_question = 'example question'
        with patch.object(self.d.speech, 'say') as say:
            self.d.on_brain(self.d.generation - 1, Answer('Old answer', 'local'))
            say.assert_not_called()
            self.d.on_brain(self.d.generation, Answer('Current answer', 'local'))
            self.assertEqual(say.call_args.args[0], 'Current answer')
            self.assertEqual(self.d.panel.answer.toPlainText(), 'You asked: example question\n\nLYA: ')
            self.d.panel.sync_caption('Current ', 120)
            self.d.panel.finish_spoken()
            self.assertEqual(self.d.panel.answer.toPlainText(), 'You asked: example question\n\nLYA: Current answer')
            self.d.brain_cancel.set()
            self.d.on_brain(self.d.generation, Answer('Cancelled answer', 'local'))
            self.assertEqual(say.call_count, 1)

    def test_spoken_chat_keeps_history_and_reveals_one_reply(self):
        from brain.workflow import Answer
        self.d.spoken = True
        self.d.panel.set_mode('chat')
        self.d.transcript = ['You: hello']
        with patch.object(self.d.speech, 'say'):
            self.d.on_brain(self.d.generation, Answer('Hello there.', 'local'))
            self.assertEqual(self.d.panel.answer.toPlainText(), 'You: hello\n\nLYA: ')
            self.d.panel.finish_spoken()
        self.assertEqual(self.d.panel.answer.toPlainText(), 'You: hello\n\nLYA: Hello there.')

    def test_second_question_while_busy_does_not_discard_first_answer(self):
        from brain.workflow import Answer
        started = threading.Event()
        release = threading.Event()

        def pending_answer(text, cancelled):
            started.set()
            if not release.wait(3):
                raise AssertionError('fake worker was not released')
            return Answer('First answer', 'local')

        with patch.object(self.d.brain, 'respond', side_effect=pending_answer):
            self.d.command('First question')
            self.assertTrue(started.wait(3))
            original_generation = self.d.generation
            self.d.command('Second question')
            self.assertEqual(self.d.generation, original_generation)
            release.set()
            for _ in range(100):
                APP.processEvents()
                if not self.d.brain_busy:
                    break
                QTest.qWait(10)
        self.assertFalse(self.d.brain_busy)
        self.assertIn('First answer', self.d.panel.answer.toPlainText())

    def test_stop_during_pending_worker_hides_late_answer(self):
        from brain.workflow import Answer
        started = threading.Event()
        release = threading.Event()

        def pending_answer(text, cancelled):
            started.set()
            if not release.wait(3):
                raise AssertionError('fake worker was not released')
            return Answer('Late private answer', 'private-local')

        self.d.spoken = True
        with patch.object(self.d.brain, 'respond', side_effect=pending_answer), \
             patch.object(self.d.speech, 'say') as speak:
            self.d.command('First question')
            try:
                self.assertTrue(started.wait(3))
                self.d.command('stop')
            finally:
                release.set()
            for _ in range(100):
                APP.processEvents()
                if not self.d.brain_busy:
                    break
                QTest.qWait(10)
            self.assertFalse(self.d.brain_busy)
            self.assertFalse(self.d.panel.isVisible())
            self.assertNotIn('Late private answer', self.d.panel.answer.toPlainText())
            self.assertEqual(self.d.transcript, [])
            speak.assert_not_called()

    def test_mute_stops_audio_and_suppresses_replies(self):
        with patch.object(self.d.speech, 'stop') as stop, patch.object(self.d.speech, 'say') as say:
            self.d.command('voice off')
            stop.assert_called()
            self.d.speak_reply('Do not speak')
            say.assert_not_called()
            self.d.command('voice on')
            say.assert_called_once()

    def setUp(self):
        self.d = OrbDesktop(APP, True)
        self.d.spoken = False
        self.d.brain.client = Mock(side_effect=AssertionError('Unexpected model call'))

    def tearDown(self):
        self.d.pool.waitForDone(2000)
        self.d.quit()
        for widget in (self.d.orb, self.d.panel, self.d.greeting):
            widget.deleteLater()
        self.d.deleteLater()
        APP.processEvents()

    def test_intro_dock_input_answer_and_chat(self):
        d = self.d
        d.start_intro()
        self.assertTrue(d.greeting.isVisible())
        self.assertFalse(d.panel.isVisible())
        self.assertIn('Guest', d.greeting.text())
        area = APP.primaryScreen().availableGeometry()
        self.assertLess(abs(d.orb.geometry().center().x() - area.center().x()), 3)
        self.assertLess(abs(d.orb.geometry().center().y() - area.center().y()), 3)
        self.assertTrue(d.orb.mask().isEmpty())
        QTest.qWait(2350)
        for _ in range(100):
            if d.orb.width() == 64:
                break
            QTest.qWait(10)
        self.assertEqual(d.orb.width(), 64)
        self.assertFalse(d.greeting.isVisible())
        self.assertFalse(d.orb.timer.isActive())
        d.toggle_panel()
        self.assertEqual(d.panel.mode, 'input')
        self.assertTrue(d.panel.entry.isVisible())
        self.assertFalse(d.panel.stack.isVisible())
        d.command('time')
        self.assertEqual(d.panel.mode, 'answer')
        self.assertTrue(d.panel.stack.isVisible())
        self.assertTrue(d.panel.title_label.isVisible())
        self.assertFalse(d.panel.entry.isVisible())
        self.assertIn(':', d.panel.title_label.text())
        self.assertTrue(d.panel.answer.toPlainText().strip())
        d.command('open chat')
        self.assertEqual(d.panel.mode, 'chat')
        d.command('stop')
        self.assertFalse(d.panel.isVisible())
        self.assertFalse(d.intro_timer.isActive())

    def test_private_denial_and_cancelled_reply(self):
        from brain.workflow import Answer
        d = self.d
        d.command('show memories')
        for _ in range(100):
            if not d.brain_busy:
                break
            QTest.qWait(10)
        self.assertIn('locked', d.panel.answer.toPlainText())
        d.brain.client.assert_not_called()
        old = d.generation
        d.close_panel()
        d.on_brain(old, Answer('STALE'))
        self.assertFalse(d.panel.isVisible())
        self.assertNotIn('STALE', d.panel.answer.toPlainText())
        self.assertEqual(d.transcript, [])

    def test_reveal_stops_on_close_and_reduced_motion(self):
        d = self.d
        d.command('time')
        d.panel.reduced = False
        d.panel.animate_answer('A bounded synthetic answer. ' * 30)
        self.assertTrue(d.panel.reveal.isActive())
        d.panel.reveal_next()
        self.assertGreaterEqual(len(d.panel.answer.toPlainText()), 2)
        d.set_motion_mode(True)
        self.assertFalse(d.panel.reveal.isActive())
        self.assertIn('synthetic', d.panel.answer.toPlainText())
        d.panel.reduced = False
        d.panel.animate_answer('another answer')
        d.close_panel()
        self.assertFalse(d.panel.reveal.isActive())

    def test_spoken_caption_reveals_words_then_restores_exact_answer(self):
        panel = self.d.panel
        panel.begin_spoken('Hello, world. **Exact answer**')
        panel.sync_caption('Hello, world.', 600)
        panel.reveal_next()
        self.assertEqual(panel.answer.toPlainText(), 'Hello, ')
        while panel.reveal.isActive():
            panel.reveal_next()
        self.assertEqual(panel.answer.toPlainText(), 'Hello, world.')
        panel.finish_spoken()
        self.assertEqual(panel.answer.toPlainText(), 'Hello, world. **Exact answer**')

    def test_spoken_answer_does_not_wait_for_audio(self):
        from brain.workflow import Answer
        d = self.d
        d.dock(False)
        d.open_panel()
        d.panel.reduced = False
        message = 'A clear answer arrives before the local voice starts. ' * 20
        with patch.object(d.speech, 'say'):
            d.on_brain(d.generation, Answer(message, 'local'))
        self.assertEqual(d.panel.answer.toPlainText(), '')
        d.panel.reveal_next()
        self.assertGreater(len(d.panel.answer.toPlainText()), 2)
        for _ in range(29):
            d.panel.reveal_next()
        self.assertEqual(d.panel.answer.toPlainText(), message)

    def test_chat_types_only_the_new_reply(self):
        from brain.workflow import Answer
        d = self.d
        d.dock(False)
        d.command('open chat')
        d.panel.reduced = False
        d.transcript = ['You: first', 'LYA: first reply', 'You: second']
        d.panel.show_transcript('\n\n'.join(d.transcript))
        d.generation += 1
        d.on_brain(d.generation, Answer('second reply'))
        before_tick = d.panel.answer.toPlainText()
        self.assertEqual(before_tick.count('first reply'), 1)
        self.assertTrue(before_tick.endswith('LYA: '))
        d.panel.reveal_next()
        after_tick = d.panel.answer.toPlainText()
        self.assertEqual(after_tick.count('first reply'), 1)
        self.assertTrue(after_tick.endswith('LYA: se'))
        while d.panel.reveal.isActive():
            d.panel.reveal_next()
        self.assertTrue(d.panel.answer.toPlainText().endswith('LYA: second reply'))

    def test_typing_on_finished_compact_answer_starts_next_input(self):
        d = self.d
        d.dock(False)
        d.command('time')
        self.assertEqual(d.panel.mode, 'answer')
        self.assertFalse(d.panel.reveal.isActive())
        QTest.keyClick(d.panel.answer, Qt.Key.Key_N)
        self.assertEqual(d.panel.mode, 'input')
        self.assertEqual(d.panel.entry.text(), 'n')
        QTest.keyClicks(d.panel.entry, 'ext question')
        self.assertEqual(d.panel.entry.text(), 'next question')
        self.assertTrue(d.panel.entry.isVisible())

    def test_layout_is_inside_screen(self):
        d = self.d
        d.dock(False)
        for mode in ('input', 'answer', 'chat'):
            d.panel.set_mode(mode)
            d.open_panel()
            self.assertTrue(APP.primaryScreen().availableGeometry().contains(d.panel.geometry()))
        d.command('show files')
        self.assertEqual(d.panel.files.count(), 4)

    def test_card_keeps_its_readable_height_near_top_edge(self):
        from PySide6.QtCore import QRect
        d = self.d
        d.dock(False)
        area = APP.primaryScreen().availableGeometry()
        d.orb.move(area.left() + 12, area.top() + 12)
        for mode, wanted in (('answer', 320), ('chat', 590), ('input', 100)):
            d.panel.set_mode(mode)
            target = d.panel_target()
            self.assertEqual(target.height, min(wanted, area.height() - 24))
            self.assertTrue(area.contains(QRect(target.x, target.y, target.width, target.height)))
            d.open_panel()
            self.assertTrue(area.contains(d.panel.geometry()))
            if mode == 'input':
                self.assertTrue(d.panel.rect().contains(d.panel.entry.geometry()))
            else:
                self.assertGreater(d.panel.answer.height(), 60)

    def test_animation_finishes_and_idle_does_not_repaint(self):
        d = self.d
        d.orb.set_reduced_motion(False)
        d.orb.set_artwork(True)
        d.start_intro()
        d.dock()
        QTest.qWait(1250)
        self.assertEqual(d.orb.width(), 64)
        self.assertEqual(d.orb.height(), 64)
        self.assertEqual(d.orb.circle_mix, 1.0)
        self.assertEqual(d.docking.state(), d.docking.State.Stopped)
        QTest.qWait(3200)
        count = len(d.orb.paint_samples)
        QTest.qWait(300)
        self.assertEqual(len(d.orb.paint_samples), count)
        self.assertFalse(d.orb.timer.isActive())

    def test_vision_window_starts_with_camera_off(self):
        from PySide6.QtCore import QProcess
        d = self.d
        d.command('open vision')
        self.assertTrue(d.vision_dialog.isVisible())
        self.assertEqual(d.vision_dialog.process.state(), QProcess.ProcessState.NotRunning)
        self.assertIn('CAMERA OFF', d.vision_dialog.scene.text())
        self.assertIn('nothing saved', d.vision_dialog.status.text())
        from PySide6.QtWidgets import QLineEdit
        self.assertEqual(d.vision_dialog.findChildren(QLineEdit), [])
        d.vision_dialog.close()

    @patch.object(OrbDesktop, 'camera_owner', new=lambda self: 'synthetic-owner')
    def test_visual_question_routes_without_general_model_or_identity_change(self):
        from camera_eyes import VisionDialog
        before = self.d.brain.session
        with patch.object(VisionDialog, 'toggle_live') as start:
            self.d.command('LYA, can you see my pen?')
        start.assert_called_once()
        self.assertEqual(self.d.vision_dialog.pending_question[1], 'LYA, can you see my pen?')
        self.d.vision_dialog.answer_ready.emit(self.d.generation, 'I cannot reliably find a pen yet.')
        self.assertTrue(self.d.panel.isVisible())
        self.assertIn('pen', self.d.panel.answer.toPlainText())
        self.assertEqual(self.d.brain.session, before)
        self.d.vision_dialog.close()

    @patch.object(OrbDesktop, 'camera_owner', new=lambda self: 'synthetic-owner')
    def test_what_do_you_see_uses_normal_answer_panel(self):
        from camera_eyes import VisionDialog
        with patch.object(VisionDialog, 'toggle_live'):
            self.d.command('what do you see?')
        self.assertEqual(self.d.vision_dialog.pending_question[1], 'what do you see?')
        self.d.vision_dialog.answer_ready.emit(self.d.generation, 'I can see a bottle.')
        self.assertIn('bottle', self.d.panel.answer.toPlainText())
        self.d.vision_dialog.close()

    @patch.object(OrbDesktop, 'camera_owner', new=lambda self: 'synthetic-owner')
    def test_spoken_pointing_question_reaches_local_camera_without_brain_request(self):
        from camera_eyes import VisionDialog
        before = self.d.brain.session
        with patch.object(VisionDialog, 'toggle_live'), \
             patch.object(self.d.brain, 'respond') as brain:
            self.d.on_voice('Lya, what am I pointing at?')
            brain.assert_not_called()
        self.assertEqual(self.d.vision_dialog.pending_question[1], 'Lya, what am I pointing at?')
        self.d.vision_dialog.answer_ready.emit(self.d.generation, 'Along your pointing direction, I see a possible bottle.')
        self.assertIn('possible bottle', self.d.panel.answer.toPlainText())
        self.assertEqual(self.d.brain.session, before)

    def test_bare_this_uses_the_existing_live_camera_context(self):
        from PySide6.QtCore import QProcess
        self.d.ensure_vision()
        with patch.object(self.d.vision_dialog.process, 'state', return_value=QProcess.ProcessState.Running), \
             patch.object(self.d.vision_dialog, 'ask') as ask, \
             patch.object(self.d.brain, 'respond') as brain:
            self.d.on_voice('Lya, what is this?')
            ask.assert_called_once_with('Lya, what is this?', self.d.generation)
            brain.assert_not_called()

    @patch.object(OrbDesktop, 'camera_owner', new=lambda self: 'synthetic-owner')
    def test_natural_open_and_see_me_bypasses_general_brain_action(self):
        from camera_eyes import VisionDialog
        from vision.answers import answer_scene
        text = 'Open the camera and see me. You cover that.'
        before = self.d.brain.session
        with patch.object(VisionDialog, 'toggle_live') as start, \
             patch.object(self.d.brain, 'respond') as brain:
            self.d.on_voice(text)
            start.assert_called_once()
            brain.assert_not_called()
        self.assertEqual(self.d.vision_dialog.pending_question[1], text)
        reply = answer_scene(text, {'width': 640, 'height': 480, 'faces': [[10, 10, 50, 60]], 'objects': []})
        self.d.vision_dialog.answer_ready.emit(self.d.generation, reply)
        self.assertIn('1 person(s)', self.d.panel.answer.toPlainText())
        self.assertEqual(self.d.brain.session, before)

    def test_natural_camera_open_and_close_commands_use_the_same_local_control(self):
        from camera_eyes import VisionDialog
        with patch.object(VisionDialog, 'toggle_live') as start, \
             patch.object(self.d.brain, 'respond') as brain:
            self.d.on_voice('Please open the camera.')
            start.assert_called_once()
            brain.assert_not_called()
        with patch.object(self.d.vision_dialog, 'close') as close, \
             patch.object(self.d.brain, 'respond') as brain:
            self.d.command('Lya, please close the camera.')
            close.assert_called_once()
            brain.assert_not_called()

    def test_camera_owner_requires_verification_active_record_and_admin_role(self):
        from security.policy import Session
        self.d.brain.clock = lambda: 1000
        valid = Session('admin', 'Synthetic', 'fake-session', 'fake-person', 1100)
        for session, record, accepted in (
                (Session(), None, False),
                (Session('admin', 'Synthetic', 'fake-session', 'fake-person', 999), None, False),
                (Session('friend', 'Synthetic', 'fake-session', 'fake-person', 1100), {'role': 'friend', 'active': True}, False),
                (valid, {'role': 'admin', 'active': False}, False),
                (valid, {'role': 'friend', 'active': True}, False),
                (valid, {'person_id': 'fake-person', 'role': 'admin', 'active': True}, True)):
            with self.subTest(session=session, record=record), patch('storage.store.get_person', return_value=record):
                self.d.brain.bind_session(session)
                self.assertEqual(bool(self.d.camera_owner()), accepted)
        with patch('storage.store.get_person', side_effect=OSError('Synthetic locked store')):
            self.assertIsNone(self.d.camera_owner())

    def test_guest_camera_button_and_spoken_request_never_launch_worker(self):
        from camera_eyes import VisionDialog
        self.d.ensure_vision()
        with patch.object(self.d.vision_dialog.process, 'start') as start:
            self.d.vision_dialog.live_button.click()
            self.d.on_voice('what all can you see?')
        start.assert_not_called()
        self.assertIsNone(self.d.vision_dialog.last_result)
        self.assertIn('locked', self.d.vision_dialog.status.text())

    def test_camera_observations_clear_in_reduced_mode_without_erasing_other_answers(self):
        d = self.d
        d.ensure_vision()
        d.spoken = False
        d.panel.reduced = True
        d.on_vision_answer(d.generation, 'Synthetic camera observation.')
        self.assertEqual(d.panel.footnote.text(), 'LOCAL CAMERA · NO IMAGE UPLOADS')
        self.assertIn('Synthetic camera observation', d.panel.answer.toPlainText())
        d.end_vision_session()
        self.assertNotIn('Synthetic camera observation', d.panel.answer.toPlainText())
        d.on_vision_answer(d.generation, 'Another synthetic camera observation.')
        d.panel.show_answer('Time', 'Unrelated current answer.')
        d.end_vision_session()
        self.assertEqual(d.panel.answer.toPlainText(), 'Unrelated current answer.')

    @patch.object(OrbDesktop, 'camera_owner', new=lambda self: 'synthetic-owner')
    def test_scene_tour_matches_spoken_items_and_stop_cancels_later_completion(self):
        from PySide6.QtCore import QProcess
        from PySide6.QtGui import QPixmap
        import time
        d = self.d
        d.ensure_vision()
        dialog = d.vision_dialog
        dialog.last_result = {'width': 640, 'height': 480, 'ready': True, 'analyzed_at': time.monotonic(),
                              'faces': [], 'objects': [
                                  {'label': 'cup', 'confidence': .9, 'box': [420, 180, 500, 300]},
                                  {'label': 'bottle', 'confidence': .8, 'box': [80, 180, 140, 300]}]}
        dialog.checked_at = dialog.last_result['analyzed_at']
        dialog.checked_pixmap = QPixmap(640, 480)
        dialog.checked_pixmap.fill(Qt.GlobalColor.black)
        d.spoken = True
        def say(*args, **kwargs):
            d.speech.request += 1
            d.speech.cancelled = False
        with patch.object(dialog.process, 'state', return_value=QProcess.ProcessState.Running), patch.object(
                dialog.process, 'kill'), patch.object(dialog.process, 'waitForFinished'), patch.object(
                d.speech, 'say', side_effect=say) as spoken:
            d.on_voice('what all can you see?')
            self.assertIn('bottle', spoken.call_args.args[0])
            self.assertFalse(any('possible bottle' in entry for entry in d.transcript))
            self.assertEqual(dialog.scene.selected['label'], 'bottle')
            d.speech.completed.emit()
            d.speech.completed.emit()  # Duplicate completion must not skip a tour item.
            APP.processEvents()
            self.assertEqual(spoken.call_count, 2)
            self.assertEqual(dialog.scene.selected['label'], 'cup')
            d.on_voice('stop')
            d.speech.completed.emit()
            APP.processEvents()
            self.assertEqual(spoken.call_count, 2)
            self.assertEqual(d.vision_tour, [])
            self.assertFalse(dialog.focus_active)
            dialog.stop_camera()
            self.assertIsNone(d.camera_panel_text)
            self.assertNotIn('possible bottle', d.panel.full_text)

    @patch.object(OrbDesktop, 'camera_owner', new=lambda self: 'synthetic-owner')
    def test_camera_quiet_tour_does_not_speak_and_error_completion_does_not_advance(self):
        from PySide6.QtCore import QProcess
        from PySide6.QtGui import QPixmap
        import time
        d = self.d
        d.ensure_vision()
        dialog = d.vision_dialog
        dialog.last_result = {'width': 640, 'height': 480, 'ready': True, 'analyzed_at': time.monotonic(),
                              'faces': [], 'objects': [
                                  {'label': 'cup', 'confidence': .9, 'box': [420, 180, 500, 300]},
                                  {'label': 'bottle', 'confidence': .8, 'box': [80, 180, 140, 300]}]}
        dialog.checked_at = dialog.last_result['analyzed_at']
        dialog.checked_pixmap = QPixmap(640, 480)
        dialog.checked_pixmap.fill(Qt.GlobalColor.black)
        d.spoken = True
        def say(*args, **kwargs):
            d.speech.request += 1
            d.speech.cancelled = False
        with patch.object(dialog.process, 'state', return_value=QProcess.ProcessState.Running), patch.object(
                dialog.process, 'kill'), patch.object(dialog.process, 'waitForFinished'), patch.object(
                d.speech, 'say', side_effect=say) as spoken:
            d.on_voice('what all can you see?', quiet=True)
            spoken.assert_not_called()
            self.assertTrue(dialog.focus_active)
            d.on_voice('what all can you see?')
            self.assertEqual(spoken.call_count, 1)
            d.speech.completed.emit()
            d.speech.cancelled = True
            d.speech.unavailable.emit()
            APP.processEvents()
            self.assertEqual(spoken.call_count, 1)
            self.assertFalse(dialog.focus_active)

    def test_chat_controls_and_independent_windows(self):
        d = self.d
        d.dock(False)
        d.command('open chat box')
        self.assertEqual(d.panel.mode, 'chat')
        self.assertTrue(d.panel.entry.isVisible())
        d.command('make it full screen')
        self.assertTrue(d.panel.isFullScreen())
        d.command('restore chat')
        self.assertFalse(d.panel.isFullScreen())
        position = d.panel.pos()
        d.orb.move(d.orb.pos() + __import__('PySide6.QtCore', fromlist=['QPoint']).QPoint(70, 0))
        d.orb.relocated.emit()
        self.assertEqual(d.panel.pos(), position)
        d.command('close chat')
        self.assertFalse(d.panel.isVisible())
        with __import__('unittest.mock', fromlist=['patch']).patch('experience.read_project_document', return_value='Synthetic file'):
            d.command('show three files')
        self.assertEqual(len(d.file_windows), 3)
        before = [w.geometry() for w in d.file_windows]
        d.orb.move(50, 50)
        d.orb.relocated.emit()
        self.assertEqual(before, [w.geometry() for w in d.file_windows])
        d.read_document('.env')
        self.assertEqual(len(d.file_windows), 3)
        d.brain.client.assert_not_called()

    def test_persistent_crystal_and_circle_command(self):
        d = self.d
        d.command('stay as a crystal')
        self.assertTrue(d.keep_crystal)
        self.assertEqual(d.orb.circle_mix, 0.0)
        self.assertFalse(d.intro_timer.isActive())
        d.command('become a circle')
        self.assertFalse(d.keep_crystal)
        self.assertEqual(d.orb.circle_mix, 1.0)

    def test_full_rotation_returns_to_circle(self):
        d = self.d
        d.orb.set_artwork(True)
        d.orb.set_reduced_motion(False)
        d.start_intro()
        QTest.qWait(1450)
        # Frame decoding may delay Qt's timers under load; the spin may have
        # already finished by the time this wait returns.
        self.assertTrue(d.spin_clock.isValid())
        self.assertEqual(len(d.spin_frames), 48)
        self.assertFalse(any(frame.isNull() for frame in d.spin_frames))
        QTest.qWait(4400)
        # Windows timer delivery may be late under load; require bounded completion.
        for _ in range(200):
            if not (d.spin_timer.isActive() or d.intro_timer.isActive() or d.docking.state() == d.docking.State.Running):
                break
            QTest.qWait(10)
        self.assertFalse(d.spin_timer.isActive())
        self.assertFalse(d.intro_timer.isActive())
        self.assertEqual(d.orb.circle_mix, 1.0)
        self.assertTrue(d.orb.mask().isEmpty())
        self.assertIsNone(d.orb.spin_frame)
        paints = len(d.orb.paint_samples)
        QTest.qWait(250)
        self.assertEqual(len(d.orb.paint_samples), paints)


def preview():
    from PySide6.QtGui import QImage
    out = Path(__file__).parent / 'qa' / '2026-09-17-window-controls'
    out.mkdir(parents=True, exist_ok=True)
    d = OrbDesktop(APP, True)
    d.orb.set_artwork(True)
    d.dock(False)
    for mode in ('input', 'answer', 'chat'):
        d.panel.set_mode(mode)
        if mode != 'input':
            d.panel.show_answer('LYA', 'Ready when you are.\n\nThis is a synthetic interface preview. Your session remains a guest.')
        d.panel.resize(520 if mode == 'chat' else 460, {'input':90,'answer':290,'chat':540}[mode])
        d.panel.show()
        APP.processEvents()
        canvas = QImage(760, 620, QImage.Format.Format_ARGB32)
        canvas.fill(QColor('#cdd8df' if mode == 'answer' else '#101925'))
        painter = QPainter(canvas)
        painter.drawPixmap((760 - d.panel.width()) // 2, 530 - d.panel.height(), d.panel.grab())
        painter.drawPixmap(348, 542, d.orb.grab())
        painter.end()
        canvas.save(str(out / (mode + '.png')))
    d.quit()


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExperienceChecks))
    if result.wasSuccessful():
        preview()
    sys.exit(not result.wasSuccessful())


