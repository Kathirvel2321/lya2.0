"""Real Qt checks with synthetic tasks. No sensors, providers or private stores."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QColor, QPainter, QFont, QLinearGradient, QPalette
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtTest import QTest

from app import GlassPanel, Desktop, BrainJob, BrainSignals, Crystal
from experience import CompactPanel
from task_border import TaskBorder, QtTarget, logical_rect, FLAGS

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'review' / '2026-10-16-glass-conversation'


class GlassChecks(unittest.TestCase):
    def test_conversation_typing_and_literal_transcript(self):
        panel = CompactPanel()
        self.addCleanup(panel.close)
        panel.set_mode('answer')
        panel.show_answer('LYA', 'You: <b>literal</b>\n\nLYA: Readable glass.')
        panel.show()
        APP.processEvents()
        self.assertTrue(panel.entry.isVisible())
        self.assertTrue(panel.stack.isVisible())
        self.assertIn('<b>literal</b>', panel.answer.toPlainText())
        sent = []
        panel.submitted.connect(sent.append)
        panel.entry.setText('Hello LYA')
        QTest.keyClick(panel.entry, Qt.Key.Key_Return)
        self.assertEqual(sent, ['Hello LYA'])
        self.assertEqual(panel.entry.text(), '')
        panel.set_mode('chat')
        self.assertTrue(panel.entry.isVisible())
        panel.set_mode('files')
        self.assertFalse(panel.entry.isVisible())

    def test_panel_motion_hidden_reduced_and_static_states(self):
        panel = CompactPanel()
        self.addCleanup(panel.close)
        panel.set_mode('chat')
        panel.set_reduced_motion(False)
        panel.set_activity('research')
        self.assertFalse(panel._edge_timer.isActive())
        panel.show()
        APP.processEvents()
        self.assertTrue(panel._edge_timer.isActive())
        self.assertEqual(panel._edge_timer.interval(), 80)
        self.assertEqual(panel.state_label.text(), 'Finding sources')
        panel.set_reduced_motion(True)
        self.assertFalse(panel._edge_timer.isActive())
        panel.set_reduced_motion(False)
        for state in ('approval', 'error', 'done', 'idle'):
            panel.set_activity(state)
            self.assertFalse(panel._edge_timer.isActive())
        panel.set_activity('working')
        panel.hide()
        self.assertFalse(panel._edge_timer.isActive())

    def test_border_follows_only_explicit_target_and_stops_on_close(self):
        app = QWidget()
        app.setGeometry(60, 70, 500, 350)
        app.show()
        self.addCleanup(app.close)
        border = TaskBorder(reduced=False)
        self.addCleanup(border.close)
        border.begin(7, QtTarget(app), 'Working in this app')
        APP.processEvents()
        self.assertTrue(border.motion.isActive())
        self.assertTrue(border.tracking.isActive())
        self.assertTrue(all(e.windowFlags() & Qt.WindowType.WindowTransparentForInput for e in border.edges))
        self.assertTrue(all(e.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus for e in border.edges))
        self.assertLess(sum(e.width()*e.height() for e in border.edges), app.width()*app.height()//10)
        app.move(110, 130)
        app.resize(600, 420)
        border.refresh()
        self.assertEqual(border.last_rect, app.frameGeometry())
        app.hide()
        border.refresh()
        self.assertFalse(border.motion.isActive())
        self.assertTrue(all(not e.isVisible() for e in border.edges))
        app.show()
        border.refresh()
        border.set_reduced(True)
        self.assertFalse(border.motion.isActive())
        border.stop()
        self.assertFalse(any(t.isActive() for t in (border.motion, border.tracking, border.search)))
        self.assertFalse(border.label.isVisible())

    def test_completion_and_destroyed_window_remove_all_surfaces(self):
        now = [0.0]
        app = QWidget()
        app.show()
        border = TaskBorder(clock=lambda: now[0])
        self.addCleanup(border.close)
        self.addCleanup(app.close)
        border.begin(2, QtTarget(app), 'Finished', 'done', .6)
        self.assertFalse(border.motion.isActive())
        now[0] = 1
        border.refresh()
        self.assertIsNone(border.target)
        target = SimpleNamespace(geometry=lambda: None)
        border.begin(3, target)
        self.assertFalse(border.tracking.isActive())

    def test_mixed_dpi_and_negative_monitor_origins(self):
        screen = SimpleNamespace(devicePixelRatio=lambda: 1.5, geometry=lambda: QRect(-1707, 0, 1707, 960))
        self.assertEqual(logical_rect((-2400, 150, -1500, 750), (-2560, 0), screen),
                         QRect(-1600, 100, 600, 400))

    def test_stale_cancelled_and_invalid_progress_cannot_show_work(self):
        panel = Mock()
        d = SimpleNamespace(generation=5, brain_busy=True, brain_cancel=threading.Event(),
                            panel=panel, launch_receipt=None)
        Desktop.on_task_progress(d, 4, {'stage':'research'})
        panel.set_activity.assert_not_called()
        d.brain_cancel.set()
        Desktop.on_task_progress(d, 5, {'stage':'research'})
        panel.set_activity.assert_not_called()
        d.brain_cancel.clear()
        Desktop.on_task_progress(d, 5, {'stage':'made up'})
        panel.set_activity.assert_not_called()
        Desktop.on_task_progress(d, 5, {'stage':'research'})
        panel.set_activity.assert_called_once_with('research')
        Desktop.on_task_progress(d, 5, {'stage':'launched','pid':123})
        self.assertEqual(d.launch_receipt, 123)
        Desktop.on_task_progress(d, 5, {'stage':'launched','pid':True})
        self.assertIsNone(d.launch_receipt)

    def test_actual_worker_forwards_progress_without_changing_answer(self):
        from brain.workflow import Answer
        signals = BrainSignals()
        observed, answers = [], []
        signals.progress.connect(lambda generation, event: observed.append((generation,event)))
        signals.finished.connect(lambda generation, answer: answers.append(answer.text))
        brain = Mock()
        def respond(text, cancelled, *, progress):
            progress({'stage':'research'})
            return Answer('Synthetic answer')
        brain.respond.side_effect = respond
        BrainJob(brain, 'Synthetic research', threading.Event(), 9, signals).run()
        self.assertEqual(observed, [(9, {'stage':'research'})])
        self.assertEqual(answers, ['Synthetic answer'])

    def test_public_research_reports_real_stages_and_observer_cannot_break_it(self):
        from brain.workflow import Brain
        events = []
        def research(*args, **kwargs):
            self.assertEqual(events[-1]['stage'], 'research')
            return []
        brain = Brain(client=lambda messages: '{"claims":[{"kind":"unknown","text":"No evidence supplied.","source_ids":[]}]}',
                      researcher=research)
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'LYA_DATA_DIR':tmp}):
            reply = brain.respond('Research public sources about rain.', progress=events.append)
            self.assertNotEqual(reply.route, 'error')
            self.assertEqual([x['stage'] for x in events], ['research', 'reason'])
            brain.researcher = lambda *args, **kwargs: []
            again = brain.respond('Research public sources about rain.', progress=lambda event: 1/0)
            self.assertNotEqual(again.route, 'error')

    @unittest.skipUnless((ROOT/'desktop/assets/lya-reference-body.png').is_file(), 'Repository body asset needed')
    def test_full_desktop_conversation_and_cancellation(self):
        from experience import OrbDesktop
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'LYA_DATA_DIR':tmp}):
            d = OrbDesktop(APP, reduced_motion=True)
            d.spoken = False
            try:
                d.brain.client = lambda messages: 'A synthetic answer.'
                d.command('Explain rain simply.')
                self.assertTrue(d.panel.isVisible())
                self.assertTrue(d.panel.entry.isVisible())
                self.assertEqual(d.orb.circle_mix, 0)
                d.pool.waitForDone(1000)
                APP.processEvents()
                self.assertIn('A synthetic answer.', d.panel.answer.toPlainText())
                self.assertEqual(d.panel._activity, 'done')
                d.close_panel()
                self.assertFalse(d.panel.isVisible())
                self.assertEqual(d.orb.width(), 64)
                self.assertFalse(d.panel._edge_timer.isActive())
                self.assertFalse(d.task_border.tracking.isActive())
                self.assertFalse(d.task_border.search.isActive())
                started, release = threading.Event(), threading.Event()
                from brain.workflow import Answer
                def slow_reply(text, cancelled, *, progress):
                    progress({'stage':'research'})
                    started.set()
                    release.wait(2)
                    return Answer('Stale synthetic answer')
                d.brain.respond = slow_reply
                d.command('Research a synthetic task.')
                self.assertTrue(started.wait(1))
                APP.processEvents()
                self.assertEqual(d.panel._activity, 'research')
                d.close_panel()
                release.set()
                d.pool.waitForDone(1000)
                APP.processEvents()
                self.assertFalse(d.panel.isVisible())
                self.assertEqual(d.panel._activity, 'idle')
                self.assertFalse(d.panel._edge_timer.isActive())
            finally:
                d.pool.waitForDone(1000)
                d.quit()
                d.orb.deleteLater()
                d.panel.deleteLater()
                d.greeting.deleteLater()
                d.deleteLater()
                APP.processEvents()

    def test_launch_receipt_is_emitted_only_after_the_allowed_launch(self):
        from skills.limited_apps import launch
        callback = Mock()
        with patch('skills.limited_apps.subprocess.Popen', return_value=SimpleNamespace(pid=321)) as popen:
            self.assertEqual(launch('calculator', on_launch=callback), 'Opened calculator.')
            callback.assert_called_once_with(321)
            self.assertEqual(len(popen.call_args.args[0]), 1)
        callback.reset_mock()
        with patch('skills.limited_apps.subprocess.Popen', side_effect=OSError):
            with self.assertRaises(OSError):
                launch('calculator', on_launch=callback)
        callback.assert_not_called()


def render_preview():
    """Render actual widgets, with the unchanged approved repository body asset."""
    if not (ROOT/'desktop/assets/lya-reference-body.png').is_file():
        print('Preview skipped locally: exact repository body asset unavailable.')
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    canvas = QWidget()
    canvas.resize(1440, 850)
    palette = canvas.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor('#071320'))
    canvas.setPalette(palette)
    canvas.setAutoFillBackground(True)
    title = QLabel('LYA  /  NATIVE INTERFACE PREVIEW', canvas)
    title.setStyleSheet('color:#a6bed0; font:16px "Segoe UI"; background:transparent;')
    title.setGeometry(54, 26, 900, 40)
    crystal = Crystal(canvas)
    crystal.set_reduced_motion(True)
    crystal.conversation_present = True
    crystal.move(30, 440)
    crystal.resize(190, 260)
    panel = CompactPanel()
    panel.setParent(canvas)
    panel.setWindowFlags(Qt.WindowType.Widget)
    panel.setGeometry(210, 240, 480, 450)
    panel.set_mode('chat')
    panel.title_label.setText('Right here with you.')
    panel.show_transcript('You: Compare these notes for me.\n\nLYA: I can help. Tell me which details matter most.')
    panel.footnote.setText('SYNTHETIC CONVERSATION')
    panel.set_activity('idle')
    panel.show()
    window = QWidget(canvas)
    window.setGeometry(760, 150, 620, 530)
    window.setStyleSheet('background:#f5f7fa; border-radius:8px;')
    heading = QLabel('Research notes', window)
    heading.setGeometry(34, 45, 540, 48)
    heading.setStyleSheet('font:26px "Segoe UI"; color:#17283a;')
    text = QLabel('An example task window\n\nThe border identifies this window only.\nYour work remains visible and usable.', window)
    text.setGeometry(34, 130, 540, 160)
    text.setStyleSheet('font:17px "Segoe UI"; color:#53677b;')
    note = QLabel('SYNTHETIC TASK PREVIEW', window)
    note.setGeometry(34, 365, 530, 30)
    note.setStyleSheet('font:12px "Segoe UI"; color:#6b7f8f;')
    window.show()
    canvas.show()
    border = TaskBorder(reduced=True)
    border.begin(1, QtTarget(window), 'Working in this app')
    APP.processEvents()
    image = canvas.grab()
    painter = QPainter(image)
    origin = canvas.mapToGlobal(QPoint(0,0))
    for surface in [*border.edges, border.label]:
        if surface.isVisible():
            painter.drawPixmap(surface.pos() - origin, surface.grab())
    painter.end()
    image.save(str(OUTPUT/'native-preview.png'))
    panel.set_activity('research')
    panel.set_reduced_motion(True)
    panel.grab().save(str(OUTPUT/'research-panel.png'))
    border.close()
    panel.close()
    canvas.close()


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GlassChecks)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        render_preview()
    sys.exit(0 if result.wasSuccessful() else 1)
