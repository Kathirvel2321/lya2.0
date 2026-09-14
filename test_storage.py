"""test_storage.py — Unit tests for LYA's person-scoped encrypted storage engine.

Run with: .venv-ui/Scripts/python.exe test_storage.py
Tests run in an isolated temporary directory with zero real biometric/secret data.
"""

import concurrent.futures
import datetime
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from storage.store import (
    ensure_layout,
    create_person,
    get_person,
    list_people,
    remember,
    recall,
    forget,
    record_pending_face,
    list_pending_faces,
    promote_pending_face,
    record_audit,
    list_audit_events,
)


class TestStorageEngine(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp_dir.name).resolve() / "LYA"
        os.environ["LYA_DATA_DIR"] = str(self.data_dir)
        self.db_path = self.data_dir / "lya.db.enc"

    def tearDown(self):
        os.environ.pop("LYA_DATA_DIR", None)
        self.tmp_dir.cleanup()

    def test_ensure_layout_creates_directories(self):
        dirs = ensure_layout(self.data_dir)
        self.assertTrue(dirs["faces"].is_dir())
        self.assertTrue(dirs["vault"].is_dir())
        self.assertTrue(dirs["models"].is_dir())
        self.assertTrue(dirs["logs"].is_dir())
        self.assertEqual(dirs["db"], self.db_path)

    def test_database_is_encrypted_at_rest(self):
        # Create a person to commit DB to disk
        p_id = create_person("Alice", "admin", db_path=self.db_path)
        remember(p_id, "secret_key", "highly_sensitive_fact", db_path=self.db_path)

        self.assertTrue(self.db_path.exists())
        raw_bytes = self.db_path.read_bytes()
        self.assertNotIn(b"highly_sensitive_fact", raw_bytes)
        self.assertNotIn(b"Alice", raw_bytes)

        # Plain SQLite must fail to parse the encrypted file
        conn = sqlite3.connect(str(self.db_path))
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("SELECT name FROM sqlite_master")
        finally:
            conn.close()

    def test_person_isolation_and_scoping(self):
        alice_id = create_person("Alice", "admin", db_path=self.db_path)
        bob_id = create_person("Bob", "friend", db_path=self.db_path)

        remember(alice_id, "color", "Alice loves blue", db_path=self.db_path)
        remember(bob_id, "color", "Bob loves green", db_path=self.db_path)

        # Alice's recall must only contain Alice's fact
        alice_facts = recall(alice_id, db_path=self.db_path)
        self.assertEqual(len(alice_facts), 1)
        self.assertEqual(alice_facts[0]["value"], "Alice loves blue")

        # Bob's recall must only contain Bob's fact
        bob_facts = recall(bob_id, db_path=self.db_path)
        self.assertEqual(len(bob_facts), 1)
        self.assertEqual(bob_facts[0]["value"], "Bob loves green")

        # Guest (empty person_id) cannot see anything
        guest_facts = recall("", db_path=self.db_path)
        self.assertEqual(guest_facts, [])

        # Cannot write to invalid/missing person ID
        with self.assertRaises(PermissionError):
            remember("nonexistent_id", "test", "data", db_path=self.db_path)

    def test_forget_only_deletes_specified_person_memory(self):
        alice_id = create_person("Alice", "admin", db_path=self.db_path)
        bob_id = create_person("Bob", "friend", db_path=self.db_path)

        remember(alice_id, "food", "Alice pizza", db_path=self.db_path)
        remember(bob_id, "food", "Bob pizza", db_path=self.db_path)

        deleted = forget(alice_id, "food", db_path=self.db_path)
        self.assertEqual(deleted, 1)

        # Alice's memory is gone
        self.assertEqual(recall(alice_id, db_path=self.db_path), [])
        # Bob's memory remains intact
        self.assertEqual(len(recall(bob_id, db_path=self.db_path)), 1)

    def test_pending_faces_and_promotion(self):
        # Record unknown visitor observation
        pending_id = record_pending_face("shots/thumb1.jpg", embedding_bytes=b"fake_512_bytes", db_path=self.db_path)
        pending_list = list_pending_faces(db_path=self.db_path)
        self.assertEqual(len(pending_list), 1)
        self.assertEqual(pending_list[0]["pending_id"], pending_id)

        # Promote unknown visitor to recognized friend
        friend_id = promote_pending_face(pending_id, "Charlie", "friend", db_path=self.db_path)
        self.assertTrue(friend_id.startswith("p_"))

        # Pending queue must now be empty
        self.assertEqual(list_pending_faces(db_path=self.db_path), [])

        # Charlie must exist in people list
        charlie = get_person(friend_id, db_path=self.db_path)
        self.assertIsNotNone(charlie)
        self.assertEqual(charlie["display_name"], "Charlie")
        self.assertEqual(charlie["role"], "friend")

    def test_audit_log_never_records_secrets(self):
        alice_id = create_person("Alice", "admin", db_path=self.db_path)
        remember(alice_id, "password", "my_super_secret_123", db_path=self.db_path)

        events = list_audit_events(limit=10, db_path=self.db_path)
        self.assertGreaterEqual(len(events), 1)
        for ev in events:
            self.assertNotIn("my_super_secret_123", ev["action_type"])
            self.assertNotIn("my_super_secret_123", ev["outcome"])

    def test_parallel_writes_thread_safety(self):
        p_id = create_person("Dave", "friend", db_path=self.db_path)

        def write_fact(idx):
            remember(p_id, f"key_{idx}", f"value_{idx}", db_path=self.db_path)
            return idx

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(write_fact, i) for i in range(12)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 12)
        saved = recall(p_id, limit=50, db_path=self.db_path)
        self.assertEqual(len(saved), 12)

    def test_face_template_crud(self):
        from storage import add_face_template, list_face_templates, remove_face_templates
        p_id = create_person("Dave", role="friend", db_path=self.db_path)
        dummy_emb = [0.1 * i for i in range(10)]
        tid = add_face_template(p_id, dummy_emb, model_version="arcface-512d", db_path=self.db_path)
        self.assertGreater(tid, 0)

        templates = list_face_templates(person_id=p_id, db_path=self.db_path)
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0]["display_name"], "Dave")
        self.assertEqual(templates[0]["embedding"], dummy_emb)

        # Remove templates
        count = remove_face_templates(p_id, db_path=self.db_path)
        self.assertEqual(count, 1)
        self.assertEqual(len(list_face_templates(person_id=p_id, db_path=self.db_path)), 0)


if __name__ == "__main__":
    unittest.main()
