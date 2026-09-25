"""Sensor-free checks for the legacy security-phrase gate."""
import unittest
from unittest.mock import patch

import numpy as np

from security import auth_wall


class SecurityPhraseTests(unittest.TestCase):
    def test_unconfigured_transcriber_fails_closed_without_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network used")):
            with self.assertRaisesRegex(RuntimeError, "Local security-phrase"):
                auth_wall.keyword_match(b"fake audio", "blue comet")

    def test_local_phrase_match_does_not_return_transcript(self):
        transcriber = lambda audio, fmt: "Please say BLUE, comet now"
        self.assertEqual(auth_wall.keyword_match(b"fake", "blue comet", local_transcriber=transcriber),
                         (True, ""))
        self.assertEqual(auth_wall.keyword_match(b"fake", "blue come", local_transcriber=transcriber),
                         (False, ""))

    def test_wall_report_does_not_repeat_spoken_phrase(self):
        wall = object.__new__(auth_wall.AuthWall)
        wall.store_face = wall.store_voice = b"fake encrypted template"
        wall.local_transcriber = lambda audio, fmt: "blue comet"
        vector = np.array([1.0, 0.0], dtype=np.float32)
        with patch.object(auth_wall, "face_embedding", return_value=vector), \
             patch.object(auth_wall, "voice_embedding", return_value=vector), \
             patch.object(auth_wall.vault, "decrypt", return_value=vector.tobytes()):
            ok, report = wall.verify(b"fake image", b"fake audio", "blue comet")
        self.assertTrue(ok)
        self.assertIn("keyword PASS", report)
        self.assertNotIn("blue comet", report)

    def test_wall_denies_without_local_transcriber(self):
        wall = object.__new__(auth_wall.AuthWall)
        wall.store_face = wall.store_voice = b"fake encrypted template"
        wall.local_transcriber = None
        vector = np.array([1.0, 0.0], dtype=np.float32)
        with patch.object(auth_wall, "face_embedding", return_value=vector), \
             patch.object(auth_wall, "voice_embedding", return_value=vector), \
             patch.object(auth_wall.vault, "decrypt", return_value=vector.tobytes()):
            ok, report = wall.verify(b"fake image", b"fake audio", "blue comet")
        self.assertFalse(ok)
        self.assertNotIn("blue comet", report)


if __name__ == "__main__":
    unittest.main()
