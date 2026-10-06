"""Sensor-free tests for local vision and explicit desktop activation."""
import unittest
from unittest.mock import patch

import numpy as np
from vision import scan
from vision.answers import answer_scene, is_visual_question
from vision.answers import scene_result


class FakeCamera:
    def __init__(self, opened=True, frame=None):
        self.opened = opened
        self.frame = frame
        self.released = False
        self.reads = 0

    def isOpened(self):
        return self.opened

    def set(self, *_):
        return True

    def read(self):
        self.reads += 1
        return self.frame is not None, self.frame

    def release(self):
        self.released = True


class VisionTests(unittest.TestCase):
    def test_worker_lease_expiry_parent_loss_and_actual_network_hook(self):
        import io
        import subprocess
        import sys
        lease = {'until': 103, 'connected': True}
        with patch.object(scan.time, 'monotonic', return_value=100), patch.object(scan.time, 'time', return_value=1000):
            self.assertTrue(scan.camera_lease_valid(lease, 1001))
            self.assertFalse(scan.camera_lease_valid(lease, 999))
            lease['until'] = 99
            self.assertFalse(scan.camera_lease_valid(lease, 1001))
            scan.renew_camera_lease(io.BytesIO(b'lease\n'), lease)
            self.assertEqual(lease['until'], 103)
            self.assertFalse(scan.camera_lease_valid(lease, 1001))  # EOF closes authorization.
        code = '''import sys, socket
from vision.scan import camera_worker_guard
sys.addaudithook(camera_worker_guard)
try:
    socket.socket().connect(('127.0.0.1', 9))
except PermissionError:
    print('NETWORK BLOCKED')
else:
    raise AssertionError('Network guard failed')
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'NETWORK BLOCKED')

    def test_scene_tour_retains_distinct_instances_and_duplicate_target_is_ambiguous(self):
        scene = {'width': 640, 'height': 480, 'objects': [
            {'label': 'bottle', 'confidence': .8, 'box': [400, 100, 440, 250]},
            {'label': 'bottle', 'confidence': .9, 'box': [30, 100, 70, 250]}]}
        result = scene_result('what all can you see?', scene)
        self.assertTrue(result['tour'])
        self.assertEqual([item['number'] for item in result['items']], [1, 2])
        self.assertEqual(result['items'][0]['box'], [30, 100, 70, 250])
        named = scene_result('find my bottle', scene)
        self.assertIsNone(named['selected'])
        self.assertIn('several', named['text'])
        self.assertEqual(len(named['items']), 2)
        self.assertTrue(is_visual_question('look at the bottle', camera_active=True))
        self.assertFalse(is_visual_question("don't scan all objects", camera_active=True))
        scene['objects'] *= 7
        self.assertEqual(len(scene_result('scan all objects', scene)['items']), 12)
        self.assertIn('12-item limit', scene_result('scan all objects', scene)['text'])

    def test_camera_worker_guard_blocks_networking_commands_and_denied_capture(self):
        for event in ('socket.connect', 'socket.bind', 'socket.sendto', 'socket.getaddrinfo',
                      'urllib.Request', 'subprocess.Popen', 'os.system', 'os.posix_spawn'):
            with self.assertRaises(PermissionError):
                scan.camera_worker_guard(event, ())
        with patch.object(scan, 'verify_models'), patch('cv2.VideoCapture') as camera:
            with self.assertRaises(PermissionError):
                next(scan.live_frames(authorized=lambda: False))
        camera.assert_not_called()

    def test_checked_pixels_are_from_analyzed_frame_and_auth_loss_releases(self):
        import cv2
        import base64
        engine = type('FakeEngine', (), {'analyze': lambda self, frame: {'pixel': int(frame[0, 0, 0])}})()
        frame = np.full((480, 640, 3), 64, np.uint8)
        checked = scan._checked_frame(engine, frame)
        decoded = cv2.imdecode(np.frombuffer(base64.b64decode(checked['checked_image']), np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(checked['pixel'], 64)
        self.assertEqual(int(decoded[0, 0, 0]), 64)
        camera = FakeCamera(frame=frame)
        checks = iter([True, True, False])
        with patch.object(scan, 'verify_models'), patch.object(scan, 'VisionEngine', return_value=engine):
            frames = list(scan.live_frames(lambda *_: camera, authorized=lambda: next(checks)))
        self.assertEqual(len(frames), 1)
        self.assertTrue(camera.released)
    def test_public_shape_blank_frame_has_no_invented_objects_or_faces(self):
        result = scan.scan_frame(np.zeros((480, 640, 3), dtype=np.uint8))
        self.assertEqual(result['faces'], [])
        self.assertEqual(result['objects'], [])
        self.assertEqual(result['identity'], 'unknown')
        self.assertGreater(len(result['image']), 100)

    def test_one_shot_camera_releases_after_bounded_reads(self):
        camera = FakeCamera(frame=np.zeros((480, 640, 3), dtype=np.uint8))
        with patch.object(scan, 'scan_frame', return_value={'identity': 'unknown'}) as analyze:
            result = scan.capture_once(lambda *_: camera)
        self.assertEqual(result['identity'], 'unknown')
        self.assertEqual(camera.reads, 3)
        self.assertTrue(camera.released)
        analyze.assert_called_once()

    def test_unavailable_camera_releases_and_fails_closed(self):
        camera = FakeCamera(opened=False)
        with self.assertRaisesRegex(RuntimeError, 'Camera unavailable'):
            scan.capture_once(lambda *_: camera)
        self.assertTrue(camera.released)

    def test_live_camera_reuses_engine_and_releases_on_limit(self):
        camera = FakeCamera(frame=np.zeros((480, 640, 3), dtype=np.uint8))
        fake_engine = type('FakeEngine', (), {'analyze': lambda self, frame: {
            'faces': [], 'objects': [], 'identity': 'unknown'}})()
        with patch.object(scan, 'verify_models'), patch.object(scan, 'VisionEngine', return_value=fake_engine) as engine:
            frames = list(scan.live_frames(lambda *_: camera, max_frames=2))
        self.assertEqual(len(frames), 2)
        self.assertEqual(camera.reads, 2)
        self.assertTrue(camera.released)
        engine.assert_called_once()
        self.assertTrue(all(frame['identity'] == 'unknown' for frame in frames))

    def test_live_answers_are_grounded_and_do_not_grant_identity(self):
        scene = {'width': 640, 'height': 480, 'faces': [[20, 20, 80, 80]],
                 'objects': [{'label': 'bottle', 'confidence': .8, 'box': [40, 310, 90, 410]}],
                 'identity': 'unknown'}
        self.assertIn('bottom left', answer_scene('where is my bottle?', scene))
        self.assertIn('cannot identify', answer_scene('is anyone there?', scene))
        self.assertIn('cannot judge', answer_scene('is anyone suspicious?', scene))
        self.assertIn('no pen class', answer_scene('find my pen', scene))
        self.assertIn('Start live view', answer_scene('where is my bottle?', scene, fresh=False))
        self.assertTrue(is_visual_question('LYA, can you see my pen?'))
        self.assertTrue(is_visual_question('Do you see anyone suspicious?'))
        self.assertFalse(is_visual_question('Where is my project file?'))


if __name__ == '__main__':
    unittest.main()
