"""Project memory acceptance using fake keys, temporary stores and fake approval."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from brain import notes
from brain.workflow import Brain
from security import vault
from security.approval import ApprovalGate
from security.policy import Session
from storage import recovery, store


class ProjectMemoryChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="lya-project-memory-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        cipher = patch.object(vault, "_F", Fernet(Fernet.generate_key()))
        cipher.start()
        self.addCleanup(cipher.stop)
        self.db = self.root / "source.enc"
        self.now = 2_000_000_000.0
        self.owner = store.create_person("Synthetic owner", "admin", db_path=self.db)
        self.other = store.create_person("Synthetic other", "admin", db_path=self.db)
        self.current = self.session(self.owner)
        self.challenges = []
        gate = ApprovalGate(lambda c: self.challenges.append(c) or c, wall_clock=lambda: self.now)
        self.brain = Brain(self.current, approve=gate, client=lambda m: "public fixture",
                           local_client=lambda m: "private fixture", db_path=self.db, clock=lambda: self.now)

    def session(self, person):
        return Session("admin", "Fixture", "session-" + person, person, self.now + 3600)

    def save(self, label, value, project="", **options):
        return notes.save(self.owner, label, value, project_id=project,
                          db_path=self.db, now=self.now, **options)

    def retrieve(self, project="", query="", **options):
        return notes.retrieve(self.owner, query, project_id=project,
                              db_path=self.db, now=self.now, **options)

    def test_same_label_is_separated_before_search_and_graph(self):
        self.save("framework", "globalcanary")
        a = self.save("framework", "alphacanary", "alpha")["id"]
        b = self.save("framework", "betacanary", "beta")["id"]
        notes.save(self.other, "framework", "othercanary", project_id="alpha", db_path=self.db, now=self.now)
        self.assertEqual([r["value"] for r in self.retrieve()], ["globalcanary"])
        self.assertEqual([r["value"] for r in self.retrieve("alpha", "framework")], ["alphacanary"])
        for needle in ("betacanary", "globalcanary", "othercanary", '" OR * NEAR('):
            self.assertEqual(self.retrieve("alpha", needle), [])
        with self.assertRaises(PermissionError):
            notes.link(self.owner, a, "supports", b, project_id="alpha", db_path=self.db, now=self.now)
        # A corrupt legacy edge must not make a foreign-project body a candidate.
        with store.store_connection(self.db) as db:
            db.execute("INSERT INTO memory_links VALUES (?,?,'supports')", (a, b))
        self.assertEqual([r["value"] for r in self.retrieve("alpha", "framework")], ["alphacanary"])
        self.assertEqual(notes.graph(self.owner, project_id="alpha", db_path=self.db, now=self.now), [])
        self.assertEqual([r["value"] for r in store.recall(self.owner, db_path=self.db)], ["globalcanary"])

    def test_correction_forget_expiry_and_budget_stay_scoped(self):
        self.save("choice", "global")
        self.save("choice", "oldalpha", "alpha", retention="until", until=self.now + 5)
        self.save("choice", "beta", "beta")
        self.save("choice", "newalpha", "alpha", correct=True)
        self.assertEqual(self.retrieve("alpha", "oldalpha"), [])
        row = self.retrieve("alpha")[0]
        self.assertEqual((row["revision"], row["expires_at"]), (2, self.now + 5))
        self.assertEqual(notes.retrieve(self.owner, project_id="alpha", db_path=self.db, now=self.now + 6), [])
        self.assertEqual(store.forget(self.owner, "choice", db_path=self.db, project_id="alpha"), 1)
        self.assertEqual([r["value"] for r in self.retrieve("beta")], ["beta"])
        with patch.object(notes, "MAX_NOTES", 2), self.assertRaises(ValueError):
            self.save("extra", "newproject cannot bypass owner budget", "gamma")

    def test_native_commands_bind_approval_to_project_and_preserve_defaults(self):
        for command in ("remember permanent framework = global",
                        "project ALPHA: remember long framework = AlphaOnly",
                        "project beta: remember permanent framework = BetaOnly"):
            self.assertEqual(self.brain.respond(command).route, "local")
            self.assertEqual(self.challenges[-1].parameters, command)
        answer = self.brain.respond("project alpha: recall framework")
        self.assertEqual(answer.route, "recall")
        self.assertIn("AlphaOnly", answer.text)
        self.assertNotIn("BetaOnly", answer.text)
        self.assertNotIn("AlphaOnly", self.brain.respond("show memories").text)
        self.brain.respond("project alpha: correct framework = AlphaChanged")
        self.assertEqual(self.retrieve("alpha")[0]["revision"], 2)
        self.brain.respond("project alpha: forget framework")
        self.assertEqual(self.retrieve("alpha"), [])
        self.assertEqual(self.retrieve("beta")[0]["value"], "BetaOnly")
        cloud = []
        self.brain.client = lambda m: cloud.append(m) or "fixture"
        self.brain.respond("Explain the weather")
        self.assertNotIn("BetaOnly", json.dumps(cloud))

    def test_no_guest_or_nonliteral_approval_access_and_invalid_prefix_no_model(self):
        before = self.db.read_bytes()
        self.brain.approve = lambda *args: 1
        self.assertEqual(self.brain.respond("project alpha: remember short note = value").route, "blocked")
        self.brain.bind_session(Session(id="guest"))
        self.assertEqual(self.brain.respond("project alpha: recall note").route, "blocked")
        self.assertEqual(self.db.read_bytes(), before)
        self.brain.bind_session(self.session(self.owner))
        self.brain.client = lambda m: self.fail("Invalid project command reached model")
        for command in ("project ../alpha: recall x", "project alpha: open camera",
                        "project alpha: remember session x = y"):
            self.assertEqual(self.brain.respond(command).route, "blocked")
        for project in (None, True, "../alpha", "alpha:beta", "x" * 65):
            with self.assertRaises(ValueError):
                self.save("label", "value", project)

    def test_project_links_need_both_endpoints_in_the_same_scope(self):
        a = self.save("design", "api", "alpha")["id"]
        b = self.save("check", "api tests", "alpha")["id"]
        self.assertEqual(self.brain.respond(f"project alpha: link {a} supports {b}").route, "local")
        self.assertEqual(notes.graph(self.owner, project_id="alpha", db_path=self.db, now=self.now),
                         [("design", "supports", "check")])
        self.assertIn("supports", self.brain.respond("project alpha: show graph").text)
        self.assertNotIn("supports", self.brain.respond("show graph").text)

    def test_backup_restore_preserves_project_scopes_and_new_key(self):
        ids = [self.save("framework", "global")["id"],
               self.save("framework", "AlphaOnly", "alpha")["id"],
               self.save("framework", "BetaOnly", "beta")["id"]]
        key = recovery.new_recovery_key()
        options = dict(get_session=lambda: self.current, db_path=self.db,
                       approve=ApprovalGate(lambda c: c, wall_clock=lambda: self.now), clock=lambda: self.now)
        blob = recovery.export_notes(ids, key, **options)
        data = recovery._decode(blob, key)
        self.assertEqual(data["format"], "lya-selected-notes/v2")
        self.assertEqual([r["project_id"] for r in data["notes"]], ["", "alpha", "beta"])
        self.assertNotIn(b"AlphaOnly", blob)
        labels = recovery.list_notes(**options)
        self.assertIn("[project:alpha] framework", [r["label"] for r in labels])
        # Simulate another protected installation with a different encryption key.
        vault._F = Fernet(Fernet.generate_key())
        dest = self.root / "restored.enc"
        target = store.create_person("Restored fixture", "admin", db_path=dest)
        self.current = self.session(target)
        options["db_path"] = dest
        self.assertEqual(recovery.restore_notes(blob, key, **options)["restored"], 3)
        for project, expected in (("", "global"), ("alpha", "AlphaOnly"), ("beta", "BetaOnly")):
            self.assertEqual(notes.retrieve(target, project_id=project, db_path=dest, now=self.now)[0]["value"], expected)
        self.assertEqual(recovery._decode(recovery.export_notes([1], key, **options), key)["format"], "lya-selected-notes/v1")

    def test_authenticated_invalid_project_archive_is_rejected(self):
        a = self.save("a", "alpha", "alpha")["id"]
        b = self.save("b", "beta", "beta")["id"]
        key = recovery.new_recovery_key()
        options = dict(get_session=lambda: self.current, db_path=self.db,
                       approve=ApprovalGate(lambda c: c, wall_clock=lambda: self.now), clock=lambda: self.now)
        data = recovery._decode(recovery.export_notes([a, b], key, **options), key)
        for change in (lambda d: d["notes"][0].update(project_id="../bad"),
                       lambda d: d["notes"][0].update(project_id=True),
                       lambda d: d.update(links=[[a, "supports", b]])):
            candidate = json.loads(json.dumps(data))
            change(candidate)
            bad = recovery.MAGIC + Fernet(key).encrypt(json.dumps(candidate).encode())
            with self.assertRaises(ValueError):
                recovery._decode(bad, key)

    def test_read_only_project_search_does_not_write_source(self):
        self.save("note", "AlphaOnly", "alpha")
        before = self.db.read_bytes()
        self.retrieve("alpha")
        self.assertEqual(self.db.read_bytes(), before)
        self.assertNotIn(b"AlphaOnly", before)

    def test_legacy_store_read_keeps_disk_and_old_memory_unchanged(self):
        self.save("existing", "legacycanary")
        db = sqlite3.connect(":memory:")
        try:
            db.deserialize(vault.decrypt(self.db.read_bytes()))
            db.execute("DROP INDEX memory_owner_project")
            db.execute("ALTER TABLE memories DROP COLUMN project_id")
            self.db.write_bytes(vault.encrypt(db.serialize()))
        finally:
            db.close()
        before = self.db.read_bytes()
        self.assertEqual(store.get_person(self.owner, db_path=self.db)["person_id"], self.owner)
        self.assertEqual(self.retrieve()[0]["value"], "legacycanary")
        self.assertEqual(self.db.read_bytes(), before)
        self.save("new", "AlphaOnly", "alpha")
        self.assertEqual(self.retrieve()[0]["value"], "legacycanary")
        self.assertEqual(self.retrieve("alpha")[0]["value"], "AlphaOnly")

    def test_revocation_or_session_change_during_project_approval_denies_write(self):
        def switch(challenge):
            self.brain.bind_session(self.session(self.other))
            return challenge
        self.brain.approve = ApprovalGate(switch, wall_clock=lambda: self.now)
        self.assertEqual(self.brain.respond("project alpha: remember short note = denied").route, "blocked")
        self.assertEqual(self.retrieve("alpha"), [])

        self.brain.bind_session(self.session(self.owner))
        def revoke(challenge):
            with store.store_connection(self.db) as db:
                db.execute("UPDATE people SET active=0 WHERE person_id=?", (self.owner,))
            return challenge
        self.brain.approve = ApprovalGate(revoke, wall_clock=lambda: self.now)
        self.assertEqual(self.brain.respond("project alpha: remember short note = denied").route, "blocked")
        self.assertEqual(self.retrieve("alpha"), [])

    def test_ordinary_project_question_keeps_the_existing_conversation_route(self):
        self.assertEqual(self.brain.respond("project ideas for a simple game").route, "private-local")


if __name__ == "__main__":
    unittest.main()
