"""Real Qt acceptance checks; no Desktop/Brain, sensors, providers or stores.

Run on the owner's installed PySide6 environment:
    python desktop/check_body_qt.py
For a headless Qt installation, set QT_QPA_PLATFORM=offscreen first.
This file is intentionally separate from the fake-Qt headless checks.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app import Crystal
from living_body import create_body_type

APPLICATION = QApplication.instance() or QApplication([])
APPLICATION.setQuitOnLastWindowClosed(False)
Body = create_body_type(Crystal)


class NativeBody(unittest.TestCase):
    def setUp(self):
        self.body = Body()
        self.body.set_reduced_motion(True)
        self.body.show()
        APPLICATION.processEvents()

    def tearDown(self):
        self.body.hide()
        self.body.deleteLater()
        APPLICATION.processEvents()

    def test_paint_fixed_body_at_intro_and_dock_sizes(self):
        self.assertTrue(self.body.body_enabled, 'Required artwork/config missing')
        for width, height in ((230, 315), (96, 112)):
            self.body.setFixedSize(width, height)
            for phase, task in (('listening', 'none'), ('thinking', 'coding'), ('speaking', 'none'),
                                ('idle', 'approval'), ('idle', 'error')):
                self.body.preview_effect(phase, task)
                APPLICATION.processEvents()
                image = self.body.grab().toImage().convertToFormat(QImage.Format.Format_RGBA8888)
                self.assertFalse(image.isNull())
                self.assertTrue(any(image.pixelColor(x, y).alpha() > 0
                                    for x in range(0, image.width(), max(1, image.width() // 30))
                                    for y in range(0, image.height(), max(1, image.height() // 30))),
                                'Rendered body is entirely transparent')
                self.assertEqual((image.width(), image.height()),
                                 (round(width * self.body.devicePixelRatioF()), round(height * self.body.devicePixelRatioF())))
                self.assertFalse(self.body.timer.isActive())
                self.assertIs(self.body.base, self.body.body_art)

    def test_existing_click_keyboard_and_legacy_rollback(self):
        clicks = []
        self.body.activated.connect(lambda: clicks.append(True))
        QTest.mouseClick(self.body, Qt.MouseButton.LeftButton, pos=QPoint(92, 126))
        QTest.keyClick(self.body, Qt.Key.Key_Return)
        self.assertEqual(len(clicks), 2)
        self.body.set_artwork(False)
        self.assertFalse(self.body.body_enabled)
        self.body.set_body_enabled(True)
        self.assertTrue(self.body.body_enabled)

    def test_live_phase_timer_and_hidden_stop(self):
        self.body.set_reduced_motion(False)
        self.body.set_voice_phase('speaking')
        self.assertTrue(self.body.timer.isActive())
        self.assertGreaterEqual(self.body.timer.interval(), 34)
        self.body.hide()
        self.assertFalse(self.body.timer.isActive())


if __name__ == '__main__':
    unittest.main()
