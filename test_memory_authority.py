"""Fake signed identities, generated keys and temporary authority stores only."""
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from brain.memory_authority import SyntheticAuthority, WriterGrant
from brain.memory_prototype import Conflict, SyntheticMemory
from brain.memory_recovery import SyntheticRecovery
import test_memory_prototype as fixtures

try:from sqlcipher3 import dbapi2 as cipher
except ImportError:cipher = None


@unittest.skipIf(cipher is None,'Run the isolated authority qualification runner.')
class AuthorityChecks(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.MemoryChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.key = os.urandom(32);self.recovery_key = SyntheticRecovery.new_key()
        self.r = SyntheticRecovery(self.recovery_key,synthetic_only=True,clock=lambda:self.f.now)
        self.f.path = self.f.path.with_name('bootstrap.sqlite')
        self.f.m = SyntheticMemory(self.f.path,synthetic_only=True,encryption_key=self.key,clock=lambda:self.f.now)
        self.f.owner = self.f.m.create_owner(self.f.f.binding)
        self.seed = self.f.call(self.f.save_packet(key='seed',value='SYNTHETIC_SEED'))
        self.path = self.f.path.parent/'authority'
        self.a = self.open()
        self.anchor = self.a.register(self.f.m,approved=True)
        self.grant = self.a.acquire(self.anchor.lineage,'a'*32,expected_epoch=0,approved=True)

    def open(self, **kwargs):
        values = dict(recovery=self.r,storage_key=self.key,synthetic_only=True,clock=lambda:self.f.now)
        values.update(kwargs)
        return SyntheticAuthority(self.path,**values)

    def call(self, packet, *, grant=None, anchor=None, turn=None, **kwargs):
        result = self.a.handle(grant or self.grant,turn or self.f.f.laptop(),packet,
                               expected_anchor=anchor or self.anchor,approved=True,**kwargs)
        self.anchor = result['anchor']
        return result['result']

    def get(self, mid):
        return self.call(dict(op='get',project='alpha',id=mid))['record']

    def state(self):
        with self.a._repository._db() as db:
            return [dict(db.execute('SELECT * FROM '+table).fetchone()) for table in ('latest','writers')]

    def current_path(self):
        return self.path/'objects'/self.state()[0]['object_id']/'live.sqlite'

    def test_encrypted_authority_survives_source_loss_restart_and_keeps_source_unchanged(self):
        original = self.f.path.read_bytes()
        first = self.call(self.f.save_packet(value='SYNTHETIC_AUTHORITY_SAVE'))
        self.assertEqual(self.f.path.read_bytes(),original)
        self.f.path.unlink();self.a = self.open()
        self.assertEqual(self.get(first['id'])['value']['text'],'SYNTHETIC_AUTHORITY_SAVE')
        self.assertNotIn(b'SQLite format 3',self.current_path().read_bytes())
        catalog = self.a._repository.catalog.read_bytes()
        for secret in (self.key,self.recovery_key,self.grant.token,b'SYNTHETIC_AUTHORITY_SAVE'):
            self.assertNotIn(secret,catalog)
        self.assertNotIn(self.grant.token.hex(),repr(self.grant))

    def test_takeover_rejects_old_writer_even_with_latest_anchor(self):
        old = self.grant
        self.grant = self.a.acquire(self.anchor.lineage,'b'*32,expected_epoch=1,approved=True)
        before = self.state()
        for packet in (self.f.save_packet(),dict(op='get',project='alpha',id=self.seed['id'])):
            with self.assertRaises(PermissionError):self.call(packet,grant=old)
        self.assertEqual(self.state(),before)
        self.assertEqual(self.get(self.seed['id'])['id'],self.seed['id'])

    def test_forged_grants_and_cross_lineage_cannot_publish(self):
        before = self.state()
        for grant in (replace(self.grant,token=os.urandom(32)),replace(self.grant,epoch=2),
                      replace(self.grant,writer='c'*32),replace(self.grant,lineage='c'*32),
                      replace(self.grant,token=b'short'),object()):
            with self.assertRaises((ValueError,PermissionError)):self.call(self.f.save_packet(),grant=grant)
        with self.assertRaises(Conflict):self.call(self.f.save_packet(),anchor=replace(self.anchor,lineage='c'*32))
        self.assertEqual(self.state(),before)

    def test_approval_fresh_auth_and_owner_scope_still_required(self):
        before = self.state();packet = self.f.save_packet()
        for approval in (False,1,'yes',None):
            with self.assertRaises(PermissionError):
                self.a.handle(self.grant,self.f.f.laptop(),packet,expected_anchor=self.anchor,approved=approval)
        with self.f.phone_unverified():
            with self.assertRaises(PermissionError):self.call(packet,turn=self.f.f.phone_turn())
        turn = self.f.f.laptop();context = replace(turn.context,principal='b'*64)
        with self.assertRaises(PermissionError):self.call(packet,turn=replace(turn,context=context,_resolve=lambda:context))
        self.assertEqual(self.state(),before)

    def test_bootstrap_takeover_and_restore_controls_fail_closed(self):
        before = self.state();destination = self.f.path.with_name('unapproved.sqlite')
        for approval in (False,1,'yes',None):
            with self.assertRaises(PermissionError):self.a.register(self.f.m,approved=approval)
            with self.assertRaises(PermissionError):
                self.a.acquire(self.anchor.lineage,'b'*32,expected_epoch=1,approved=approval)
            with self.assertRaises(PermissionError):
                self.a.restore(self.anchor.lineage,destination,expected_anchor=self.anchor,approved=approval)
        self.assertFalse(destination.exists());self.assertEqual(self.state(),before)
        for values in (dict(synthetic_only=False),dict(storage_key=None),dict(storage_key=b'short')):
            with self.assertRaises((PermissionError,ValueError)):self.open(**values)
        plain = SyntheticMemory(self.f.path.with_name('plaintext.sqlite'),synthetic_only=True)
        with self.assertRaises(ValueError):self.a.register(plain,approved=True)
        self.assertEqual(self.state(),before)

    def test_stale_anchor_blocks_new_writes_but_lost_reply_retries_are_idempotent(self):
        old = self.anchor;packet = self.f.save_packet()
        first = self.call(packet);before = self.state()
        self.assertEqual(self.call(packet,anchor=old,turn=self.f.f.phone_turn()),first)
        self.assertEqual(self.state(),before)
        with self.assertRaises(Conflict):self.call(self.f.save_packet(key='new'),anchor=old)
        with self.assertRaises(Conflict):self.call(dict(packet,value={'text':'changed'}),anchor=old)
        self.assertEqual(self.state(),before)

    def test_two_concurrent_takeovers_have_one_winner(self):
        barrier = threading.Barrier(2);outcomes = []
        def acquire(writer):
            barrier.wait(3)
            try:outcomes.append(self.a.acquire(self.anchor.lineage,writer,expected_epoch=1,approved=True))
            except Conflict:outcomes.append('conflict')
        threads = [threading.Thread(target=acquire,args=(writer*32,)) for writer in ('b','c')]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
        self.assertEqual(sum(type(value) is WriterGrant for value in outcomes),1)
        self.assertEqual(outcomes.count('conflict'),1)
        self.assertEqual(self.a.head(self.anchor.lineage)['writer_epoch'],2)

    def test_two_new_writes_against_same_anchor_have_one_commit(self):
        barrier = threading.Barrier(2);outcomes = [];anchor = self.anchor
        packets = [self.f.save_packet(key='concurrent-'+str(i)) for i in range(2)]
        def save(packet,turn):
            barrier.wait(3)
            try:outcomes.append(self.a.handle(self.grant,turn,packet,expected_anchor=anchor,approved=True))
            except Conflict:outcomes.append('conflict')
        threads = [threading.Thread(target=save,args=(packet,turn)) for packet,turn in
                   zip(packets,(self.f.f.laptop(),self.f.f.phone_turn()))]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
        self.assertEqual(sum(type(value) is dict for value in outcomes),1)
        self.assertEqual(outcomes.count('conflict'),1)
        self.assertEqual(self.a.head(anchor.lineage)['anchor'].sequence,anchor.sequence+1)

    def test_takeover_serializes_with_inflight_publication(self):
        entered = threading.Event();release = threading.Event();attempted = threading.Event();done = threading.Event()
        results = [];original = self.a._publish;packet = self.f.save_packet()
        def held(*args):
            result = original(*args);entered.set()
            if not release.wait(2):raise RuntimeError('synthetic release timed out')
            return result
        def write():
            try:results.append(self.a.handle(self.grant,self.f.f.laptop(),packet,expected_anchor=self.anchor,approved=True))
            except Exception as error:results.append(error)
        def takeover():
            attempted.set()
            try:results.append(self.a.acquire(self.anchor.lineage,'b'*32,expected_epoch=1,approved=True))
            except Exception as error:results.append(error)
            finally:done.set()
        with patch.object(self.a,'_publish',side_effect=held):
            first = threading.Thread(target=write);first.start()
            self.assertTrue(entered.wait(3))
            second = threading.Thread(target=takeover);second.start()
            self.assertTrue(attempted.wait(1));self.assertFalse(done.wait(.05));release.set()
            first.join(5);second.join(5)
        self.assertFalse(first.is_alive());self.assertFalse(second.is_alive())
        self.assertCountEqual([type(value) for value in results],[dict,WriterGrant])
        self.anchor = next(value['anchor'] for value in results if type(value) is dict)
        with self.assertRaises(PermissionError):self.call(packet)

    def test_restore_latest_forget_state_is_quarantined_and_revokes_grants(self):
        old_anchor = self.anchor
        packet = dict(op='forget',project='alpha',request_id=self.f.rid(),id=self.seed['id'],expected_revision=1)
        first = self.call(packet)
        self.assertEqual(self.call(packet,anchor=old_anchor),first)
        self.assertIsNone(self.get(self.seed['id']))
        destination = self.f.path.with_name('restored.sqlite')
        result = self.a.restore(self.anchor.lineage,destination,expected_anchor=self.anchor,approved=True)
        self.assertEqual((result['result']['active_bindings'],result['result']['resumed_jobs']),(0,0))
        self.assertEqual(result['result']['suppressed_deleted'],1)
        restored = SyntheticMemory(destination,synthetic_only=True,encryption_key=self.key)
        with restored._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM deletions').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_search').fetchone()[0],0)
            self.assertIsNone(db.execute('SELECT value FROM memories WHERE id=?',(self.seed['id'],)).fetchone()[0])
        with self.assertRaises(PermissionError):self.get(self.seed['id'])
        self.assertFalse(self.a.head(self.anchor.lineage)['writer_active'])
        self.assertNotIn(b'SYNTHETIC_SEED',destination.read_bytes())

    def test_old_restore_anchor_refused_without_revoking_current_writer(self):
        old = self.anchor;self.call(self.f.save_packet())
        destination = self.f.path.with_name('old-restore.sqlite');before = self.state()
        with self.assertRaises(Conflict):
            self.a.restore(old.lineage,destination,expected_anchor=old,approved=True)
        self.assertFalse(destination.exists());self.assertEqual(self.state(),before)
        self.assertIsNotNone(self.get(self.seed['id']))

    def test_corrupt_live_file_blocks_writes_but_latest_bundle_can_restore(self):
        self.call(self.f.save_packet(value='SYNTHETIC_RECOVERABLE'))
        self.current_path().write_bytes(b'SYNTHETIC_DAMAGED_SOURCE')
        with self.assertRaises(ValueError):self.call(self.f.save_packet())
        destination = self.f.path.with_name('recover-missing-live.sqlite')
        result = self.a.restore(self.anchor.lineage,destination,expected_anchor=self.anchor,approved=True)
        self.assertEqual(result['result']['preserved'],2)
        with self.assertRaises(PermissionError):self.call(self.f.save_packet())

    def test_old_device_copy_cannot_reset_or_overwrite_authority(self):
        self.call(self.f.save_packet(key='canonical',value='SYNTHETIC_CANONICAL'))
        self.f.call(self.f.save_packet(key='offline-one'));self.f.call(self.f.save_packet(key='offline-two'))
        before = self.state()
        with self.assertRaises(Conflict):self.a.register(self.f.m,approved=True)
        self.assertEqual(self.state(),before)
        self.assertEqual(len(self.call(dict(op='search',project='alpha',query='SYNTHETIC_CANONICAL'))['records']),1)
        self.assertEqual(self.call(dict(op='search',project='alpha',query='offline'))['records'],[])

    def test_source_changed_during_copy_cannot_contaminate_new_commit(self):
        before = self.state();original = self.a._clone
        rogue = self.f.save_packet(key='rogue-copy',value='SYNTHETIC_UNACKNOWLEDGED')
        def changed(source,path):
            source.handle(self.f.f.laptop(),rogue,approved=True)
            return original(source,path)
        with patch.object(self.a,'_clone',side_effect=changed):
            with self.assertRaises(ValueError):self.call(self.f.save_packet(key='wanted'))
        self.assertEqual(self.state(),before)

    def test_missing_or_wrong_authority_state_is_never_recreated(self):
        with self.a._repository._db() as db:db.execute('UPDATE authority_meta SET version=999')
        before = self.a._repository.catalog.read_bytes()
        with self.assertRaises(ValueError):self.open()
        self.assertEqual(self.a._repository.catalog.read_bytes(),before)
        self.a._repository.catalog.unlink()
        with self.assertRaises(ValueError):self.open()
        self.assertFalse(self.a._repository.catalog.exists())

    def test_wrong_keys_cannot_replace_authority_snapshots(self):
        before = self.state()
        wrong = SyntheticRecovery(SyntheticRecovery.new_key(),synthetic_only=True)
        for values in (dict(storage_key=os.urandom(32)),dict(recovery=wrong)):
            bad = self.open(**values)
            with self.assertRaises(ValueError):bad.acquire(self.anchor.lineage,'b'*32,expected_epoch=1,approved=True)
        self.assertEqual(self.state(),before)

    def test_missing_latest_bundle_does_not_fall_back_to_older_snapshot(self):
        self.call(self.f.save_packet());before = self.state()
        latest = self.current_path().parent/'checkpoint.enc';latest.unlink()
        with self.assertRaises(OSError):self.a.head(self.anchor.lineage)
        with self.assertRaises(OSError):self.call(self.f.save_packet())
        destination = self.f.path.with_name('unsafe-fallback.sqlite')
        with self.assertRaises(OSError):self.a.restore(self.anchor.lineage,destination,expected_anchor=self.anchor,approved=True)
        self.assertFalse(destination.exists());self.assertEqual(self.state(),before)

    def test_publication_failure_and_cancellation_leave_old_head_and_no_receipt(self):
        before = self.state();packet = self.f.save_packet()
        with patch.object(self.r,'bundle',side_effect=OSError('synthetic destination full')):
            with self.assertRaises(OSError):self.call(packet)
        self.assertEqual(self.state(),before)
        cancelled = threading.Event();original = self.r.bundle
        def stop(*args,**kwargs):
            result = original(*args,**kwargs);cancelled.set();return result
        with patch.object(self.r,'bundle',side_effect=stop):
            with self.assertRaises(InterruptedError):self.call(packet,cancelled=cancelled.is_set)
        self.assertEqual(self.state(),before)
        self.assertEqual(self.call(packet)['revision'],1)

    def test_identity_revocation_during_publication_rolls_back_authority(self):
        before = self.state();turn = self.f.f.laptop();original = self.r.bundle
        def revoke(*args,**kwargs):
            result = original(*args,**kwargs);turn._cancelled.set();return result
        with patch.object(self.r,'bundle',side_effect=revoke):
            with self.assertRaises(InterruptedError):self.call(self.f.save_packet(),turn=turn)
        self.assertEqual(self.state(),before)

    def test_catalogue_failure_after_files_publish_rolls_back_pointer_and_retry(self):
        before = self.state();packet = self.f.save_packet()
        with self.a._repository._db() as db:
            db.execute("CREATE TRIGGER fail_pointer BEFORE UPDATE OF live_sha256 ON writers BEGIN SELECT RAISE(ABORT,'synthetic catalogue full'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.call(packet)
        self.assertEqual(self.state(),before)
        with self.a._repository._db() as db:db.execute('DROP TRIGGER fail_pointer')
        self.assertEqual(self.call(packet)['revision'],1)

    def test_read_expiry_cleanup_advances_the_authority_deletion_checkpoint(self):
        receipt = self.call(self.f.save_packet(retention={'mode':'until','expires_at':self.f.now+1}))
        before = self.anchor;self.f.now += 2
        self.assertIsNone(self.get(receipt['id']))
        self.assertEqual(self.anchor.sequence,before.sequence+1)
        destination = self.f.path.with_name('expired-restore.sqlite')
        result = self.a.restore(self.anchor.lineage,destination,expected_anchor=self.anchor,approved=True)
        self.assertEqual(result['result']['suppressed_deleted'],1)

    def test_child_death_before_commit_and_lost_reply_after_commit(self):
        program = '''
from contextlib import contextmanager
import json,os,sys,threading,time
from brain.conversation import Context,PublicTurn
from brain.memory_authority import SyntheticAuthority,WriterGrant
from brain.memory_recovery import SyntheticRecovery,CheckpointAnchor
path,key,recovery_key,binding,grant_json,anchor_json,mode = sys.argv[1:]
authority = SyntheticAuthority(path,storage_key=bytes.fromhex(key),recovery=SyntheticRecovery(bytes.fromhex(recovery_key),synthetic_only=True),synthetic_only=True,clock=lambda:2000000000.)
grant_data = json.loads(grant_json);grant_data['token'] = bytes.fromhex(grant_data['token'])
grant = WriterGrant(**grant_data);anchor = CheckpointAnchor(**json.loads(anchor_json))
context = Context(binding,'laptop','a'*64,binding,4102444800.,True)
turn = PublicTurn('f'*32,'SYNTHETIC_TURN',context,time.monotonic()+30,lambda:context,lambda:2000000000.,threading.Event())
original = authority._repository._db
@contextmanager
def die(*args,**kwargs):
    with original(*args,**kwargs) as db:
        yield db
        if mode == 'before':os._exit(17)
    os._exit(18)
authority._repository._db = die
packet = dict(op='save',project='alpha',request_id=('d' if mode=='before' else 'e')*32,kind='fact',key='authority crash',value={'text':'SYNTHETIC_AUTHORITY_CRASH'},retention={'mode':'permanent'})
authority.handle(grant,turn,packet,expected_anchor=anchor,approved=True)
'''
        from dataclasses import asdict
        env = dict(os.environ);env['PYTHONPATH'] = str(Path(cipher.__file__).resolve().parents[1])
        grant = asdict(self.grant);grant['token'] = self.grant.token.hex()
        before = self.state();old = self.anchor
        for mode,code in (('before',17),('after',18)):
            run = subprocess.run([sys.executable,'-c',program,str(self.path),self.key.hex(),self.recovery_key.hex(),
                                  self.f.f.binding,json.dumps(grant),json.dumps(asdict(old)),mode],
                                 cwd=Path(__file__).resolve().parent,env=env,capture_output=True,text=True,timeout=20,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,code,run.stderr)
            self.a = self.open()
            if mode == 'before':self.assertEqual(self.state(),before)
        packet = dict(op='save',project='alpha',request_id='e'*32,kind='fact',key='authority crash',
                      value={'text':'SYNTHETIC_AUTHORITY_CRASH'},retention={'mode':'permanent'})
        result = self.call(packet,anchor=old)
        self.assertEqual(self.call(packet,anchor=old),result)
        self.assertEqual(self.anchor.sequence,old.sequence+1)


if __name__ == '__main__':unittest.main()
