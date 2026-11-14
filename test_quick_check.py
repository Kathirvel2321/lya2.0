"""Tests for the first-glance quick_check and its integration."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vision.quick_check import frame_stats, analyze, MIN_BRIGHTNESS, MIN_SHARPNESS


def make_frame(brightness=128, blur=False, size=(480, 640)):
    import numpy as np
    frame = np.full((size[0], size[1], 3), brightness, dtype=np.uint8)
    if not blur:
        # A black square roughly face-sized keeps YuNet from being the issue
        # in stats-only tests; detection tests mock the detector instead.
        frame[100:220, 250:390] = brightness // 3
    return frame


class StatsTests(unittest.TestCase):
    def test_brightness_measured(self):
        stats = frame_stats(make_frame(brightness=200))
        self.assertGreater(stats["brightness"], 150)

    def test_dark_frame_detected(self):
        verdict = analyze(make_frame(brightness=8))
        self.assertFalse(verdict["usable"])
        self.assertEqual(verdict["reason"], "camera_covered_or_dark")

    def test_blurry_frame_detected(self):
        import numpy as np
        import cv2
        smooth = cv2.GaussianBlur(make_frame(brightness=128), (51, 51), 30)
        verdict = analyze(smooth)
        self.assertFalse(verdict["usable"])
        self.assertEqual(verdict["reason"], "too_blurry")


class DetectorTests(unittest.TestCase):
    def test_no_face_returns_reason(self):
        # A uniformly noisy frame: bright and sharp enough, but no face.
        import numpy as np
        rng = np.random.default_rng(7)
        frame = rng.integers(60, 200, size=(480, 640, 3), dtype=np.uint8)
        verdict = analyze(frame)
        self.assertIn(verdict["reason"],
                      ("no_face_visible", "face_too_small", "too_blurry"))

    def test_analyze_never_raises_on_any_frame(self):
        import numpy as np
        for frame in (np.zeros((10, 10, 3), dtype=np.uint8),
                      np.full((2000, 2000, 3), 128, dtype=np.uint8)):
            verdict = analyze(frame)
            self.assertIn("usable", verdict)


class IntegrationTests(unittest.TestCase):
    def test_recognizer_skips_arcface_on_covered_camera(self):
        from brain import admin_recognizer as R
        import unittest.mock as mock
        calls = []

        def fake_identify(sample, admin_threshold=0.45, db_path=None):
            calls.append(sample)
            return {"status": "unknown", "similarity": 0.1, "verified": False}

        dark = make_frame(brightness=5)
        with mock.patch("vision.identity", create=True) as fake_vi, \
                mock.patch("vision.quick_check._yunet", side_effect=AssertionError("should not run")):
            fake_vi.identify.side_effect = fake_identify
            result = R.recognize_me([dark, dark, dark])
        self.assertEqual(len(calls), 0)          # ArcFace never ran
        self.assertEqual(result["status"], "camera_covered_or_dark")

    def test_workflow_understands_all_quick_reasons(self):
        import re
        source = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "brain", "workflow.py"), encoding="utf-8").read()
        for reason in ("camera_covered_or_dark", "too_blurry", "no_face_visible",
                       "face_too_small", "face_turned_away", "no_usable_frame"):
            self.assertIn(reason, source, f"workflow should handle {reason}")


if __name__ == "__main__":
    unittest.main()
