"""Sensor-free tests for local vision and explicit desktop activation."""
import unittest
from unittest.mock import patch

import numpy as np
from vision import scan
from vision.answers import answer_scene, is_visual_question


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
