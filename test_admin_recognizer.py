"""Tests for tiered admin recognition - fake data only, no camera, no model."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain import admin_recognizer as R


ADMIN_HIT = {"status": "admin", "name": "admin", "role": "admin",
             "similarity": 0.9, "person_id": "p_fake", "verified": False,
             "session": None}

UNKNOWN = {"status": "unknown", "name": None, "role": None,
           "similarity": 0.1, "person_id": None, "verified": False,
           "session": None}


class _FakeVi:
    """Stands in for the vision.identity module inside recognize_me."""
    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.calls = []

    def identify(self, sample, admin_threshold=0.45, db_path=None):
        self.calls.append(sample)
        return self.verdicts.pop(0) if self.verdicts else dict(UNKNOWN)


class SessionTests(unittest.TestCase):
    def test_mint_and_validate(self):
        sid = R.mint_session()
        self.assertTrue(R.session_valid(sid))
        R.end_session(sid)
        self.assertFalse(R.session_valid(sid))

    def test_expiry(self):
        sid = R.mint_session(now=0)
        self.assertFalse(R.session_valid(sid, now=R.SESSION_TTL + 1))


class ClassifyTests(unittest.TestCase):
    def test_simple_is_tier1(self):
        for text in ("what time is it", "tell me a joke", "open my iphone interface",
                     "remember my birthday is 12 march"):
            self.assertEqual(R.classify_request(text), "tier1")

    def test_sensitive_is_tier2(self):
        for text in ("show me my password", "open the vault",
                     "delete my saved memory", "payment status",
                     "what is my api key"):
            self.assertEqual(R.classify_request(text), "tier2")


class AuthorizeTests(unittest.TestCase):
    def setUp(self):
        self.hit = dict(ADMIN_HIT, verified=True, session="sid1")

    def test_tier1_face_alone_suffices(self):
        ok, why, tier = R.authorize("what time is it", self.hit)
        self.assertTrue(ok)
        self.assertEqual(tier, "tier1")

    def test_tier2_needs_word(self):
        ok, why, _ = R.authorize("show my password", self.hit)   # no word checker
        self.assertFalse(ok)
        self.assertEqual(why, "word_required")
        ok, why, _ = R.authorize("show my password", self.hit,
                                 spoken_word_check=lambda: True)
        self.assertTrue(ok)
        ok, why, _ = R.authorize("show my password", self.hit,
                                 spoken_word_check=lambda: False)
        self.assertFalse(ok)

    def test_no_face_never_authorizes(self):
        miss = dict(UNKNOWN, verified=False, session=None)
        ok, why, _ = R.authorize("what time is it", miss)
        self.assertFalse(ok)
        self.assertEqual(why, "face")


class WorkflowIntentTests2(unittest.TestCase):
    def test_its_me_matches_capability(self):
        from brain import capabilities
        import re
        for text in ("its me", "it's me", "it is me", "lya its me",
                     "hey lya its me", "i am back"):
            # Mirror the wake-word stripping the workflow applies before the
            # Capability matcher, since the matcher anchors at the start.
            normalized = re.sub(r'^(?:hey )?(?:lya|laya|leya)\s+', '', text.casefold())
            self.assertTrue(capabilities.matches("its_me", normalized),
                            f"{text!r} should match its_me after wake-word strip")

    def test_welcome_back_does_not_match_intent(self):
        from brain import capabilities
        self.assertFalse(capabilities.matches("its_me", "welcome back boss"))


class RecognitionTests(unittest.TestCase):
    def _run_recognize(self, verdicts_out, frames_in=(b"\xff\xd8fake",)):
        import unittest.mock as mock
        fake = _FakeVi(verdicts_out)
        with mock.patch("vision.identity", create=True) as fake_vi, \
                mock.patch("brain.admin_recognizer.capture_frames", return_value=list(frames_in)):
            fake_vi.identify.side_effect = fake.identify
            result = R.its_me()
        return result, fake

    def test_admin_hit_mints_session(self):
        result, _ = self._run_recognize([dict(ADMIN_HIT)], [b"\xff\xd8f"] * 3)
        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "admin")
        self.assertIsNotNone(result["session"])
        self.assertTrue(R.session_valid(result["session"]))
        R.end_session(result["session"])

    def test_unknown_gets_no_session(self):
        result, _ = self._run_recognize([dict(UNKNOWN)], [b"\xff\xd8f"] * 3)
        self.assertFalse(result["verified"])
        self.assertIsNone(result["session"])

    def test_camera_unavailable(self):
        import unittest.mock as mock
        with mock.patch("brain.admin_recognizer.capture_frames", return_value=[]):
            result = R.its_me()
        self.assertEqual(result["status"], "camera_unavailable")
        self.assertFalse(result["verified"])

    def test_frame_is_jpeg_encoded_before_matching(self):
        # Regression: a raw BGR frame used to be treated as a precomputed
        # embedding vector (shape (480,640,3) vs (128,)). The frame must be
        # JPEG-encoded so the real ArcFace pipeline runs. The frame passes
        # the quick_check pre-screen first, then gets encoded.
        import unittest.mock as mock
        import numpy as np
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[200:320, 240:400] = 160          # bright enough, sharp enough
        seen = {}

        def fake_identify(sample, admin_threshold=0.45, db_path=None):
            seen["sample"] = sample
            return dict(UNKNOWN)

        def fake_analyze(f):
            return {"usable": True, "reason": "ok"}

        with mock.patch("vision.identity", create=True) as fake_vi, \
                mock.patch("vision.quick_check.analyze", side_effect=fake_analyze):
            fake_vi.identify.side_effect = fake_identify
            R.recognize_me([frame])
        sample = seen.get("sample")
        self.assertIsInstance(sample, (bytes, bytearray))
        self.assertEqual(sample[:2], b"\xff\xd8")   # JPEG magic bytes


if __name__ == "__main__":
    unittest.main()
