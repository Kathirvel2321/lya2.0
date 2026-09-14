"""Isolated brain acceptance checks. No real keys, stores, sensors or network."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from security import vault
# Lazy vault import reads nothing; inject a disposable key before any operation.
vault._F = Fernet(Fernet.generate_key())
from storage import store
from brain import notes, mind
from brain.workflow import Brain, LocalModel, ModelUnavailable
from security.policy import Session


class BrainChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lya-brain-test-")
        self.db = Path(self.tmp.name).resolve() / "test.enc"
        self.now = 2000000000.0
        self.alice = store.create_person("Fake Alice", "admin", db_path=self.db)
        self.bob = store.create_person("Fake Bob", "admin", db_path=self.db)
        self.calls = []
        self.brain = Brain(self.session(self.alice), approve=lambda *a: True,
                           client=self.client, db_path=self.db, clock=lambda: self.now)

    def tearDown(self):
        self.tmp.cleanup()

    def session(self, person):
        return Session("admin", "Fixture", person, person, self.now + 3600)

    def client(self, messages):
        self.calls.append(messages)
        return "Mock recommendation, not a fact."

    def test_ranked_search_avoids_substrings_and_fts_operators(self):
        notes.save(self.alice, 'art', 'painting', db_path=self.db, now=self.now)
        notes.save(self.alice, 'cart', 'shopping', db_path=self.db, now=self.now)
        found = notes.retrieve(self.alice, 'art', db_path=self.db, now=self.now)
        self.assertEqual([r['key'] for r in found], ['art'])
        self.assertEqual(notes.retrieve(self.alice, '" OR * NEAR(', db_path=self.db, now=self.now), [])
        self.assertEqual(notes.retrieve(self.alice, 'art', db_path=self.db, now=self.now, limit=0), [])

    def test_full_ranked_results_keep_linked_contradiction(self):
        ids = [notes.save(self.alice, 'camera '+str(i), 'camera room', db_path=self.db, now=self.now)['id'] for i in range(7)]
        conflict = notes.save(self.alice, 'exception', 'do not infer occupancy from a still image', db_path=self.db, now=self.now)
        notes.link(self.alice, ids[-1], 'contradicts', conflict['id'], db_path=self.db, now=self.now)
        found = notes.retrieve(self.alice, 'camera', db_path=self.db, now=self.now)
        self.assertEqual(len(found), 6)
        self.assertIn(conflict['id'], [r['id'] for r in found])

    def test_correction_rebuilds_search_without_stale_terms(self):
        notes.save(self.alice, 'choice', 'azure', db_path=self.db, now=self.now)
        notes.save(self.alice, 'choice', 'oracle', correct=True, db_path=self.db, now=self.now)
        self.assertFalse(notes.retrieve(self.alice, 'azure', db_path=self.db, now=self.now))
        self.assertEqual(notes.retrieve(self.alice, 'oracle', db_path=self.db, now=self.now)[0]['revision'], 2)

    def test_guest_and_denied_approval_cannot_touch_private_memory(self):
        guest = Brain(db_path=self.db, client=self.client, clock=lambda: self.now)
        with patch.object(store, 'get_person', side_effect=AssertionError('Guest queried registry')):
            self.assertEqual(guest.respond('show memories').route, 'blocked')
        self.brain.approve = lambda *a: False
        self.assertEqual(self.brain.respond('remember short x = y').route, 'blocked')
        self.assertEqual(store.recall(self.alice, db_path=self.db), [])

    def test_router_receives_task_and_private_context_classification(self):
        seen = []
        class Client:
            def invoke(self, messages, **policy):
                seen.append(policy)
                return 'Fixture response'
        self.brain.client = Client()
        self.assertEqual(self.brain.respond('debug this code').route, 'model')
        self.assertEqual(seen[-1], {'task': 'coding', 'sensitivity': 'private'})
        guest = Brain(client=Client(), db_path=self.db, clock=lambda: self.now)
        guest.respond('research this topic')
        self.assertEqual(seen[-1], {'task': 'research', 'sensitivity': 'public'})

    def test_scoped_retrieval_credentials_and_model_not_auto_saved(self):
        self.brain.respond('remember permanent laptop = low resource machine')
        store.remember(self.alice, 'auth', 'FAKE_HASH', kind='credential', db_path=self.db)
        notes.save(self.bob, 'laptop', 'BOB_ONLY', db_path=self.db, now=self.now)
        answer = self.brain.respond('Plan work for my laptop')
        self.assertEqual(answer.route, 'model')
        prompt = str(self.calls[-1])
        self.assertIn('low resource machine', prompt)
        self.assertNotIn('BOB_ONLY', prompt)
        self.assertNotIn('FAKE_HASH', prompt)
        self.assertEqual(len(store.recall(self.alice, context_only=True, db_path=self.db)), 1)

    def test_short_long_deadline_and_permanent_expiry(self):
        for mode in ('short', 'long', 'permanent'):
            notes.save(self.alice, mode, 'fixture', mode, db_path=self.db, now=self.now)
        notes.save(self.alice, 'deadline', 'fixture', 'until', until=self.now+10, db_path=self.db, now=self.now)
        future = self.now + 8*86400
        rows = store.recall(self.alice, db_path=self.db, now=future)
        self.assertEqual({r['key'] for r in rows}, {'long', 'permanent'})
        self.assertEqual(notes.expire(self.alice, db_path=self.db, now=future), 2)
        rows = store.recall(self.alice, db_path=self.db, now=self.now+91*86400)
        self.assertEqual([r['key'] for r in rows], ['permanent'])

    def test_timezone_and_nonfinite_deadlines_rejected(self):
        self.assertEqual(self.brain.respond('remember until 2040-01-01 x = y').route, 'blocked')
        with self.assertRaises(ValueError):
            notes.save(self.alice, 'x', 'y', 'until', until=float('nan'), db_path=self.db)

    def test_correction_preserves_expiry_and_graph_forget_cascades(self):
        a = notes.save(self.alice, 'laptop', 'old', db_path=self.db, now=self.now)
        b = notes.save(self.alice, 'project', 'LYA', db_path=self.db, now=self.now)
        notes.link(self.alice, b['id'], 'depends_on', a['id'], db_path=self.db, now=self.now)
        self.assertEqual(self.brain.respond('correct laptop = new').route, 'local')
        row = next(r for r in store.recall(self.alice, db_path=self.db, now=self.now) if r['id']==a['id'])
        self.assertEqual((row['value'], row['revision'], row['expires_at']), ('new', 2, a['expires_at']))
        self.brain.respond('forget laptop')
        self.assertEqual(notes.graph(self.alice, db_path=self.db, now=self.now), [])

    def test_graph_rejects_other_owner_and_expired_endpoints(self):
        a = notes.save(self.alice, 'x', 'y', db_path=self.db, now=self.now)
        b = notes.save(self.bob, 'z', 'w', db_path=self.db, now=self.now)
        with self.assertRaises(PermissionError):
            notes.link(self.alice, a['id'], 'supports', b['id'], db_path=self.db, now=self.now)
        self.assertEqual(notes.graph(self.alice, db_path=self.db), [])

    def test_session_notes_clear_on_identity_change_sleep_and_idle(self):
        self.brain.respond('remember session task = example')
        self.assertTrue(self.brain.session_notes)
        self.brain.bind_session(self.session(self.bob))
        self.assertFalse(self.brain.session_notes)
        self.brain.respond('remember session task = example')
        self.brain.respond('sleep')
        self.assertFalse(self.brain.session_notes)
        self.brain.respond('remember session task = example')
        self.now += 901
        self.brain.respond('brain status')
        self.assertFalse(self.brain.session_notes)

    def test_identity_switch_and_cancellation_discard_answer(self):
        def switch(messages):
            self.brain.bind_session(self.session(self.bob))
            return 'DO NOT DISPLAY'
        self.brain.client = switch
        self.assertEqual(self.brain.respond('hello').route, 'cancelled')
        event = threading.Event()
        event.set()
        self.assertEqual(self.brain.respond('remember short bad = value', event).route, 'cancelled')

    def test_note_expiry_during_inference_hides_stale_answer(self):
        notes.save(self.alice, 'laptop', 'temporary', 'until', until=self.now+1, now=self.now, db_path=self.db)
        def slow(messages):
            self.now += 2
            return 'STALE ANSWER'
        self.brain.client = slow
        answer = self.brain.respond('laptop advice')
        self.assertEqual(answer.route, 'blocked')
        self.assertNotIn('STALE ANSWER', answer.text)

    def test_council_uses_four_calls_without_executing_or_saving(self):
        answer = self.brain.respond('council: important plan for my laptop')
        self.assertEqual(answer.route, 'council')
        self.assertEqual(len(self.calls), 4)
        self.assertIn('Agreement is not proof', answer.text)
        self.assertEqual(store.recall(self.alice, db_path=self.db), [])

    def test_council_failure_does_not_invent_verdict(self):
        self.brain.client = LocalModel('')
        answer = self.brain.respond('council: choose a plan')
        self.assertEqual(answer.route, 'blocked')
        self.assertIn('No council perspective', answer.text)

    def test_legacy_memory_fallback_closed(self):
        store.remember(self.alice, 'auth', 'FAKE_CREDENTIAL', kind='credential', db_path=self.db)
        self.assertNotIn('FAKE_CREDENTIAL', mind._memory_block(self.alice, self.db))
        with patch.object(store, 'list_people', side_effect=AssertionError('guessed identity')):
            self.assertIn('identity required', mind._memory_block(db_path=self.db))
        with patch.object(store, 'recall', side_effect=RuntimeError('failure')):
            with patch.object(mind.memory, 'recall', side_effect=AssertionError('legacy fallback')):
                self.assertIn('storage error', mind._memory_block(self.alice, self.db))

    def test_expired_pending_cannot_be_promoted(self):
        face = store.record_pending_face(embedding=[1, 0], expires_days=-1, db_path=self.db)
        with self.assertRaises(KeyError):
            store.promote_pending_face(face, 'Expired fixture', db_path=self.db)

    def test_encrypted_file_and_restart_recall(self):
        self.brain.respond('remember permanent project = SYNTHETIC_PRIVATE_NOTE')
        self.assertNotIn(b'SYNTHETIC_PRIVATE_NOTE', self.db.read_bytes())
        fresh = Brain(self.session(self.alice), approve=lambda *a: True, db_path=self.db, clock=lambda: self.now)
        self.assertIn('SYNTHETIC_PRIVATE_NOTE', fresh.respond('recall project').text)

    def test_revocation_during_inference_hides_answer(self):
        def revoke(messages):
            with store.store_connection(self.db) as db:
                db.execute('UPDATE people SET active=0 WHERE person_id=?', (self.alice,))
            return 'REVOKED RESULT'
        self.brain.client = revoke
        answer = self.brain.respond('hello')
        self.assertEqual(answer.route, 'blocked')
        self.assertNotIn('REVOKED RESULT', answer.text)

    def test_old_encrypted_schema_migrates_without_losing_note(self):
        import sqlite3
        legacy = self.db.with_name('legacy.enc')
        db = sqlite3.connect(':memory:')
        db.executescript('''CREATE TABLE people(person_id TEXT PRIMARY KEY,display_name TEXT,role TEXT,created_at TEXT,active INTEGER);
            CREATE TABLE memories(id INTEGER PRIMARY KEY,person_id TEXT,kind TEXT,key_enc TEXT,value_enc TEXT,source TEXT,importance REAL,hits INTEGER,created_at TEXT,updated_at TEXT);''')
        db.execute("INSERT INTO people VALUES (?,'Fixture','admin','2026-01-01',1)", (self.alice,))
        db.execute("INSERT INTO memories VALUES (1,?,'fact',?,?,'user',1,0,'2026-01-01','2026-01-01')",
                   (self.alice, vault.encrypt_text('legacy label'), vault.encrypt_text('keep this')))
        db.commit()
        legacy.write_bytes(vault.encrypt(db.serialize()))
        db.close()
        rows = store.recall(self.alice, db_path=legacy)
        self.assertEqual((rows[0]['value'], rows[0]['retention'], rows[0]['expires_at']), ('keep this', 'permanent', None))


if __name__ == '__main__':
    unittest.main(verbosity=2)
