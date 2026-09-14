"""Comprehensive unit test suite for LYA face recognition & identity engine.

Checks:
1. Cosine similarity mathematical invariants (_cos).
2. Multi-user enrollment & identification (Admin, Friend, Unknown).
3. Stranger/visitor pending face capture (7-day TTL) and Admin promotion.
4. Owner verification with anti-spoofing policy gate.
5. Secondary user PBKDF2 salted password authentication.
6. Identity forgetting and template cleanup.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np

from vision import identity
from storage import store


class FaceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "lya_test.db.enc"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_cosine_similarity_invariants(self):
        v1 = np.zeros(512, dtype=np.float32)
        v1[0] = 1.0

        v2 = np.zeros(512, dtype=np.float32)
        v2[0] = 1.0

        v3 = np.zeros(512, dtype=np.float32)
        v3[1] = 1.0  # Orthogonal to v1

        v4 = -v1     # Opposite

        # Invariants
        self.assertAlmostEqual(identity._cos(v1, v2), 1.0, places=5)
        self.assertAlmostEqual(identity._cos(v1, v3), 0.0, places=5)
        self.assertAlmostEqual(identity._cos(v1, v4), -1.0, places=5)
        self.assertEqual(identity._cos(np.zeros(512), v1), 0.0)

    def test_multi_user_enrollment_and_identification(self):
        # 1. Generate synthetic 512-d unit embeddings
        rng = np.random.default_rng(42)
        raw_alice = rng.standard_normal(512).astype(np.float32)
        emb_alice = raw_alice / np.linalg.norm(raw_alice)

        raw_bob = rng.standard_normal(512).astype(np.float32)
        emb_bob = raw_bob / np.linalg.norm(raw_bob)

        raw_charlie = rng.standard_normal(512).astype(np.float32)
        emb_charlie = raw_charlie / np.linalg.norm(raw_charlie)

        # 2. Enroll Alice (admin) and Bob (friend)
        self.assertTrue(identity.enroll_person("Alice", identity.ADMIN, [emb_alice], db_path=self.db_path))
        self.assertTrue(identity.enroll_person("Bob", identity.FRIEND, [emb_bob], db_path=self.db_path))

        # 3. Identify Alice
        res_alice = identity.identify(emb_alice, db_path=self.db_path)
        self.assertEqual(res_alice["status"], identity.ADMIN)
        self.assertEqual(res_alice["who"], "Alice")
        self.assertGreater(res_alice["similarity"], 0.95)

        # 4. Identify Bob
        res_bob = identity.identify(emb_bob, db_path=self.db_path)
        self.assertEqual(res_bob["status"], identity.FRIEND)
        self.assertEqual(res_bob["who"], "Bob")
        self.assertGreater(res_bob["similarity"], 0.95)

        # 5. Identify Unknown (Charlie)
        res_charlie = identity.identify(emb_charlie, db_path=self.db_path)
        self.assertEqual(res_charlie["status"], identity.UNKNOWN)
        self.assertIsNone(res_charlie["who"])

        # 6. Verify stranger was captured in pending faces
        pending = identity.list_pending(db_path=self.db_path)
        self.assertEqual(len(pending), 1)
        pending_id = pending[0]["id"]

        # 7. Admin names the stranger -> Charlie becomes known friend
        self.assertTrue(identity.name_person(pending_id, "Charlie", role=identity.FRIEND, db_path=self.db_path))
        res_charlie_promoted = identity.identify(emb_charlie, db_path=self.db_path)
        self.assertEqual(res_charlie_promoted["status"], identity.FRIEND)
        self.assertEqual(res_charlie_promoted["who"], "Charlie")

    def test_owner_verification_and_spoof_gate(self):
        rng = np.random.default_rng(101)
        raw_alice = rng.standard_normal(512).astype(np.float32)
        emb_alice = raw_alice / np.linalg.norm(raw_alice)

        raw_bob = rng.standard_normal(512).astype(np.float32)
        emb_bob = raw_bob / np.linalg.norm(raw_bob)

        # Enroll Alice as admin
        identity.enroll_person("Alice", identity.ADMIN, [emb_alice], db_path=self.db_path)

        # Owner match succeeds with Alice's template
        ok, msg = identity.verify_owner(emb_alice, threshold=0.60, db_path=self.db_path)
        self.assertTrue(ok)
        self.assertIn("Owner matched", msg)

        # Bob (friend or imposter) fails owner verification
        ok, msg = identity.verify_owner(emb_bob, threshold=0.60, db_path=self.db_path)
        self.assertFalse(ok)
        self.assertIn("Owner not recognized", msg)

        # Synthetic flat image buffer fails liveness check immediately
        import cv2
        flat_img = np.full((160, 160, 3), 128, dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", flat_img)
        ok, msg = identity.verify_owner(buf.tobytes(), threshold=0.60, db_path=self.db_path)
        self.assertFalse(ok)
        self.assertIn("liveness", msg.lower())

    def test_secondary_password_authentication(self):
        # Set password for secondary user "David"
        self.assertTrue(identity.set_secondary_password("David", "CorrectHorseBatteryStaple", db_path=self.db_path))

        # Check correct password
        self.assertTrue(identity.check_secondary_password("David", "CorrectHorseBatteryStaple", db_path=self.db_path))

        # Check wrong password
        self.assertFalse(identity.check_secondary_password("David", "WrongPassword", db_path=self.db_path))

        # Check non-existent user
        self.assertFalse(identity.check_secondary_password("Mallory", "AnyPassword", db_path=self.db_path))

    def test_forget_person(self):
        rng = np.random.default_rng(77)
        raw_bob = rng.standard_normal(512).astype(np.float32)
        emb_bob = raw_bob / np.linalg.norm(raw_bob)

        identity.enroll_person("Bob", identity.FRIEND, [emb_bob], db_path=self.db_path)
        res1 = identity.identify(emb_bob, db_path=self.db_path)
        self.assertEqual(res1["who"], "Bob")

        # Forget Bob
        self.assertTrue(identity.forget("Bob", db_path=self.db_path))

        # Bob should now be recognized only as unknown
        res2 = identity.identify(emb_bob, db_path=self.db_path)
        self.assertEqual(res2["status"], identity.UNKNOWN)
        self.assertIsNone(res2["who"])


if __name__ == "__main__":
    unittest.main()
