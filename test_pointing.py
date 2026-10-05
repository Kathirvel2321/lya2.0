"""Synthetic landmark/object tests; no camera, network, owner frame or store."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
from vision import hands
from vision.answers import answer_scene, is_visual_question


def pointing_hand():
    points = [[100., 250.] for _ in range(21)]
    points[5], points[6], points[7], points[8] = [105, 200], [130, 200], [150, 200], [170, 200]
    points[9], points[10], points[12] = [105, 220], [120, 210], [110, 245]
    points[14], points[16] = [120, 215], [108, 247]
    points[18], points[20] = [115, 220], [107, 246]
    return {'points': points, 'confidence': .95}


def scene(objects=None):
    return {'width': 640, 'height': 480, 'faces': [], 'hand_status': 'ready',
            'hands': [pointing_hand()], 'objects': objects or [
                {'label': 'bottle', 'confidence': .85, 'box': [260, 160, 320, 280]}]}


class PointingTests(unittest.TestCase):
    def test_pointing_hand_is_distinct_from_open_palm_or_low_confidence(self):
        hand = pointing_hand()
        self.assertEqual(len(hands.pointing_rays([hand])), 1)
        opened = copy.deepcopy(hand)
        for tip in (12, 16, 20):
            opened['points'][tip] = [180, 200]
        self.assertEqual(hands.pointing_rays([opened]), [])
        hand['confidence'] = .5
        self.assertEqual(hands.pointing_rays([hand]), [])

    def test_bent_or_tiny_index_is_not_a_clear_point(self):
        hand = pointing_hand()
        hand['points'][8] = [110, 240]
        self.assertEqual(hands.pointing_rays([hand]), [])
        hand = pointing_hand()
        hand['points'] = [[x / 20, y / 20] for x, y in hand['points']]
        self.assertEqual(hands.pointing_rays([hand]), [])

    def test_points_behind_finger_or_off_its_direction_are_not_selected(self):
        for box in ([10, 160, 50, 280], [260, 30, 320, 80]):
            sample = scene([{'label': 'cup', 'confidence': .9, 'box': box}])
            item, reason = hands.referenced_object(sample, 'pointing')
            self.assertIsNone(item)
            self.assertIn('cannot confidently identify', reason)

    def test_unambiguous_finger_direction_names_the_detected_object(self):
        answer = answer_scene('Lya, what am I pointing at?', scene())
        self.assertIn('possible bottle', answer)
        self.assertIn('pointing direction', answer)

    def test_multiple_aligned_objects_require_clarification(self):
        sample = scene()
        sample['objects'].append({'label': 'cup', 'confidence': .9, 'box': [380, 160, 420, 280]})
        answer = answer_scene('what am i pointing at', sample)
        self.assertIn('Several objects', answer)
        self.assertNotIn('possible bottle', answer)

    def test_person_and_backdrop_are_not_a_pointing_target(self):
        sample = scene()
        sample['objects'].extend([
            {'label': 'person', 'confidence': .98, 'box': [0, 0, 640, 480]},
            {'label': 'dining table', 'confidence': .9, 'box': [0, 140, 600, 400]}])
        self.assertIn('possible bottle', answer_scene('what am i pointing at', sample))

    def test_no_hand_or_unsupported_models_do_not_invent_a_point(self):
        sample = scene()
        sample['hands'] = []
        self.assertIn('cannot see a clear pointing finger', answer_scene('what am i pointing at', sample))
        sample['hand_status'] = 'unavailable'
        self.assertIn('unavailable', answer_scene('what am i pointing at', sample))

    def test_centered_reference_is_not_just_the_first_detection(self):
        sample = scene([
            {'label': 'chair', 'confidence': .95, 'box': [0, 0, 70, 90]},
            {'label': 'cup', 'confidence': .85, 'box': [290, 190, 340, 300]}])
        sample['hands'] = []
        self.assertIn('possible cup', answer_scene('what is this', sample))
        sample['objects'].append({'label': 'bottle', 'confidence': .8, 'box': [350, 190, 400, 300]})
        self.assertIn('several possible objects', answer_scene('what is this', sample))

    def test_held_reference_requires_visible_hand_and_detected_object(self):
        sample = scene([{'label': 'cell phone', 'confidence': .9, 'box': [155, 185, 200, 255]}])
        self.assertIn('Near your hand', answer_scene('what am i holding', sample))
        sample['hands'] = []
        self.assertIn('cannot see your hand clearly', answer_scene('what am i holding', sample))

    def test_reference_routes_are_specific_and_bare_this_needs_a_live_camera(self):
        for question in ('what object is this?', 'what am i holding?', 'Lya, what am I pointing at?',
                         'what object is near me?', 'Hey Lya, what do you see?'):
            self.assertTrue(is_visual_question(question), question)
        self.assertFalse(is_visual_question('what is this?'))
        self.assertTrue(is_visual_question('Lya, what is this?', camera_active=True))
        self.assertTrue(is_visual_question("Lya, what's this?", camera_active=True))
        for question in ('what is this error?', 'what is this code?', 'where is my project file?'):
            self.assertFalse(is_visual_question(question, camera_active=True), question)

    def test_stale_scene_cannot_identify_a_reference(self):
        self.assertIn('current camera view', answer_scene('what am i pointing at', scene(), fresh=False))

    def test_natural_camera_requests_and_negative_or_settings_requests(self):
        from vision.answers import camera_control
        for text in ('open camera', 'Please open the camera.', 'Lya, can you turn on my camera?',
                     'Open the camera and see me. You cover that.'):
            self.assertEqual(camera_control(text), 'open', text)
        for text in ('close camera', 'Please close the camera.', 'Lya, turn off my camera now'):
            self.assertEqual(camera_control(text), 'close', text)
        for text in ('do not open camera', "don't open the camera", 'why does the camera open?',
                     'how can I open the camera?', 'open camera settings', 'open camera photos'):
            self.assertIsNone(camera_control(text), text)
            self.assertFalse(is_visual_question(text), text)

    def test_open_and_see_me_is_a_local_presence_question(self):
        text = 'Open the camera and see me. You cover that.'
        self.assertTrue(is_visual_question(text))
        sample = scene()
        sample['faces'] = [[10, 10, 50, 60]]
        self.assertIn('1 person(s)', answer_scene(text, sample))
        self.assertIn('cannot identify', answer_scene(text, sample))
        self.assertTrue(is_visual_question('Lya, can you see me?'))
        sample['faces'] = []
        self.assertIn('cannot confirm a person', answer_scene('can you see me?', sample))

    def test_hand_tracker_rejects_missing_weights_without_downloading(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(hands, 'MODEL_DIR', Path(folder)):
            with self.assertRaises(RuntimeError):
                hands.HandTracker()

    def test_hand_tracker_limits_pose_jobs_and_returns_only_image_points(self):
        tracker = hands.HandTracker.__new__(hands.HandTracker)
        tracker.palms = Mock()
        tracker.palms.infer.return_value = [np.r_[np.zeros(18), score] for score in (.7, .9, .8)]
        tracker.pose = Mock()
        tracker.pose.infer.return_value = np.r_[np.zeros(131), .95]
        result = tracker.analyze(np.zeros((100, 100, 3), dtype=np.uint8))
        self.assertEqual(tracker.pose.infer.call_count, 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]['points']), 21)
        self.assertEqual(len(result[0]['points'][0]), 2)


if __name__ == '__main__':
    unittest.main()
