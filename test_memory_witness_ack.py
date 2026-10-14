"""Fake keys, synthetic identity, disposable stores; no external witness or enrollment."""
from contextlib import closing,contextmanager
from dataclasses import asdict,replace
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from brain.memory_authority import SyntheticAuthority
from brain.memory_custody import RecoveryKeys,SyntheticWitness,WitnessState,seal_keys
from brain.memory_prototype import Conflict
from brain.memory_recovery import SyntheticRecovery

try:from sqlcipher3 import dbapi2 as cipher
except ImportError:cipher = None


@unittest.skipIf(cipher is None,'Use the isolated witness acknowledgement runner.')
class WitnessAckChecks(unittest.TestCase):
    def setUp(self):
        import test_qualification as portable
        self.f = portable.StorageChecks(methodName='runTest');self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.rkey = SyntheticRecovery.new_key()
        self.f.recovery = SyntheticRecovery(self.rkey,synthetic_only=True,clock=lambda:self.f.now)
        self.f.authority();self.bare = self.f.a;self.lineage = self.f.anchor.lineage
        self.w = SyntheticWitness.create(self.f.home/'witness.sqlite',synthetic_only=True,approved=True)
        keys = RecoveryKeys(self.lineage,self.f.key,self.rkey)
        self.digest = seal_keys(self.f.home/'keys.enc',SyntheticRecovery.new_key(),keys,synthetic_only=True,approved=True)
        self.initial = WitnessState(self.f.anchor,self.f.grant.epoch)
        self.w.register(self.initial,self.digest,approved=True)
        self.a = self.open();self.a.bind_witness(self.lineage,self.digest,approved=True)

    def open(self, **kwargs):
        values = dict(recovery=self.f.recovery,storage_key=self.f.key,synthetic_only=True,
                      clock=lambda:self.f.now,witness=self.w)
        values.update(kwargs)
        return SyntheticAuthority(self.bare._repository.path,**values)

    def local(self):
        with self.a._repository._db() as db:return self.a._witness_state(db,self.lineage)

    def call(self, packet, **kwargs):
        values = dict(expected_anchor=self.f.anchor,approved=True);values.update(kwargs)
        reply = self.a.handle(self.f.grant,self.f.turn(),packet,**values)
        self.f.anchor = reply['anchor'];self.assertTrue(reply['witness_confirmed'])
        return reply['result']

    def assert_current(self):
        self.assertEqual(self.w.head(self.lineage),(self.local(),self.digest))
        self.assertTrue(self.a.head(self.lineage)['witness_confirmed'])

    def test_explicit_binding_and_reopen_cannot_omit_or_replace_trust(self):
        original = self.a._repository.catalog.read_bytes()
        for approval in (False,1,'yes',None):
            with self.assertRaises(PermissionError):self.a.bind_witness(self.lineage,self.digest,approved=approval)
        with self.assertRaises(Conflict):self.a.bind_witness(self.lineage,self.digest,approved=True)
        with self.assertRaises(PermissionError):self.open(witness=None)
        with self.assertRaises(PermissionError):self.bare.head(self.lineage)
        with self.assertRaises(PermissionError):self.bare.acquire(self.lineage,'a'*32,expected_epoch=1,approved=True)
        with self.assertRaises(ValueError):self.open(witness=object())
        self.assertEqual(self.a._repository.catalog.read_bytes(),original)
        self.a = self.open();self.assert_current()

    def test_cutover_requires_exact_registered_state_and_digest(self):
        import test_qualification as portable
        f = portable.StorageChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp();f.authority()
        a = SyntheticAuthority(f.a._repository.path,recovery=f.recovery,storage_key=f.key,synthetic_only=True,witness=self.w)
        original = a._repository.catalog.read_bytes()
        with self.assertRaises(ValueError):a.bind_witness(f.anchor.lineage,self.digest,approved=True)
        state = WitnessState(f.anchor,f.grant.epoch)
        self.w.register(state,self.digest,approved=True)
        with self.assertRaises(Conflict):a.bind_witness(f.anchor.lineage,'f'*64,approved=True)
        with self.assertRaises(PermissionError):a.head(f.anchor.lineage)
        with self.assertRaises(PermissionError):a.register(f.memory,approved=True)
        self.assertEqual(a._repository.catalog.read_bytes(),original)
        a.bind_witness(f.anchor.lineage,self.digest,approved=True)
        self.assertTrue(a.head(f.anchor.lineage)['witness_confirmed'])

    def test_saves_correction_forget_and_expiry_are_witnessed(self):
        saved = self.call(self.f.packet())
        self.assert_current()
        self.call(dict(op='correct',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],
                       expected_revision=1,value={'text':'SYNTHETIC_CORRECTION'}))
        self.assert_current()
        self.call(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],expected_revision=2))
        self.assert_current()
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=saved['id']))['record'])
        timed = self.f.packet('timed');timed['retention']={'mode':'until','expires_at':self.f.now+1}
        expiring = self.call(timed);self.f.now += 2
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=expiring['id']))['record'])
        self.assert_current()
        data = self.a._repository.catalog.read_bytes()
        for secret in (self.f.key,self.rkey,self.f.grant.token,b'SYNTHETIC_CORRECTION'):
            self.assertNotIn(secret,data)

    def test_witness_failure_blocks_all_use_until_explicit_reconcile_and_receipt_retry(self):
        packet = self.f.packet();old = self.f.anchor
        with patch.object(self.w,'_advance',side_effect=OSError('Synthetic witness unavailable')):
            with self.assertRaises(OSError):self.call(packet)
        committed = self.local();self.assertGreater(committed.anchor.sequence,old.sequence)
        self.assertEqual(self.w.head(self.lineage)[0],self.initial)
        self.a = self.open()
        with self.assertRaises(Conflict):self.a.head(self.lineage)
        with self.assertRaises(Conflict):self.call(packet)
        with self.assertRaises(Conflict):self.a.acquire(self.lineage,'b'*32,expected_epoch=1,approved=True)
        destination = self.f.home/'blocked.sqlite'
        with self.assertRaises(Conflict):self.a.restore(self.lineage,destination,expected_anchor=old,approved=True)
        self.assertFalse(destination.exists())
        with self.assertRaises(PermissionError):self.a.reconcile_witness(self.lineage)
        reply = self.a.reconcile_witness(self.lineage,approved=True)
        self.assertEqual(reply['anchor'],committed.anchor);self.assertNotIn('grant',reply)
        first = self.call(packet,expected_anchor=old);self.assertEqual(self.call(packet,expected_anchor=old),first)
        self.assertEqual(self.local(),committed);self.assert_current()

    def test_local_commit_failure_never_advances_witness(self):
        original = self.a._repository._db
        @contextmanager
        def failed(*args,**kwargs):
            with original(*args,**kwargs) as db:
                yield db
                raise sqlite3.OperationalError('Synthetic local commit failure')
        with patch.object(self.a._repository,'_db',failed):
            with self.assertRaises(sqlite3.OperationalError):self.call(self.f.packet())
        self.assertEqual(self.local(),self.initial);self.assert_current()

    def test_witness_commit_failure_retains_reconcilable_local_transition(self):
        original = self.w._db;packet = self.f.packet()
        @contextmanager
        def failed():
            with original() as db:
                yield db
                raise sqlite3.OperationalError('Synthetic witness commit failure')
        with patch.object(self.w,'_db',failed):
            with self.assertRaises(sqlite3.OperationalError):self.call(packet)
        self.assertEqual(self.w.head(self.lineage)[0],self.initial)
        with self.assertRaises(Conflict):self.a.head(self.lineage)
        self.a.reconcile_witness(self.lineage,approved=True);self.call(packet);self.assert_current()

    def test_lost_reply_after_witness_commit_replays_only_the_receipt(self):
        original = self.w._db;packet = self.f.packet()
        @contextmanager
        def lost():
            with original() as db:yield db
            raise OSError('Synthetic reply lost after witness commit')
        with patch.object(self.w,'_db',lost):
            with self.assertRaises(OSError):self.call(packet)
        committed = self.local();self.assert_current()
        first = self.call(packet);self.assertEqual(self.call(packet),first)
        self.assertEqual(self.local(),committed)

    def test_failed_takeover_reconciles_generation_without_releasing_lost_grant(self):
        old = self.f.grant
        with patch.object(self.w,'_advance',side_effect=OSError('Synthetic witness failure')):
            with self.assertRaises(OSError):self.a.acquire(self.lineage,'b'*32,expected_epoch=old.epoch,approved=True)
        self.assertEqual(self.local().writer_epoch,old.epoch+1)
        reply = self.a.reconcile_witness(self.lineage,approved=True);self.assertNotIn('grant',reply)
        self.f.grant = self.a.acquire(self.lineage,'c'*32,expected_epoch=reply['writer_epoch'],approved=True)
        with self.assertRaises(PermissionError):
            self.a.handle(old,self.f.turn(),self.f.packet(),expected_anchor=self.f.anchor,approved=True)
        self.assert_current()

    def test_restore_and_activation_both_require_witness_commit(self):
        saved = self.call(self.f.packet())
        self.call(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],expected_revision=1))
        destination = self.f.home/'quarantine.sqlite';old = self.f.grant
        with patch.object(self.w,'_advance',side_effect=OSError('Synthetic witness failure')):
            with self.assertRaises(OSError):self.a.restore(self.lineage,destination,expected_anchor=self.f.anchor,approved=True)
        with self.assertRaises(Conflict):
            self.a.activate_restored(self.lineage,destination,self.f.turn(),'b'*32,expected_anchor=self.f.anchor,
                                     expected_epoch=old.epoch+1,approved=True)
        restored = self.a.reconcile_witness(self.lineage,approved=True)
        with self.assertRaises(Conflict):self.a.acquire(self.lineage,'b'*32,expected_epoch=restored['writer_epoch'],approved=True)
        with patch.object(self.w,'_advance',side_effect=OSError('Synthetic witness failure')):
            with self.assertRaises(OSError):
                self.a.activate_restored(self.lineage,destination,self.f.turn(),'b'*32,expected_anchor=self.f.anchor,
                                         expected_epoch=restored['writer_epoch'],approved=True)
        activated = self.a.reconcile_witness(self.lineage,approved=True);self.f.anchor = activated['anchor']
        self.assertFalse(self.a.head(self.lineage)['recovery_pending'])
        self.f.grant = self.a.acquire(self.lineage,'c'*32,expected_epoch=activated['writer_epoch'],approved=True)
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=saved['id']))['record'])
        self.assert_current()

    def test_successful_restore_activation_and_fresh_owner_proof(self):
        destination = self.f.home/'quarantine.sqlite'
        restored = self.a.restore(self.lineage,destination,expected_anchor=self.f.anchor,approved=True)
        self.assertTrue(restored['witness_confirmed']);self.assert_current()
        with self.assertRaises(PermissionError):
            self.a.activate_restored(self.lineage,destination,self.f.turn(verified=False),'b'*32,
                expected_anchor=self.f.anchor,expected_epoch=restored['writer_epoch'],approved=True)
        reply = self.a.activate_restored(self.lineage,destination,self.f.turn(),'b'*32,
            expected_anchor=self.f.anchor,expected_epoch=restored['writer_epoch'],approved=True)
        self.assertTrue(reply['witness_confirmed']);self.assertEqual((reply['active_bindings'],reply['resumed_jobs']),(1,0))
        self.assert_current()

    def test_source_rollback_is_rejected_without_republishing_stale_state(self):
        backup = self.f.home/'old-catalog.sqlite'
        with closing(sqlite3.connect(self.a._repository.catalog)) as source,closing(sqlite3.connect(backup)) as target:source.backup(target)
        self.call(self.f.packet());latest = self.w.head(self.lineage)
        shutil.copyfile(backup,self.a._repository.catalog)
        self.a = self.open()
        with self.assertRaises(Conflict):self.a.head(self.lineage)
        with self.assertRaises(Conflict):self.a.reconcile_witness(self.lineage,approved=True)
        self.assertEqual(self.w.head(self.lineage),latest)

    def test_missing_witness_and_missing_binding_never_recreate_trust(self):
        blob = self.w.path.read_bytes();self.w.path.unlink()
        with self.assertRaises(sqlite3.OperationalError):self.a.head(self.lineage)
        with self.assertRaises(sqlite3.OperationalError):self.a.reconcile_witness(self.lineage,approved=True)
        self.assertFalse(self.w.path.exists());self.w.path.write_bytes(blob)
        with self.w._db() as db:db.execute('DELETE FROM heads')
        with self.assertRaises(ValueError):self.a.reconcile_witness(self.lineage,approved=True)
        with self.a._repository._db() as db:db.execute('DROP TABLE witness_links')
        with self.assertRaises(sqlite3.DatabaseError):self.open()

    def test_corrupt_journal_and_key_pin_cannot_be_reconciled(self):
        with self.a._repository._db() as db:
            db.execute('UPDATE witness_links SET keys_digest=?',('f'*64,))
        with self.assertRaises(Conflict):self.a.head(self.lineage)
        with self.assertRaises(Conflict):self.a.reconcile_witness(self.lineage,approved=True)
        with self.a._repository._db() as db:
            db.execute('UPDATE witness_links SET keys_digest=?,next_state=?',(self.digest,'{}'))
        with self.assertRaises(ValueError):self.a.reconcile_witness(self.lineage,approved=True)
        self.assertEqual(self.w.head(self.lineage),(self.initial,self.digest))

    def test_cancellation_after_local_commit_withholds_acknowledgement(self):
        cancelled = threading.Event();original = self.w._advance;packet = self.f.packet()
        def cancel(*args):
            result = original(*args);cancelled.set();return result
        with patch.object(self.w,'_advance',side_effect=cancel):
            with self.assertRaises(InterruptedError):self.call(packet,cancelled=cancelled.is_set)
        self.assertEqual(self.w.head(self.lineage)[0],self.initial)
        self.a.reconcile_witness(self.lineage,approved=True);self.call(packet);self.assert_current()

    def test_identity_revocation_during_witness_commit_withholds_reply(self):
        original = self.w._advance;turn = self.f.turn();packet = self.f.packet()
        def revoke(*args):
            result = original(*args);turn._cancelled.set();return result
        with patch.object(self.w,'_advance',side_effect=revoke):
            with self.assertRaises(InterruptedError):
                self.a.handle(self.f.grant,turn,packet,expected_anchor=self.f.anchor,approved=True)
        committed = self.local();self.assert_current()
        self.call(packet);self.assertEqual(self.local(),committed)

    def test_witness_advance_cannot_race_the_restore_check_and_use(self):
        entered = threading.Event();release = threading.Event();started = threading.Event();done = threading.Event()
        results = [];original = self.f.recovery.restore
        def paused(*args,**kwargs):
            entered.set()
            if not release.wait(2):raise RuntimeError('Synthetic restore barrier timed out')
            return original(*args,**kwargs)
        def restore():
            try:results.append(self.a.restore(self.lineage,self.f.home/'quarantine.sqlite',expected_anchor=self.f.anchor,approved=True))
            except Exception as error:results.append(error)
        def advance():
            started.set()
            try:results.append(self.w.advance(self.initial,replace(self.initial,writer_epoch=99),self.digest,approved=True))
            except Exception as error:results.append(error)
            finally:done.set()
        with patch.object(self.f.recovery,'restore',side_effect=paused):
            first = threading.Thread(target=restore);first.start();self.assertTrue(entered.wait(2))
            second = threading.Thread(target=advance);second.start();self.assertTrue(started.wait(2))
            try:self.assertFalse(done.wait(.1))
            finally:release.set();first.join(5);second.join(5)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(sum(isinstance(item,Conflict) for item in results),1)
        self.assertEqual(sum(type(item) is dict for item in results),1);self.assert_current()

    def test_simultaneous_writes_have_one_witnessed_winner(self):
        barrier = threading.Barrier(2);results = [];anchor = self.f.anchor
        def write():
            try:
                packet = self.f.packet(os.urandom(8).hex());barrier.wait(3)
                results.append(self.a.handle(self.f.grant,self.f.turn(),packet,expected_anchor=anchor,approved=True))
            except Exception as error:results.append(error)
        threads = [threading.Thread(target=write) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(type(item) is dict for item in results),1)
        self.assertEqual(sum(isinstance(item,Conflict) for item in results),1);self.assert_current()

    def test_process_death_before_local_commit_between_commits_and_after_witness_commit(self):
        program = r'''
from contextlib import contextmanager
import json,os,sys,threading,time
p=json.load(sys.stdin);sys.path[:0]=p['imports']
from brain.memory_authority import SyntheticAuthority,WriterGrant
from brain.memory_custody import SyntheticWitness
from brain.memory_recovery import SyntheticRecovery,CheckpointAnchor
from brain.conversation import Context,PublicTurn
w=SyntheticWitness(p['witness'],synthetic_only=True)
a=SyntheticAuthority(p['authority'],witness=w,storage_key=bytes.fromhex(p['key']),
    recovery=SyntheticRecovery(p['recovery'].encode(),synthetic_only=True,clock=lambda:p['now']),synthetic_only=True,clock=lambda:p['now'])
original=a._repository._db if p['mode']=='before_local' else w._db
@contextmanager
def die(*args,**kwargs):
    with original(*args,**kwargs) as db:
        yield db
        if p['mode']=='before_local':os._exit(17)
    os._exit(19)
if p['mode']=='before_local':a._repository._db=die
elif p['mode']=='after_local':w._advance=lambda *args:os._exit(18)
else:w._db=die
g=p['grant'];g['token']=bytes.fromhex(g['token']);grant=WriterGrant(**g)
c=Context('1'*64,'phone','2'*64,'1'*64,p['now']+300,True)
t=PublicTurn('3'*32,'SYNTHETIC_CRASH',c,time.monotonic()+30,lambda:c,lambda:p['now'],threading.Event())
a.handle(grant,t,p['packet'],expected_anchor=CheckpointAnchor(**p['anchor']),approved=True)
'''
        for mode,code in (('before_local',17),('after_local',18),('after_witness',19)):
            before = self.local();packet = self.f.packet(mode);grant = asdict(self.f.grant);grant['token']=grant['token'].hex()
            data = dict(imports=[str(Path(__file__).resolve().parent),str(Path(cipher.__file__).resolve().parents[1])],
                witness=str(self.w.path),authority=str(self.a._repository.path),key=self.f.key.hex(),recovery=self.rkey.decode(),
                now=self.f.now,grant=grant,packet=packet,anchor=asdict(self.f.anchor),mode=mode)
            run = subprocess.run([sys.executable,'-I','-B','-c',program],input=json.dumps(data),capture_output=True,text=True,
                                 timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,code,'Synthetic crash child failed; raw output withheld.')
            self.a = self.open()
            if mode=='before_local':self.assertEqual(self.local(),before)
            elif mode=='after_local':
                with self.assertRaises(Conflict):self.a.head(self.lineage)
                self.a.reconcile_witness(self.lineage,approved=True)
            else:self.assert_current()
            first = self.call(packet);current = self.local()
            self.assertEqual(self.call(packet),first);self.assertEqual(self.local(),current);self.assert_current()


if __name__=='__main__':unittest.main()
