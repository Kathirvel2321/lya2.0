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
from camera_eyes import VisionDialog, VisionCanvas
from vision.scan import encode_frame
from security.policy import Session

APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class CameraDialogTests(unittest.TestCase):
    def setUp(self):
        self.token = Session('admin', 'Synthetic owner', 'fake-session', 'fake-person', time.time()+60)
        self.dialog = VisionDialog(access_check=lambda: self.token)
        self.addCleanup(self.dialog.close)
        self.answer = []
        self.dialog.answer_ready.connect(lambda request, text: self.answer.append((request, text)))
        self.scene = {'width': 640, 'height': 480, 'ready': True, 'analyzed_at': time.monotonic(),
                      'faces': [], 'objects': [{'label': 'bottle', 'confidence': .85, 'box': [280, 180, 350, 300]}]}
        self.image = encode_frame(np.zeros((480, 640, 3), np.uint8))
        self.dialog.checked_pixmap = self.dialog.packet_pixmap(self.image['image'], 640, 480)
        self.dialog.checked_at = self.scene['analyzed_at']

    def test_fresh_analysis_answers_reference_without_another_capture(self):
        self.dialog.last_result = self.scene
        with patch.object(self.dialog.process, 'state', return_value=QProcess.ProcessState.Running), \
             patch.object(self.dialog.process, 'start', side_effect=AssertionError('Unexpected camera start')):
            self.dialog.ask('what is this?', 12)
        self.assertEqual(len(self.answer), 1)
        self.assertEqual(self.answer[0][0], 12)
        self.assertIn('possible bottle', self.answer[0][1])
        self.assertEqual(self.dialog.scene.selected['box'], self.scene['objects'][0]['box'])
        self.assertIn('Checked frame', self.dialog.status.text())

    def test_new_video_does_not_make_old_analysis_fresh(self):
        self.scene['analyzed_at'] = time.monotonic() - 5
        self.dialog.last_result = self.scene
        self.dialog.last_seen = time.monotonic()
        with patch.object(self.dialog.process, 'state', return_value=QProcess.ProcessState.Running):
            self.dialog.ask('what is this?', 12)
        self.assertEqual(self.answer, [])
        self.assertIsNotNone(self.dialog.pending_question)
        self.scene['analyzed_at'] = time.monotonic()
        self.dialog.checked_at = self.scene['analyzed_at']
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
        current = {**image, **self.scene, 'checked_image': image['image']}
        packets = (json.dumps(old) + '\n' + json.dumps(current) + '\n').encode()
        self.dialog.pending_question = (12, 'what is this?')
        with patch.object(self.dialog.process, 'readAllStandardOutput', return_value=packets):
            self.dialog._read_output()
        self.assertIn('possible bottle', self.answer[0][1])
        self.assertNotIn('cup', self.answer[0][1])

    def test_default_denial_applies_to_button_and_question(self):
        locked = VisionDialog()
        self.addCleanup(locked.close)
        with patch.object(locked.process, 'start') as start:
            locked.toggle_live()
            locked.ask('what can you see?', 12)
        start.assert_not_called()
        self.assertIn('locked', locked.status.text())
        self.assertIsNone(locked.last_result)

    def test_access_failure_between_start_checks_never_launches(self):
        self.dialog.access_check = iter([self.token]).__next__
        with patch.object(self.dialog.process, 'start') as start:
            self.dialog.toggle_live()
        start.assert_not_called()
        self.assertIn('locked', self.dialog.status.text())

    def test_batched_checked_packet_survives_newer_live_video(self):
        self.dialog.checked_at = 0
        checked = {**self.image, **self.scene, 'checked_image': self.image['image']}
        current = {**self.image, **self.scene}
        self.dialog.pending_question = (12, 'what is this?')
        packets = (json.dumps(checked)+'\n'+json.dumps(current)+'\n').encode()
        with patch.object(self.dialog.process, 'readAllStandardOutput', return_value=packets):
            self.dialog._read_output()
        self.assertEqual(self.dialog.checked_at, self.scene['analyzed_at'])
        self.assertIn('possible bottle', self.answer[0][1])

    def test_new_question_survives_previous_focus_cancellation(self):
        self.dialog.focus_active = True
        self.dialog.focus_cleared.connect(lambda: setattr(self.dialog, 'pending_question', None))
        self.dialog.last_result = self.scene
        with patch.object(self.dialog.process, 'state', return_value=QProcess.ProcessState.Running):
            self.dialog.ask('what is this?', 13)
        self.assertEqual(self.answer[0][0], 13)

    def test_replaced_owner_session_is_denied(self):
        self.dialog.owner_token = self.token
        self.token = Session('admin', 'Synthetic owner', 'other-session', 'fake-person', time.time()+60)
        self.assertFalse(self.dialog.authorized())

    def test_revocation_kills_worker_and_clears_checked_pixels(self):
        self.dialog.owner_token = self.token
        self.dialog.last_result = self.scene
        self.token = None
        with patch.object(self.dialog.process, 'state', return_value=QProcess.ProcessState.Running), patch.object(
                self.dialog.process, 'kill') as kill, patch.object(self.dialog.process, 'waitForFinished'):
            self.dialog.check_access()
        kill.assert_called_once()
        self.assertTrue(self.dialog.checked_pixmap.isNull())
        self.assertIsNone(self.dialog.last_result)
        self.assertFalse(self.dialog.access_timer.isActive())

    def test_worker_has_no_provider_secrets_and_bounded_threads(self):
        with patch.dict(os.environ, {'NVIDIA_API_KEY': 'fake-secret', 'GROQ_API_KEY': 'fake-secret'}), patch.object(
                self.dialog.process, 'start') as start:
            self.dialog.toggle_live()
        environment = self.dialog.process.processEnvironment()
        self.assertFalse(environment.contains('NVIDIA_API_KEY'))
        self.assertFalse(environment.contains('GROQ_API_KEY'))
        self.assertEqual(environment.value('OMP_NUM_THREADS'), '2')
        self.assertEqual(start.call_args.args[1][-1], str(self.token.verified_until))

    def test_mismatched_checked_frame_does_not_dispatch_or_mark(self):
        self.dialog.last_result = self.scene
        self.dialog.checked_at -= 1
        with patch.object(self.dialog.process, 'state', return_value=QProcess.ProcessState.Running):
            self.dialog.ask('what is this?', 12)
        self.assertEqual(self.answer, [])
        self.assertFalse(self.dialog.focus_active)

    def test_malformed_packets_fail_closed_before_image_decode(self):
        for changes in ({'width': 99999}, {'objects': self.scene['objects'] * 13},
                        {'objects': [{'label': 'injected instruction', 'confidence': .9, 'box': [1, 1, 2, 2]}]},
                        {'hands': [{'points': [], 'confidence': .9}]}, {'analyzed_at': float('nan')}):
            with self.subTest(changes=changes):
                self.dialog.stopping = False
                packet = {**self.image, **self.scene, **changes}
                with patch.object(self.dialog.process, 'readAllStandardOutput', return_value=(json.dumps(packet)+'\n').encode()):
                    self.dialog._read_output()
                self.assertTrue(self.dialog.checked_pixmap.isNull())
                self.assertIsNone(self.dialog.last_result)

    def test_overlay_uses_letterboxed_image_rectangle(self):
        canvas = VisionCanvas()
        canvas.setPixmap(self.dialog.checked_pixmap)
        canvas.resize(800, 800)
        target = canvas.image_rect()
        self.assertEqual((target.x(), target.y(), target.width(), target.height()), (0, 100, 800, 600))
        canvas.items = self.scene['objects']
        canvas.selected = self.scene['objects'][0]
        image = canvas.grab().toImage()
        self.assertGreater(image.pixelColor(350, 325).green(), 200)


if __name__ == '__main__':
    unittest.main()
