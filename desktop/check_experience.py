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
        with patch.object(self.d.speech, 'say') as say, patch.object(
                self.d.panel, 'animate_answer', wraps=self.d.panel.animate_answer) as animate:
            self.d.on_brain(self.d.generation - 1, Answer('Old answer', 'local'))
            say.assert_not_called()
            self.d.on_brain(self.d.generation, Answer('Current answer', 'local'))
            self.assertEqual(say.call_args.args[0], 'Current answer')
            self.assertEqual(animate.call_count, 1)
            self.d.brain_cancel.set()
            self.d.on_brain(self.d.generation, Answer('Cancelled answer', 'local'))
            self.assertEqual(say.call_count, 1)

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
        self.assertFalse(d.panel.title_label.isVisible())
        self.assertFalse(d.panel.entry.isVisible())
        self.assertIn(':', d.panel.answer.toPlainText())
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

    def test_visual_question_routes_to_camera_without_model_or_auth(self):
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

    def test_what_do_you_see_uses_normal_answer_panel(self):
        from camera_eyes import VisionDialog
        with patch.object(VisionDialog, 'toggle_live'):
            self.d.command('what do you see?')
        self.assertEqual(self.d.vision_dialog.pending_question[1], 'what do you see?')
        self.d.vision_dialog.answer_ready.emit(self.d.generation, 'I can see a bottle.')
        self.assertIn('bottle', self.d.panel.answer.toPlainText())
        self.d.vision_dialog.close()

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


