"""Offline recovery checks: disposable keys/profiles only, no sensors or network."""
from dataclasses import replace
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from brain import notes
from security import vault
from security.approval import ApprovalGate
from security.policy import Session
from storage import recovery, store


class RecoveryChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lya-recovery-test-")
        self.addCleanup(self.tmp.cleanup)
        self.key_patch = patch.object(vault, "_F", Fernet(Fernet.generate_key()))
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)
        self.source = Path(self.tmp.name) / "source.enc"
        self.dest = Path(self.tmp.name) / "destination.enc"
        self.now = 2000000000.0
        self.owner = store.create_person("Fake owner", "admin", db_path=self.source)
        self.other = store.create_person("Fake other", "friend", db_path=self.source)
        self.target = store.create_person("New fake owner", "admin", db_path=self.dest)
        self.current = self.session(self.owner)
        self.key = recovery.new_recovery_key()
        self.a = notes.save(self.owner, "Private example", "Synthetic value A", "permanent",
                            kind="private", db_path=self.source, now=self.now)["id"]
        self.b = notes.save(self.owner, "Timed example", "Synthetic value B", "until",
                            until=self.now + 100, db_path=self.source, now=self.now)["id"]
        with store.store_connection(self.source) as db:
            db.execute("UPDATE memories SET revision=3 WHERE id=?", (self.a,))
            db.execute("INSERT INTO memory_links(src,dst,relation) VALUES (?,?,'supports')", (self.a, self.b))

    def session(self, pid):
        return Session("admin", "Fixture", "session-" + pid, pid, self.now + 3600)

    def options(self, path):
        return dict(get_session=lambda: self.current, db_path=path, clock=lambda: self.now,
                    approve=ApprovalGate(lambda c: c, wall_clock=lambda: self.now))

    def export(self, ids=None, **changes):
        return recovery.export_notes(ids if ids is not None else [self.a, self.b], self.key,
                                     **(self.options(self.source) | changes))

    def restore(self, blob, **changes):
        self.current = self.session(self.target)
        return recovery.restore_notes(blob, self.key, **(self.options(self.dest) | changes))

    def test_portable_restore_with_new_local_key_and_remapped_links(self):
        before = self.source.read_bytes()
        blob = self.export()
        self.assertEqual(before, self.source.read_bytes())
        self.assertNotIn(b"Synthetic", blob)
        data = json.loads(Fernet(self.key).decrypt(blob[len(recovery.MAGIC):]))
        self.assertEqual(set(data), {"format", "created_at", "notes", "links"})
        self.assertNotIn(self.owner, json.dumps(data))
        vault._F = Fernet(Fernet.generate_key())
        self.dest = Path(self.tmp.name) / "fresh-key.enc"
        self.target = store.create_person("Restored fake owner", "admin", db_path=self.dest)
        notes.save(self.target, "Discarded fixture", "Advance ID sequence", db_path=self.dest, now=self.now)
        with store.store_connection(self.dest) as db:
            db.execute("DELETE FROM memories")
        self.assertEqual(self.restore(blob), {"restored": 2, "expired_skipped": 0})
        self.assertIn("Synthetic value A", [r["value"] for r in notes.retrieve(
            self.target, "Synthetic value A", db_path=self.dest, now=self.now)])
        with store.store_connection(self.dest, read_only=True) as db:
            rows = db.execute("SELECT kind,value_enc,revision,expires_at,person_id FROM memories ORDER BY id").fetchall()
            self.assertEqual(vault.decrypt_text(rows[0][1]), "Synthetic value A")
            self.assertEqual((rows[0][0], rows[0][2]), ("private", 3))
            self.assertEqual(rows[1][3], self.now + 100)
            self.assertTrue(all(r[4] == self.target for r in rows))
            self.assertEqual(db.execute("SELECT count(*) FROM memory_links").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT src,dst FROM memory_links").fetchone(), (2, 3))
            self.assertEqual(db.execute("SELECT count(*) FROM face_templates").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM admin_recovery").fetchone()[0], 0)

    def test_wrong_key_and_tampering_leave_destination_unchanged(self):
        blob = self.export()
        before = self.dest.read_bytes()
        self.current = self.session(self.target)
        with self.assertRaises(ValueError):
            recovery.restore_notes(blob, recovery.new_recovery_key(), **self.options(self.dest))
        damaged = blob[:-10] + bytes([blob[-10] ^ 1]) + blob[-9:]
        with self.assertRaises(ValueError):
            self.restore(damaged)
        self.assertEqual(before, self.dest.read_bytes())

    def test_authenticated_but_invalid_schema_rejected(self):
        data = json.loads(Fernet(self.key).decrypt(self.export()[len(recovery.MAGIC):]))
        before = self.dest.read_bytes()
        invalid = []
        for change in (lambda d: d.update(format="unknown"),
                       lambda d: d["notes"][0].update(kind="credential"),
                       lambda d: d["notes"][0].update(role="admin"),
                       lambda d: d["notes"].append(d["notes"][0]),
                       lambda d: d.update(links=[[self.a, "exec", self.b]]),
                       lambda d: d["notes"][1].update(expires_at=float("nan"))):
            candidate = json.loads(json.dumps(data))
            change(candidate)
            invalid.append(recovery.MAGIC + Fernet(self.key).encrypt(json.dumps(candidate).encode()))
        for blob in invalid:
            with self.subTest(blob_size=len(blob)), self.assertRaises(ValueError):
                self.restore(blob)
        self.assertEqual(before, self.dest.read_bytes())

    def test_expiry_is_preserved_not_restarted(self):
        blob = self.export()
        self.now += 101
        with self.assertRaises(PermissionError):
            self.export()
        self.assertEqual(self.restore(blob), {"restored": 1, "expired_skipped": 1})
        with store.store_connection(self.dest, read_only=True) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM memory_links").fetchone()[0], 0)

    def test_cross_person_and_protected_selection_denied(self):
        foreign = notes.save(self.other, "Other", "Other synthetic note", db_path=self.source,
                             now=self.now)["id"]
        with self.assertRaises(PermissionError):
            self.export([self.a, foreign])
        with store.store_connection(self.source) as db:
            db.execute("UPDATE memories SET kind='credential' WHERE id=?", (self.a,))
        with self.assertRaises(PermissionError):
            self.export([self.a])

    def test_restore_never_overwrites_existing_notes(self):
        blob = self.export()
        notes.save(self.target, "Keep", "Existing", db_path=self.dest, now=self.now)
        before = self.dest.read_bytes()
        with self.assertRaises(PermissionError):
            self.restore(blob)
        self.assertEqual(before, self.dest.read_bytes())

    def test_default_denial_and_nonliteral_approval(self):
        for approval in (None, lambda *a: (False, "no"), lambda *a: 1):
            with self.subTest(approval=type(approval)), self.assertRaises(PermissionError):
                self.export(approve=approval)
        self.current = replace(self.current, role="friend")
        with self.assertRaises(PermissionError):
            self.export()

    def test_session_switch_and_profile_revocation_during_approval(self):
        def switch(*args):
            self.current = self.session(self.other)
            return True
        with self.assertRaises(PermissionError):
            self.export(approve=switch)
        self.current = self.session(self.owner)
        def revoke(*args):
            with store.store_connection(self.source) as db:
                db.execute("UPDATE people SET active=0 WHERE person_id=?", (self.owner,))
            return True
        with self.assertRaises(PermissionError):
            self.export(approve=revoke)

    def test_cancelled_restore_rolls_back(self):
        blob = self.export()
        before = self.dest.read_bytes()
        calls = iter([False, True])
        with self.assertRaises(PermissionError):
            self.restore(blob, cancelled=lambda: next(calls))
        self.assertEqual(before, self.dest.read_bytes())

    def test_mid_restore_encryption_failure_rolls_back(self):
        blob = self.export()
        before = self.dest.read_bytes()
        encrypt = vault.encrypt_text
        calls = 0
        def failing_encrypt(value):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("simulated encryption failure")
            return encrypt(value)
        with patch.object(vault, "encrypt_text", side_effect=failing_encrypt), self.assertRaises(OSError):
            self.restore(blob)
        self.assertEqual(before, self.dest.read_bytes())

    def test_atomic_replace_failure_keeps_original_and_cleans_temp(self):
        blob = self.export()
        before = self.dest.read_bytes()
        with patch.object(store.os, "replace", side_effect=OSError("simulated disk failure")), self.assertRaises(OSError):
            self.restore(blob)
        self.assertEqual(before, self.dest.read_bytes())
        self.assertEqual(list(Path(self.tmp.name).glob("*.tmp.*")), [])

    def test_read_only_transactions_cannot_write(self):
        before = self.source.read_bytes()
        with self.assertRaises(sqlite3.OperationalError):
            with store.store_connection(self.source, read_only=True) as db:
                db.execute("DELETE FROM memories")
        self.assertEqual(before, self.source.read_bytes())


if __name__ == "__main__":
    unittest.main()
