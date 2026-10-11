"""Fake identities, fake content and disposable SQLite databases only."""
from dataclasses import replace
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from brain import memory_prototype as memory
import test_conversation_contract as contract_fixtures


class MemoryChecks(unittest.TestCase):
    def setUp(self):
        fixture = contract_fixtures.ContractChecks(methodName='runTest')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        fixture.fresh_phone_owner()
        self.f = fixture
        temp = tempfile.TemporaryDirectory(prefix='lya-synthetic-memory-')
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'fake.sqlite'
        self.now = fixture.now
        self.m = memory.SyntheticMemory(self.path, synthetic_only=True, clock=lambda: self.now)
        self.owner = self.m.create_owner(fixture.binding)
        self.serial = 0

    def rid(self):
        self.serial += 1
        return f'{self.serial:032x}'

    def save_packet(self, key='fake preference', value='SYNTHETIC_VALUE', project='alpha', retention=None):
        return dict(op='save', project=project, request_id=self.rid(), kind='preference', key=key,
                    value={'text': value}, retention=retention or {'mode': 'permanent'})

    def call(self, packet, *, phone=False, turn=None, approved=True):
        return self.m.handle(turn or (self.f.phone_turn() if phone else self.f.laptop()), packet, approved=approved)

    def get(self, mid, project='alpha', **kwargs):
        return self.call(dict(op='get', project=project, id=mid), **kwargs)['record']

    def search(self, query, project='alpha', **kwargs):
        return self.call(dict(op='search', project=project, query=query), **kwargs)['records']

    def counts(self):
        with self.m._db() as db:
            return {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                    for name in ('memories', 'memory_search', 'outbox', 'requests', 'deletions')}

    def test_laptop_save_phone_recall_restart_and_source_scope(self):
        packet = self.save_packet()
        receipt = self.call(packet)
        self.m = memory.SyntheticMemory(self.path, synthetic_only=True, clock=lambda: self.now)
        row = self.get(receipt['id'], phone=True)
        self.assertEqual((row['owner'], row['project'], row['revision']), (self.owner, 'alpha', 1))
        self.assertEqual(row['value'], packet['value'])
        self.assertEqual(row['source_request'], packet['request_id'])
        self.assertEqual(row['approval_state'], 'owner_confirmed')
        self.assertEqual(self.search('SYNTHETIC_VALUE', phone=True)[0]['id'], receipt['id'])
        self.assertEqual(self.counts(), dict(memories=1, memory_search=1, outbox=1, requests=1, deletions=0))

    def test_correction_preserves_id_retention_changes_revision_and_search(self):
        first = self.call(self.save_packet(retention={'mode': 'short'}))
        before = self.get(first['id'])
        self.now += 10
        packet = dict(op='correct', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=1, value={'text': 'SYNTHETIC_CORRECTED'})
        result = self.call(packet, phone=True)
        row = self.get(first['id'])
        self.assertEqual(result['revision'], 2)
        self.assertEqual(row['expires_at'], before['expires_at'])
        self.assertEqual(row['recorded_at'], before['recorded_at'])
        self.assertEqual(row['updated_at'], self.now)
        self.assertEqual(row['source_request'], packet['request_id'])
        self.assertEqual(self.search('SYNTHETIC_VALUE'), [])
        self.assertEqual(self.search('SYNTHETIC_CORRECTED')[0]['revision'], 2)
        with self.assertRaises(memory.Conflict):self.call(dict(packet, request_id=self.rid()))
        with self.assertRaises(memory.Conflict):self.call(self.save_packet(key='FAKE PREFERENCE'))

    def test_retries_survive_restart_and_request_id_cannot_change_meaning(self):
        packet = self.save_packet()
        expected = self.call(packet)
        self.m = memory.SyntheticMemory(self.path, synthetic_only=True, clock=lambda: self.now)
        self.assertEqual(self.call(packet, phone=True), expected)
        with self.assertRaises(memory.Conflict):self.call(dict(packet, value={'text': 'different'}))
        with self.assertRaises(memory.Conflict):self.call(dict(packet, project='beta'))
        self.assertEqual(self.counts()['requests'], 1)

    def test_forget_erases_current_projection_and_retry_cannot_resurrect(self):
        save = self.save_packet()
        first = self.call(save)
        forget = dict(op='forget', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=1)
        receipt = self.call(forget, phone=True)
        self.assertEqual(self.call(forget), receipt)
        self.assertIsNone(self.get(first['id']))
        self.assertEqual(self.search('SYNTHETIC_VALUE'), [])
        self.assertEqual(self.call(save), first)
        self.assertIsNone(self.get(first['id']))
        with self.m._db() as db:
            row = db.execute('SELECT * FROM memories').fetchone()
            self.assertEqual((row['key'], row['value'], row['revision'], row['deleted']), ('', None, 2, 1))
            self.assertEqual(db.execute('SELECT reason FROM deletions').fetchone()[0], 'forget')
            receipts = str([tuple(r) for r in db.execute('SELECT * FROM requests')])
            self.assertNotIn('SYNTHETIC_VALUE', receipts)
        with self.assertRaises(memory.Conflict):
            self.call(dict(op='correct', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=2, value={'text': 'revive'}))

    def test_retention_boundary_expiry_cleanup_and_new_save_has_new_id(self):
        expired_ids = []
        for mode, seconds in (('short', 7 * 86400), ('long', 90 * 86400), ('until', 23)):
            retention = {'mode': mode, **({'expires_at': self.now + seconds} if mode == 'until' else {})}
            packet = self.save_packet(key=mode, retention=retention)
            receipt = self.call(packet)
            expired_ids.append(receipt['id'])
            self.assertEqual(self.get(receipt['id'])['expires_at'], self.now + seconds)
            with self.m._db() as db:job = db.execute('SELECT max(id) FROM outbox').fetchone()[0]
            self.now += seconds
            self.assertFalse(self.m.finish_job(job))
            self.assertIsNone(self.get(receipt['id']))
            self.assertEqual(self.call(packet), receipt)
            self.assertIsNone(self.get(receipt['id']))
        again = self.call(self.save_packet(key='short'))
        self.assertNotIn(again['id'], expired_ids)
        self.assertEqual(self.get(again['id'])['expires_at'], None)
        self.assertEqual(self.counts()['deletions'], 3)

    def test_owner_project_isolation_and_untrusted_scope_rejection(self):
        first = self.call(self.save_packet())
        self.assertIsNone(self.get(first['id'], project='beta'))
        self.assertEqual(self.search('SYNTHETIC_VALUE', project='beta'), [])
        other = self.m.create_owner('b' * 64)
        turn = self.f.laptop()
        context = replace(turn.context, principal='b' * 64)
        other_turn = replace(turn, context=context, _resolve=lambda: context)
        self.assertIsNone(self.get(first['id'], turn=other_turn))
        self.assertEqual(self.search('SYNTHETIC_VALUE', turn=other_turn), [])
        own_second = self.call(self.save_packet(), turn=other_turn)
        self.assertEqual(self.get(own_second['id'], turn=other_turn)['owner'], other)
        with self.assertRaises(memory.Conflict):
            self.call(dict(op='forget', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=1), turn=other_turn)
        with self.assertRaises(ValueError):self.call(dict(self.save_packet(), owner=self.owner))

    def test_rotation_keeps_stable_owner_and_records_but_revokes_old_binding(self):
        first = self.call(self.save_packet())
        with self.assertRaises(PermissionError):self.m.rotate_binding(self.f.binding, 'b' * 64)
        self.assertEqual(self.m.rotate_binding(self.f.binding, 'b' * 64, approved=True), self.owner)
        with self.assertRaises(PermissionError):self.get(first['id'])
        with self.assertRaises(PermissionError):self.m.create_owner(self.f.binding)
        turn = self.f.laptop()
        context = replace(turn.context, principal='b' * 64)
        new_turn = replace(turn, context=context, _resolve=lambda: context)
        self.assertEqual(self.get(first['id'], turn=new_turn)['owner'], self.owner)
        self.assertEqual(self.m.create_owner('b' * 64), self.owner)
        with self.assertRaises(memory.Conflict):self.m.rotate_binding('b' * 64, self.f.binding, approved=True)

    def test_each_operation_needs_fresh_auth_and_literal_trusted_approval(self):
        packet = self.save_packet()
        for approval in (False, 1, 'yes', None):
            with self.assertRaises(PermissionError):self.call(packet, approved=approval)
        with self.phone_unverified():
            with self.assertRaises(PermissionError):self.call(packet, phone=True)
        turn = self.f.laptop()
        self.f.brain.bind_session(replace(self.f.owner, verified_until=0))
        with self.assertRaises(PermissionError):self.call(packet, turn=turn)
        self.assertEqual(self.counts()['memories'], 0)

    def phone_unverified(self):
        return patch.dict(self.f.phone.app.session(self.f.token), {'owner_until': 0})

    def test_schema_limits_and_invalid_retention_never_create_records(self):
        packet = self.save_packet()
        bad = [dict(packet, approved=True), dict(packet, kind='credentials'), dict(packet, project='../escape'),
               dict(packet, key=''), dict(packet, value={'text': 'x' * 4096}), dict(packet, value={'text': float('nan')}),
               dict(packet, value={'text': {'nested': 'not yet supported'}}), dict(packet, retention={'mode': 'automatic'}),
               dict(packet, retention={'mode': 'until', 'expires_at': True}), dict(packet, retention={'mode': 'until', 'expires_at': self.now}),
               dict(packet, retention={'mode': 'permanent', 'expires_at': self.now + 50})]
        for request in bad:
            with self.subTest(request=request):
                with self.assertRaises(ValueError):self.call(request)
        self.assertEqual(self.counts()['memories'], 0)

    def test_unicode_literal_fts_query_and_bounded_results(self):
        for key, value in (('தமிழ்', 'தமிழில் பேசலாம்'), ('Tanglish', 'Tamil la sollu'), ('café', 'warm coffee')):
            row = self.call(self.save_packet(key=key, value=value))
            query = 'தமிழில்' if key == 'தமிழ்' else 'Tamil' if key == 'Tanglish' else 'café'
            self.assertEqual(self.search(query)[0]['id'], row['id'])
        with self.assertRaises(memory.Conflict):self.call(self.save_packet(key='cafe\u0301'))
        self.assertEqual(self.search('" OR * OR "'), [])
        self.assertEqual(self.search('no-match-fixture'), [])
        for i in range(8):self.call(self.save_packet(key=f'bounded {i}', value='common'))
        self.assertEqual(len(self.search('common')), 6)

    def test_outbox_stale_jobs_cannot_acknowledge_newer_or_deleted_values(self):
        first = self.call(self.save_packet())
        with self.m._db() as db:old_job = db.execute('SELECT id FROM outbox').fetchone()[0]
        self.call(dict(op='correct', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=1, value={'text': 'new'}))
        self.assertFalse(self.m.finish_job(old_job))
        with self.m._db() as db:new_job = db.execute('SELECT max(id) FROM outbox').fetchone()[0]
        self.assertTrue(self.m.finish_job(new_job))
        self.assertTrue(self.m.finish_job(new_job))
        self.call(dict(op='forget', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=2))
        self.assertFalse(self.m.finish_job(new_job))
        with self.m._db() as db:delete_job = db.execute('SELECT max(id) FROM outbox').fetchone()[0]
        self.assertTrue(self.m.finish_job(delete_job))

    def test_statement_failure_and_cancel_before_commit_roll_back_every_projection(self):
        with self.m._db() as db:
            db.execute("CREATE TRIGGER fake_failure BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        before = self.counts()
        packet = self.save_packet()
        with self.assertRaises(sqlite3.IntegrityError):self.call(packet)
        self.assertEqual(self.counts(), before)
        with self.m._db() as db:db.execute('DROP TRIGGER fake_failure')
        turn = self.f.laptop()
        enqueue = self.m._enqueue
        def cancel(*args):
            enqueue(*args)
            turn._cancelled.set()
        with patch.object(self.m, '_enqueue', side_effect=cancel):
            with self.assertRaises(InterruptedError):self.call(packet, turn=turn)
        self.assertEqual(self.counts(), before)
        self.assertTrue(self.call(packet)['committed'])

    def test_concurrent_device_corrections_have_one_winner(self):
        first = self.call(self.save_packet())
        barrier = threading.Barrier(2)
        outcomes = []
        def run(turn, packet):
            barrier.wait(3)
            try:outcomes.append(self.m.handle(turn, packet, approved=True))
            except memory.Conflict:outcomes.append('conflict')
        threads = []
        for turn, text in ((self.f.laptop(), 'fake laptop correction'), (self.f.phone_turn(), 'fake phone correction')):
            packet = dict(op='correct', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=1, value={'text': text})
            threads.append(threading.Thread(target=run, args=(turn, packet)))
        for thread in threads:thread.start()
        for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(outcomes.count('conflict'), 1)
        self.assertEqual(self.get(first['id'])['revision'], 2)

    def test_actual_sqlite_full_is_atomic_and_logical_budgets_fail_closed(self):
        with self.m._db() as db:pages = db.execute('PRAGMA page_count').fetchone()[0]
        failed = False
        with patch.object(memory, 'MAX_PAGES', pages):
            for i in range(20):
                before = self.counts()
                try:self.call(self.save_packet(key=f'full-{i}', value='0123456789abcdef' * 240))
                except sqlite3.OperationalError as exc:
                    self.assertEqual(exc.sqlite_errorcode, sqlite3.SQLITE_FULL)
                    self.assertEqual(self.counts(), before)
                    failed = True
                    break
        self.assertTrue(failed)
        with patch.object(memory, 'MAX_RECORDS', 0):
            with self.assertRaises(ValueError):self.call(self.save_packet())
        with patch.object(memory, 'MAX_REQUESTS', 0):
            with self.assertRaises(ValueError):self.call(self.save_packet())

    def test_wrong_database_and_missing_storage_never_acknowledge(self):
        with self.assertRaises(PermissionError):memory.SyntheticMemory(self.path)
        wrong = self.path.with_name('unrelated.sqlite')
        db = sqlite3.connect(wrong);db.execute('CREATE TABLE unrelated(value TEXT)');db.commit();db.close()
        before = wrong.read_bytes()
        with self.assertRaises(ValueError):memory.SyntheticMemory(wrong, synthetic_only=True)
        self.assertEqual(wrong.read_bytes(), before)
        with self.assertRaises(sqlite3.OperationalError):memory.SyntheticMemory(self.path.parent/'absent'/'fake.sqlite', synthetic_only=True)

    def test_process_death_before_commit_rolls_back_and_lost_reply_retries_once(self):
        import json
        program = '''
from contextlib import contextmanager
import os, sys, threading, time
from brain.conversation import Context, PublicTurn
from brain.memory_prototype import SyntheticMemory
path, binding, mode = sys.argv[1:]
context = Context(binding, 'laptop', 'a'*64, binding, 4102444800., True)
turn = PublicTurn('f'*32, 'SYNTHETIC_PUBLIC_QUESTION', context, time.monotonic()+30,
                  lambda: context, lambda: 2000000000., threading.Event())
m = SyntheticMemory(path, synthetic_only=True, clock=lambda: 2000000000.)
if mode == 'before':
    original = m._db
    @contextmanager
    def die_before_commit(*args, **kwargs):
        with original(*args, **kwargs) as db:
            yield db
            os._exit(17)
    m._db = die_before_commit
packet = dict(op='save', project='alpha', request_id=('d' if mode=='before' else 'e')*32,
              kind='fact', key='crash fixture', value={'text':'SYNTHETIC_CRASH_VALUE'}, retention={'mode':'permanent'})
m.handle(turn, packet, approved=True)
os._exit(18)
'''
        before = self.counts()
        for mode, code in (('before', 17), ('after', 18)):
            run = subprocess.run([sys.executable, '-c', program, str(self.path), self.f.binding, mode],
                                 cwd=Path(__file__).resolve().parent, capture_output=True, text=True, timeout=15,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.assertEqual(run.returncode, code, run.stderr)
            if mode == 'before':self.assertEqual(self.counts(), before)
        packet = dict(op='save', project='alpha', request_id='e'*32, kind='fact', key='crash fixture',
                      value={'text':'SYNTHETIC_CRASH_VALUE'}, retention={'mode':'permanent'})
        first = self.call(packet)
        self.assertEqual(self.call(packet, phone=True), first)
        self.assertEqual(self.counts()['memories'], 1)
        self.assertEqual(self.counts()['requests'], 1)
        self.assertNotIn('SYNTHETIC_CRASH_VALUE', json.dumps(first))

    def test_forget_remains_available_at_ordinary_request_budget(self):
        first = self.call(self.save_packet())
        with patch.object(memory, 'MAX_REQUESTS', 0):
            result = self.call(dict(op='forget', project='alpha', request_id=self.rid(), id=first['id'], expected_revision=1))
        self.assertTrue(result['committed'])
        self.assertIsNone(self.get(first['id']))

    def test_composite_foreign_keys_reject_cross_scope_jobs_and_deletions(self):
        first = self.call(self.save_packet())
        with self.assertRaises(sqlite3.IntegrityError):
            with self.m._db() as db:
                db.execute('INSERT INTO outbox(owner,project,memory_id,revision,operation) VALUES(?,?,?,?,?)',
                           (self.owner, 'other-project', first['id'], 1, 'upsert'))
        with self.assertRaises(sqlite3.IntegrityError):
            with self.m._db() as db:
                db.execute('INSERT INTO deletions VALUES(?,?,?,?,?,?)',
                           ('b'*32, 'alpha', first['id'], 1, self.now, 'fake'))
        self.assertEqual(self.counts()['outbox'], 1)
        self.assertEqual(self.counts()['deletions'], 0)

    def test_revocation_during_transaction_rolls_back_and_denies_retry_receipt(self):
        turn = self.f.phone_turn()
        enqueue = self.m._enqueue
        def revoke(*args):
            enqueue(*args)
            self.f.phone.store.control('revoke', self.f.binding, self.f.now)
        packet = self.save_packet()
        before = self.counts()
        with patch.object(self.m, '_enqueue', side_effect=revoke):
            with self.assertRaises(PermissionError):self.call(packet, turn=turn)
        self.assertEqual(self.counts(), before)
        receipt = self.call(packet)
        with self.assertRaises(PermissionError):self.call(packet, turn=turn)
        self.assertEqual(self.get(receipt['id'])['revision'], 1)


if __name__ == '__main__':
    unittest.main()
