"""Synthetic camera packets only; child/camera activation is always mocked."""
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent / 'desktop'))
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication
from camera_eyes import VisionDialog
from vision.scan import encode_frame

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class CameraDialogTests(unittest.TestCase):
    def setUp(self):
        self.dialog = VisionDialog()
        self.addCleanup(self.dialog.close)
        self.answer = []
        self.dialog.answer_ready.connect(lambda request, text: self.answer.append((request, text)))
        self.scene = {'width': 640, 'height': 480, 'ready': True, 'analyzed_at': time.monotonic(),
                      'faces': [], 'objects': [{'label': 'bottle', 'confidence': .85, 'box': [280, 180, 350, 300]}]}

    def test_fresh_analysis_answers_reference_without_another_capture(self):
        self.dialog.last_result = self.scene
        with patch.object(self.dialog.process, 'state', return_value=QProcess.ProcessState.Running), \
             patch.object(self.dialog.process, 'start', side_effect=AssertionError('Unexpected camera start')):
            self.dialog.ask('what is this?', 12)
        self.assertEqual(len(self.answer), 1)
        self.assertEqual(self.answer[0][0], 12)
        self.assertIn('possible bottle', self.answer[0][1])

    def test_new_video_does_not_make_old_analysis_fresh(self):
        self.scene['analyzed_at'] = time.monotonic() - 5
        self.dialog.last_result = self.scene
        self.dialog.last_seen = time.monotonic()
        with patch.object(self.dialog.process, 'state', return_value=QProcess.ProcessState.Running):
            self.dialog.ask('what is this?', 12)
        self.assertEqual(self.answer, [])
        self.assertIsNotNone(self.dialog.pending_question)
        self.scene['analyzed_at'] = time.monotonic()
        self.dialog._answer_pending()
        self.assertEqual(len(self.answer), 1)

    def test_stream_error_replies_to_pending_question_and_clears_scene(self):
        self.dialog.pending_question = (12, 'what is this?')
        self.dialog.last_result = self.scene
        packet = b'{"error":"synthetic camera unavailable"}\n'
        with patch.object(self.dialog.process, 'readAllStandardOutput', return_value=packet):
            self.dialog._read_output()
        self.assertEqual(len(self.answer), 1)
        self.assertIn('camera stopped', self.answer[0][1])
        self.assertIsNone(self.dialog.last_result)
        self.assertIsNone(self.dialog.pending_question)

    def test_close_discards_pending_reference_and_in_memory_scene(self):
        self.dialog.pending_question = (12, 'what is this?')
        self.dialog.last_result = self.scene
        self.dialog.close()
        self.assertIsNone(self.dialog.last_result)
        self.assertIsNone(self.dialog.pending_question)
        self.assertFalse(self.dialog.timer.isActive())
        self.assertEqual(self.answer, [])

    def test_oversized_stream_replies_to_pending_question(self):
        self.dialog.pending_question = (12, 'what is this?')
        with patch.object(self.dialog.process, 'readAllStandardOutput', return_value=b'x' * 4_000_001):
            self.dialog._read_output()
        self.assertEqual(len(self.answer), 1)
        self.assertIn('camera stopped', self.answer[0][1])
        self.assertIsNone(self.dialog.pending_question)

    def test_only_newest_synthetic_packet_is_answered(self):
        image = encode_frame(np.zeros((480, 640, 3), np.uint8))
        old = {**image, **self.scene, 'objects': [{'label': 'cup', 'confidence': .9, 'box': [280, 180, 350, 300]}]}
        current = {**image, **self.scene}
        packets = (json.dumps(old) + '\n' + json.dumps(current) + '\n').encode()
        self.dialog.pending_question = (12, 'what is this?')
        with patch.object(self.dialog.process, 'readAllStandardOutput', return_value=packets):
            self.dialog._read_output()
        self.assertIn('possible bottle', self.answer[0][1])
        self.assertNotIn('cup', self.answer[0][1])


if __name__ == '__main__':
    unittest.main()
