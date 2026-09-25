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
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtTest import QTest

from layout import Box, place_panel, accent
from app import Desktop, Crystal, GlassPanel, read_project_document, WINDOW_FLAGS

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
