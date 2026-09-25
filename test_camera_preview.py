"""Sensor-free tests for newest-frame display and normal-conversation replies."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import time
import unittest
from unittest.mock import patch
import numpy as np
from PySide6.QtWidgets import QApplication, QLineEdit
from desktop.camera_eyes import VisionDialog
from vision.scan import encode_frame

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)

class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.dialog = VisionDialog()
        self.dialog.show()
        self.replies = []
        self.dialog.answer_ready.connect(lambda request, text: self.replies.append((request, text)))

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()
        APP.processEvents()

    def packet(self, stamp):
        return {**encode_frame(np.zeros((720, 1280, 3), dtype=np.uint8)),
                'faces': [], 'objects': [{'label': 'bottle', 'confidence': .8, 'box': [20, 30, 80, 200]}],
                'identity': 'unknown', 'ready': True, 'analyzed_at': stamp}

    def feed(self, payload):
        with patch.object(self.dialog.process, 'readAllStandardOutput', return_value=payload):
            self.dialog._read_output()

    def test_latest_frame_preserves_native_resolution_without_search_ui(self):
        older, latest = self.packet(1), self.packet(time.monotonic())
        payload = (json.dumps(older)+'\n'+json.dumps(latest)+'\n').encode()
        self.feed(payload[:90])
        self.assertIsNone(self.dialog.last_result)
        self.feed(payload[90:])
        self.assertEqual(self.dialog.last_result['analyzed_at'], latest['analyzed_at'])
        self.assertEqual(self.dialog.scene.pixmap().width(), 1280)
        self.assertEqual(self.dialog.findChildren(QLineEdit), [])
        APP.processEvents()
        self.assertLessEqual(self.dialog.width(), 800)

    def test_camera_only_window_has_no_answer_panel(self):
        self.assertFalse(hasattr(self.dialog, 'answer'))
        self.assertFalse(hasattr(self.dialog, 'question'))

    def test_pending_question_waits_for_fresh_analysis_and_answers_once(self):
        with patch.object(self.dialog, 'toggle_live'):
            self.dialog.ask('where is my bottle?', 7)
        self.feed((json.dumps(self.packet(time.monotonic()-10))+'\n').encode())
        self.assertEqual(self.replies, [])
        self.feed((json.dumps(self.packet(time.monotonic()))+'\n').encode())
        self.assertEqual(len(self.replies), 1)
        self.assertEqual(self.replies[0][0], 7)
        self.assertIn('bottle', self.replies[0][1])
        self.feed((json.dumps(self.packet(time.monotonic()))+'\n').encode())
        self.assertEqual(len(self.replies), 1)

    def test_stop_discards_preview_and_pending_request(self):
        with patch.object(self.dialog, 'toggle_live'):
            self.dialog.ask('where is my bottle?', 8)
        self.dialog.stop_camera()
        self.assertIsNone(self.dialog.last_result)
        self.assertIsNone(self.dialog.pending_question)
        self.assertTrue(self.dialog.scene.pixmap().isNull())
        self.assertEqual(len(self.replies), 0)

if __name__ == '__main__':
    unittest.main()
