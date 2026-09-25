"""Encrypted search-index migration and mutation checks with disposable data."""
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from brain import notes
from security import vault
from storage import store


class SearchIndexChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lya-index-test-")
        self.addCleanup(self.temp.cleanup)
        key = patch.object(vault, "_F", Fernet(Fernet.generate_key()))
        key.start()
        self.addCleanup(key.stop)
        self.db = Path(self.temp.name) / "fake.enc"
        self.now = 2_000_000_000.0
        self.owner = store.create_person("Fake owner", "admin", db_path=self.db)
        self.other = store.create_person("Fake friend", "friend", db_path=self.db)

    def test_legacy_backfill_stays_encrypted_at_rest(self):
        notes.save(self.owner, "legacy", "synthetic needle", "permanent",
                   db_path=self.db, now=self.now)
        with store.store_connection(self.db) as db:
            for trigger in ("note_search_insert", "note_search_delete", "note_search_update"):
                db.execute(f"DROP TRIGGER {trigger}")
            db.execute("DROP TABLE note_search")
        before_read = self.db.read_bytes()
        self.assertEqual([row["key"] for row in notes.retrieve(
            self.owner, "needle", db_path=self.db, now=self.now)], ["legacy"])
        self.assertEqual(before_read, self.db.read_bytes())
        self.assertNotIn(b"synthetic needle", self.db.read_bytes())
        notes.save(self.owner, "new", "second target", db_path=self.db, now=self.now)
        raw = sqlite3.connect(":memory:")
        try:
            raw.deserialize(vault.decrypt(self.db.read_bytes()))
            self.assertIsNone(raw.execute("SELECT 1 FROM sqlite_master WHERE name='note_search'").fetchone())
        finally:
            raw.close()
        with patch.dict(os.environ, {"LYA_ENABLE_SEARCH_MIGRATION": "1"}):
            notes.save(self.owner, "opted in", "third target", db_path=self.db, now=self.now)
        raw = sqlite3.connect(":memory:")
        try:
            raw.deserialize(vault.decrypt(self.db.read_bytes()))
            self.assertIsNotNone(raw.execute("SELECT 1 FROM sqlite_master WHERE name='note_search'").fetchone())
        finally:
            raw.close()
        self.assertEqual([row["key"] for row in notes.retrieve(
            self.owner, "second", db_path=self.db, now=self.now)], ["new"])

    def test_correction_forget_expiry_and_person_scope(self):
        notes.save(self.owner, "fixture", "oldneedle", db_path=self.db, now=self.now)
        notes.save(self.other, "fixture", "friendneedle", db_path=self.db, now=self.now)
        self.assertEqual(notes.retrieve(self.owner, "friendneedle", db_path=self.db, now=self.now), [])
        notes.save(self.owner, "fixture", "newneedle", db_path=self.db, now=self.now, correct=True)
        self.assertEqual(notes.retrieve(self.owner, "oldneedle", db_path=self.db, now=self.now), [])
        self.assertEqual([row["value"] for row in notes.retrieve(
            self.owner, "newneedle", db_path=self.db, now=self.now)], ["newneedle"])
        notes.save(self.owner, "timed", "expiringneedle", "until", until=self.now + 1,
                   db_path=self.db, now=self.now)
        self.assertEqual(notes.retrieve(self.owner, "expiringneedle", db_path=self.db,
                                        now=self.now + 2), [])
        notes.expire(self.owner, db_path=self.db, now=self.now + 2)
        self.assertEqual(notes.retrieve(self.owner, "expiringneedle", db_path=self.db,
                                        now=self.now), [])
        store.forget(self.owner, "fixture", db_path=self.db)
        self.assertEqual(notes.retrieve(self.owner, "newneedle", db_path=self.db, now=self.now), [])
        self.assertEqual([row["value"] for row in notes.retrieve(
            self.other, "friendneedle", db_path=self.db, now=self.now)], ["friendneedle"])

    def test_protected_record_never_enters_search(self):
        store.remember(self.owner, "credential", "fake-secret-needle", kind="credential",
                       db_path=self.db)
        self.assertEqual(notes.retrieve(self.owner, "fake-secret-needle",
                                        db_path=self.db, now=self.now), [])
        with store.store_connection(self.db, read_only=True) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM note_search").fetchone()[0], 0)
        note_id = notes.save(self.owner, "former note", "second-secret-needle",
                             db_path=self.db, now=self.now)["id"]
        with store.store_connection(self.db) as db:
            db.execute("UPDATE memories SET kind='credential' WHERE id=?", (note_id,))
        self.assertEqual(notes.retrieve(self.owner, "second-secret-needle",
                                        db_path=self.db, now=self.now), [])


if __name__ == "__main__":
    unittest.main()
