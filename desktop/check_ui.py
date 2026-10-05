"""Isolated native UI checks and screenshots on synthetic light/dark desktops.

Run: .venv-ui/Scripts/python.exe desktop/check_ui.py
No camera, microphone, private memory, network or user-desktop screenshots.
"""
import json
import statistics
import sys
import time
import unittest
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient, QTextCursor
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtTest import QTest

from layout import Box, place_panel, accent
from app import Desktop, Crystal, GlassPanel, ResponseText, read_project_document, WINDOW_FLAGS

OUTPUT = Path(__file__).resolve().parent / "qa"
APPLICATION = QApplication.instance() or QApplication([])
APPLICATION.setQuitOnLastWindowClosed(False)


class Backdrop(QWidget):
    def __init__(self, light):
        super().__init__()
        self.light = light
        self.resize(1180, 780)
        self.setWindowTitle("LYA synthetic desktop contrast check")

    def paintEvent(self, event):
        p = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#faf7ee" if self.light else "#111c2d"))
        gradient.setColorAt(1, QColor("#d1e2e8" if self.light else "#19262a"))
        p.fillRect(self.rect(), gradient)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#e8ece4" if self.light else "#203a3c"))
        p.drawEllipse(QRectF(-120, 270, 900, 780))
        p.setPen(QColor("#667c81" if self.light else "#8babb2"))
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(52, 68, "LYA / NATIVE DESKTOP STUDY")
        p.setFont(QFont("Segoe UI", 26, QFont.Weight.Light))
        p.drawText(52, 118, "A presence. Not a page.")
        p.setFont(QFont("Segoe UI", 11))
        p.drawText(52, 151, "Synthetic " + ("light" if self.light else "dark") + " background · real Qt widgets · UI milestone")
        p.drawText(52, 737, "Click the crystal to open. Drag to place. Escape to close. Ctrl+M for reduced motion.")
        p.end()


def render_sample(light, person="admin", task="files", message=False):
    backdrop = Backdrop(light)
    orb = Crystal(backdrop)
    orb.set_reduced_motion(True)
    orb.set_state(person=person, task=task)
    orb.move(950, 430)
    panel = GlassPanel(backdrop)
    panel.resize(480, 510)
    panel.move(445, 170)
    panel.color = orb.color
    panel.state_label.setText(f"{person.upper()} PALETTE · {task.upper()}")
    if message:
        panel.show_answer("Your space, uninterrupted.", "I can bring your saved project documents here.\n\nTry “show files” to choose one and read it beside the crystal.")
    else:
        panel.show_documents()
    backdrop.show()
    orb.show()
    panel.show()
    QTest.qWait(180)
    path = OUTPUT / ("message-desktop.png" if message else "light-desktop.png" if light else "dark-desktop.png")
    assert backdrop.grab().save(str(path)), "Could not save rendered widget image"
    backdrop.close()
    backdrop.deleteLater()
    APPLICATION.processEvents()


class InterfaceChecks(unittest.TestCase):
    def test_response_styles_preserve_literal_text_and_reset_between_turns(self):
        view = ResponseText()
        self.addCleanup(view.close)
        first = 'You: <b>literal question</b>\n\nLYA: literal answer'
        view.setPlainText(first)
        self.assertEqual(view.toPlainText(), first)
        second = 'Ordinary answer <script>literal text</script>'
        view.setPlainText(second)
        self.assertEqual(view.toPlainText(), second)
        cursor = QTextCursor(view.document())
        cursor.movePosition(QTextCursor.MoveOperation.Right)
        self.assertEqual(cursor.charFormat().fontWeight(), QFont.Weight.Normal)

    def setUp(self):
        self.desktop = Desktop(APPLICATION, reduced_motion=True)

    def tearDown(self):
        d = self.desktop
        d.generation += 1
        d.pool.waitForDone(2000)
        d.orb.hide()
        d.panel.hide()
        d.tray.hide()
        d.orb.deleteLater()
        d.panel.deleteLater()
        d.deleteLater()
        APPLICATION.processEvents()

    def test_microphone_menu_reads_metadata_without_opening_input(self):
        import os
        from unittest.mock import patch
        devices = [{'name': 'Synthetic mic', 'max_input_channels': 1, 'hostapi': 0},
                   {'name': 'Speaker', 'max_input_channels': 0, 'hostapi': 0}]
        with patch.dict(os.environ, {'LYA_MICROPHONE': 'Synthetic mic'}), \
             patch('sounddevice.query_devices', return_value=devices), \
             patch('sounddevice.query_hostapis', return_value={'name': 'Windows WASAPI'}), \
             patch('sounddevice.RawInputStream', side_effect=AssertionError('unexpected recording')):
            self.desktop.refresh_microphones()
            actions = self.desktop.microphone_menu.actions()
            self.assertEqual([a.text() for a in actions], ['Follow Windows default', 'Synthetic mic'])
            self.assertTrue(actions[1].isChecked())

    def test_microphone_restart_waits_and_manual_stop_cancels_it(self):
        import os
        from unittest.mock import Mock, patch
        d = self.desktop
        d.voice_thread = Mock()
        d.voice_thread.is_alive.return_value = True
        d.voice_stop_event = Mock()
        callbacks = []
        with patch.dict(os.environ, {}, clear=False), \
             patch('app.QTimer.singleShot', side_effect=lambda delay, callback: callbacks.append(callback)), \
             patch.object(d, 'start_voice') as start:
            d.select_microphone('Synthetic mic')
            self.assertEqual(os.environ['LYA_MICROPHONE'], 'Synthetic mic')
            d.voice_stop_event.set.assert_called_once()
            callbacks.pop(0)()
            start.assert_not_called()
            d.voice_thread.is_alive.return_value = False
            callbacks.pop(0)()
            start.assert_called_once_with(False)
            d.voice_thread.is_alive.return_value = True
            d.select_microphone('Synthetic other mic')
            d.stop_voice()
            callbacks.pop(0)()
            self.assertEqual(start.call_count, 1)

    def test_panel_stays_on_available_monitor_for_edges_and_negative_coordinates(self):
        for screen in (Box(0, 0, 1536, 816), Box(-1920, 0, 1920, 1080), Box(0, -900, 1440, 900), Box(0, 0, 600, 600)):
            for ox, oy in ((screen.x, screen.y), (screen.x + screen.width - 184, screen.y + screen.height - 252)):
                result = place_panel(Box(ox, oy, 184, 252), screen)
                self.assertGreaterEqual(result.x, screen.x)
                self.assertGreaterEqual(result.y, screen.y)
                self.assertLessEqual(result.x + result.width, screen.x + screen.width)
                self.assertLessEqual(result.y + result.height, screen.y + screen.height)

    def test_only_small_native_windows_and_alpha_artwork(self):
        d = self.desktop
        self.assertTrue(d.orb.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(d.panel.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertLess(d.orb.width(), 250)
        self.assertLess(d.panel.width(), 550)
        self.assertTrue(d.orb.base.hasAlphaChannel())
        self.assertEqual(d.orb.base.toImage().pixelColor(0, 0).alpha(), 0)

    def test_palette_is_presentation_only_and_task_takes_priority(self):
        d = self.desktop
        d.command("person admin")
        self.assertEqual(d.orb.person, "admin")
        self.assertIn("does not identify", d.panel.answer.toPlainText())
        self.assertEqual(accent("admin", "files"), "#6dceff")
        self.assertEqual(accent("admin", "idle"), "#ffc26b")
        self.assertFalse(hasattr(d, "session"))

    def test_stop_rejects_stale_worker_result_and_clears_panel(self):
        d = self.desktop
        d.show_files()
        old = d.generation
        d.close_panel()
        d.on_document(old, "private test", "MUST NOT REAPPEAR", True)
        self.assertFalse(d.panel.isVisible())
        self.assertNotIn("MUST NOT REAPPEAR", d.panel.answer.toPlainText())

    def test_project_file_read_is_allowlisted_and_real(self):
        self.assertIn("LYA", read_project_document("README.md"))
        for name in ("../secrets", "security/.lya_key", "C:/Windows/win.ini", "missing.md"):
            with self.assertRaises(PermissionError):
                read_project_document(name)

    def test_keyboard_submission_and_escape(self):
        d = self.desktop
        d.orb.show()
        d.open_panel()
        d.panel.entry.setText("show files")
        QTest.keyClick(d.panel.entry, Qt.Key.Key_Return)
        self.assertEqual(d.panel.files.count(), 4)
        self.assertEqual(d.orb.task, "files")
        d.panel.activateWindow()
        QTest.qWait(60)
        QTest.keyClick(d.panel.entry, Qt.Key.Key_Escape)
        QTest.qWait(60)
        self.assertFalse(d.panel.isVisible())

    def test_deterministic_commands(self):
        d = self.desktop
        d.orb.show()
        d.open_panel()

        # Test status command
        d.command("status")
        self.assertEqual(d.panel.title_label.text(), "System Readiness")
        self.assertIn("Foundations", d.panel.answer.toPlainText())

        # Test help command
        d.command("help")
        self.assertEqual(d.panel.title_label.text(), "LYA Commands")
        self.assertIn("Available commands", d.panel.answer.toPlainText())

        # Test time command
        d.command("time")
        self.assertRegex(d.panel.title_label.text(), r"\d{1,2}:\d{2} [AP]M")

    def test_voice_wake_signal_dispatch(self):
        d = self.desktop
        d.sleep()
        self.assertFalse(d.orb.isVisible())
        self.assertFalse(d.panel.isVisible())

        # 1. Voice wake utterance triggers wake, reveals crystal, opens panel, executes command
        d.voice_signals.wake_detected.emit("time", True)
        QTest.qWait(60)
        self.assertTrue(d.orb.isVisible())
        self.assertTrue(d.panel.isVisible())
        self.assertRegex(d.panel.title_label.text(), r"\d{1,2}:\d{2} [AP]M")

        # 2. Voice "stop" closes panel
        d.voice_signals.wake_detected.emit("stop", False)
        QTest.qWait(60)
        self.assertFalse(d.panel.isVisible())

        # 3. Voice "status" reopens and reports system readiness
        d.voice_signals.wake_detected.emit("status", True)
        QTest.qWait(60)
        self.assertTrue(d.panel.isVisible())
        self.assertEqual(d.panel.title_label.text(), "System Readiness")

        # 4. Voice "sleep" puts crystal to sleep
        d.voice_signals.wake_detected.emit("sleep", False)
        QTest.qWait(60)
        # Without a system tray (e.g. offscreen Qt), keep the orb recoverable.
        self.assertEqual(d.orb.isVisible(), not d.tray.isVisible())

    def test_voice_enables_claps_and_surfaces_listener_failures(self):
        from unittest.mock import patch
        d = self.desktop
        with patch('threading.Thread') as thread, patch('audio.voice.wake_loop') as listen:
            d.start_voice()
            thread.call_args.kwargs['target']()
            self.assertTrue(listen.call_args.kwargs['clap_enabled'])
            listen.call_args.kwargs['on_ready']()
            self.assertIn('CLAP TWICE', d.orb.toolTip())
            listen.call_args.kwargs['on_error']('SyntheticError')
            self.assertIn('SyntheticError', d.panel.footnote.text())
        d.on_voice_status('VOICE UNAVAILABLE · synthetic test')
        self.assertTrue(d.panel.isVisible())
        self.assertIn('VOICE UNAVAILABLE', d.panel.answer.toPlainText())

    def test_nvidia_voice_checks_current_privacy_before_each_question(self):
        from unittest.mock import patch
        d = self.desktop
        d.cloud_asr = 'nvidia'
        d.brain.private_mode = False
        with patch('threading.Thread') as thread, patch('audio.voice.wake_loop') as listen:
            d.start_voice(allow_cloud=True)
            thread.call_args.kwargs['target']()
            policy = listen.call_args.kwargs['offline_required']
            self.assertFalse(policy())
            self.assertEqual(listen.call_args.kwargs['cloud_provider'], 'nvidia')
            self.assertTrue(listen.call_args.kwargs['cloud_only'])
            listen.call_args.kwargs['on_provider']('Whisper Large v3', True)
            self.assertIn('BACKUP', d.panel.footnote.text())
            listen.call_args.kwargs['on_ready']()
            self.assertIn('NVIDIA', d.panel.footnote.text())
            d.brain.private_mode = True
            self.assertTrue(policy())
            listen.call_args.kwargs['on_ready']()
            self.assertIn('AUDIO STAYS ON DEVICE', d.panel.footnote.text())

    def test_nvidia_selection_alone_keeps_cloud_audio_disabled(self):
        from unittest.mock import patch
        d = self.desktop
        d.cloud_asr = 'nvidia'
        with patch('threading.Thread') as thread, patch('audio.voice.wake_loop') as listen:
            d.start_voice()
            thread.call_args.kwargs['target']()
            self.assertTrue(listen.call_args.kwargs['offline_required']())

    def test_online_private_mode_tells_owner_to_use_text(self):
        d = self.desktop
        d.cloud_voice = True
        d.cloud_asr = 'nvidia'
        d.brain.private_mode = True
        message = d.on_voice_retry()
        self.assertIn('type your private question', message)

    def test_microphone_self_test_reports_without_a_second_microphone_reader(self):
        from unittest.mock import Mock, patch
        import audio.voice as voice
        d = self.desktop
        d.voice_thread = Mock()
        report = {'device': 'Synthetic microphone', 'seconds': 5.0, 'elapsed': 5.2, 'blocks': 250,
                  'samples': 80000, 'peak': 4200, 'loud_blocks': 42, 'claps': 0, 'suppressed': 0,
                  'threshold': 700, 'rms_mean': 130.5, 'rms_min': 3.0, 'rms_max': 1900.0,
                  'listening': True, 'verdict': 'hearing', 'detail': 'Synthetic detail.'}
        with patch.object(voice, 'listener_health', return_value={'listening': True, 'state': 'listening',
                                                                 'device': 'Synthetic microphone'}), \
             patch.object(voice, 'mic_test_start') as start, \
             patch.object(voice, 'mic_test_report', return_value=report), \
             patch('sounddevice.RawInputStream', side_effect=AssertionError('second microphone reader')):
            d.microphone_self_test()
            self.assertTrue(start.called)
            self.assertTrue(d._mic_test_timer.isActive())
            d.finish_microphone_self_test()
            d._mic_test_timer.stop()
        self.assertEqual(d.panel.title_label.text(), "Sound reaches the microphone.")
        self.assertIn('Synthetic microphone', d.panel.answer.toPlainText())
        self.assertIn('42', d.panel.answer.toPlainText())
        self.assertIn('Synthetic detail.', d.panel.answer.toPlainText())
        self.assertEqual(d.orb.task, 'success')

    def test_microphone_self_test_refuses_when_the_listener_is_off(self):
        from unittest.mock import Mock, patch
        import audio.voice as voice
        d = self.desktop
        d.voice_thread = Mock()
        with patch.object(voice, 'listener_health',
                          return_value={'listening': False, 'state': 'stopped', 'device': None}), \
             patch.object(voice, 'mic_test_start') as start:
            d.microphone_self_test()
        self.assertFalse(start.called)
        self.assertIn('not running', d.panel.answer.toPlainText())
        self.assertNotEqual(d.orb.task, 'success')

    def test_motion_stops_on_hide_and_reduced_motion(self):
        orb = self.desktop.orb
        orb.show()
        orb.set_reduced_motion(False)
        self.assertTrue(orb.timer.isActive())
        orb.hide()
        self.assertFalse(orb.timer.isActive())
        orb.show()
        orb.set_reduced_motion(True)
        self.assertFalse(orb.timer.isActive())

    def test_idle_burst_finishes_and_interaction_can_restart_it(self):
        orb = self.desktop.orb
        orb.show()
        orb.set_reduced_motion(False)
        self.assertTrue(orb.timer.isActive())
        orb.motion_until = time.monotonic() - 1
        orb.tick()
        self.assertFalse(orb.timer.isActive())
        self.assertEqual(orb.phase, 0)
        orb.animate_briefly()
        self.assertTrue(orb.timer.isActive())
        orb.hide()
        orb.animate_briefly()
        self.assertFalse(orb.timer.isActive())
        orb.set_state(task="thinking")
        self.assertEqual(orb.animation.state(), orb.animation.State.Stopped)

    def test_model_artwork_can_revert_and_bad_decode_uses_original(self):
        from unittest.mock import patch, MagicMock
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QImage
        orb = self.desktop.orb
        self.assertFalse(orb.using_model)
        orb.set_artwork(True)
        self.assertTrue(orb.using_model)
        self.assertEqual(orb.base.size(), QSize(288, 408))
        self.assertTrue(any(orb.base.toImage().pixelColor(x, 200).alpha() for x in range(50, 230)))
        orb.set_artwork(False)
        self.assertFalse(orb.using_model)
        self.assertEqual(orb.base.cacheKey(), orb.original.cacheKey())
        reader = MagicMock()
        reader.size.return_value = QSize(288, 408)
        reader.read.return_value = QImage()
        with patch('app.QImageReader', return_value=reader):
            failed = Crystal()
        self.assertFalse(failed.using_model)
        self.assertFalse(failed.base.isNull())
        failed.deleteLater()

    def test_slow_paint_falls_back_and_updates_motion_control(self):
        orb = self.desktop.orb
        orb.set_artwork(True)
        orb.show()
        orb.set_reduced_motion(False)
        QTest.qWait(40)
        orb.paint_samples = [20.0] * 30
        orb.repaint()
        QTest.qWait(60)
        self.assertFalse(orb.using_model)
        self.assertTrue(orb.reduced_motion)
        self.assertFalse(orb.timer.isActive())
        self.assertTrue(self.desktop.motion_action.isChecked())

    def wait_for_brain(self):
        for _ in range(500):
            if not self.desktop.brain_busy:
                return
            QTest.qWait(20)
        self.fail("Brain worker did not finish")

    def test_native_brain_dispatch_and_cosmetic_role_stays_locked(self):
        d = self.desktop
        d.command("person admin")
        d.command("show memories")
        self.wait_for_brain()
        self.assertIn("locked", d.panel.answer.toPlainText())
        self.assertIsNone(d.brain.session.person_id)
        d.command("who am i")
        self.wait_for_brain()
        self.assertIn("Guest / unverified", d.panel.answer.toPlainText())

    def test_brain_cancel_during_worker_does_not_reopen_panel(self):
        import threading
        started, release = threading.Event(), threading.Event()
        def delayed(messages):
            started.set()
            release.wait(2)
            return "STALE BRAIN RESULT"
        d = self.desktop
        d.brain.client = delayed
        d.command("hello")
        for _ in range(100):
            if started.is_set():
                break
            QTest.qWait(10)
        self.assertTrue(started.is_set())
        d.close_panel()
        release.set()
        self.wait_for_brain()
        self.assertFalse(d.panel.isVisible())
        self.assertNotIn("STALE BRAIN RESULT", d.panel.answer.toPlainText())

    def test_isolated_demo_runs_from_native_command(self):
        self.desktop.command("brain demo")
        self.wait_for_brain()
        self.assertIn("SYNTHETIC DEMO", self.desktop.panel.answer.toPlainText())
        self.assertIsNone(self.desktop.brain.session.person_id)

    def test_file_rows_are_readable_and_enter_loads_actual_document(self):
        d = self.desktop
        d.show_files()
        QTest.qWait(60)
        for i in range(d.panel.files.count()):
            row = d.panel.files.itemWidget(d.panel.files.item(i))
            for label in row.findChildren(QLabel):
                self.assertGreaterEqual(label.height(), label.fontMetrics().height())
        d.panel.files.setCurrentRow(3)
        d.panel.files.setFocus()
        QTest.keyClick(d.panel.files, Qt.Key.Key_Return)
        for _ in range(100):
            if d.orb.task != "thinking":
                break
            QTest.qWait(10)
        self.assertEqual(d.panel.answer.toPlainText(), read_project_document("README.md"))


def measure_motion(use_model=True):
    orb = Crystal()
    orb.set_artwork(use_model)
    orb.show()
    ticks = []
    from PySide6.QtCore import QTimer
    beat = QTimer()
    beat.timeout.connect(lambda: ticks.append(time.perf_counter()))
    beat.start(16)
    start_cpu, start_wall = time.process_time(), time.perf_counter()
    for task in ("listening", "thinking", "files", "success", "idle"):
        orb.set_state(task=task)
        QTest.qWait(500)
    cpu, wall = time.process_time() - start_cpu, time.perf_counter() - start_wall
    beat.stop()
    samples = orb.paint_samples
    gaps = [(b - a) * 1000 for a, b in zip(ticks, ticks[1:])]
    result = {"duration_seconds": round(wall, 3), "process_cpu_seconds": round(cpu, 3),
              "paint_count": len(samples), "paint_median_ms": round(statistics.median(samples), 3),
              "paint_max_ms": round(max(samples), 3), "event_gap_max_ms": round(max(gaps), 3),
              "limits": "Short local Qt smoke measurement; excludes sensors/model/network, not a guarantee of display FPS or sustained performance."}
    QTest.qWait(3300)
    count = len(orb.paint_samples)
    QTest.qWait(1200)
    result.update(artwork="model_bake" if use_model else "original",
                  idle_timer_active=orb.timer.isActive(),
                  idle_paint_delta=len(orb.paint_samples)-count)
    unique = {p.cacheKey(): p for p in [orb.base, orb.original, orb.model_art, orb.previous, orb.current, *orb.frames.values()] if not p.isNull()}
    result['estimated_unique_pixmap_bytes'] = sum(p.width()*p.height()*4 for p in unique.values())
    orb.hide()
    orb.deleteLater()
    return result


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    outcome = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InterfaceChecks))
    if not outcome.wasSuccessful():
        sys.exit(1)
    render_sample(False)
    render_sample(True)
    render_sample(False, task="idle", message=True)
    measurement = measure_motion()
    (OUTPUT / "measurement.json").write_text(json.dumps(measurement, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(measurement, indent=2))
