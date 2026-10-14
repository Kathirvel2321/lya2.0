"""Disposable fake-owner recovery/reactivation checks; no enrollment or real keys."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import os
import threading
import unittest
from unittest.mock import patch

from brain.memory_authority import SyntheticAuthority
from brain.memory_prototype import Conflict, SyntheticMemory
import test_memory_authority as fixtures


@unittest.skipIf(fixtures.cipher is None,'Run the isolated recovery/reactivation runner.')
class ReactivationChecks(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.AuthorityChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.restored = self.f.f.path.with_name('quarantined.sqlite')
        self.recovery = self.f.a.restore(self.f.anchor.lineage,self.restored,
                                         expected_anchor=self.f.anchor,approved=True)

    def state(self):
        with self.f.a._repository._db() as db:
            return {table:[dict(row) for row in db.execute('SELECT * FROM '+table)]
                    for table in ('latest','writers','owner_bindings','recoveries')}

    def activate(self, **kwargs):
        values = dict(lineage=self.f.anchor.lineage,restored=self.restored,turn=self.f.f.f.phone_turn(),
                      writer='b'*32,expected_anchor=self.f.anchor,expected_epoch=self.recovery['writer_epoch'],approved=True)
        values.update(kwargs)
        result = self.f.a.activate_restored(**values)
        self.f.grant,self.f.anchor = result['grant'],result['anchor']
        return result

    def test_activation_rebinds_verified_existing_owner_without_changing_quarantine(self):
        before = self.restored.read_bytes();old = self.f.grant;old_anchor = self.f.anchor
        result = self.activate()
        self.assertEqual(self.restored.read_bytes(),before)
        self.assertEqual((result['active_bindings'],result['resumed_jobs'],result['quarantined']),(1,0,False))
        self.assertEqual(result['anchor'].sequence,old_anchor.sequence+2)
        self.assertGreater(result['grant'].epoch,self.recovery['writer_epoch'])
        self.f.a = self.f.open()
        self.assertEqual(self.f.get(self.f.seed['id'])['owner'],self.f.f.owner)
        self.assertFalse(self.f.a.head(old_anchor.lineage)['recovery_pending'])
        with self.assertRaises(PermissionError):self.f.call(self.f.f.save_packet(),grant=old)
        current = SyntheticMemory(self.f.current_path(),synthetic_only=True,encryption_key=self.f.key)
        with current._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM bindings').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM outbox').fetchone()[0],0)
        catalogue = self.f.a._repository.catalog.read_bytes()
        for secret in (self.f.key,self.f.recovery_key,result['grant'].token,self.f.f.f.binding.encode()):
            self.assertNotIn(secret,catalogue)
        self.assertNotIn(b'SQLite format 3',self.f.current_path().read_bytes())

    def test_normal_takeover_cannot_bypass_pending_recovery(self):
        before = self.state();head = self.f.a.head(self.f.anchor.lineage)
        self.assertTrue(head['recovery_pending']);self.assertFalse(head['writer_active'])
        with self.assertRaises(Conflict):
            self.f.a.acquire(self.f.anchor.lineage,'b'*32,expected_epoch=head['writer_epoch'],approved=True)
        with self.assertRaises(PermissionError):self.f.get(self.f.seed['id'])
        self.assertEqual(self.state(),before)

    def test_activation_requires_literal_approval_fresh_proof_and_registered_identity(self):
        before = self.state()
        for approval in (False,1,'yes',None):
            with self.assertRaises(PermissionError):self.activate(approved=approval)
        with self.f.f.phone_unverified():
            with self.assertRaises(PermissionError):self.activate()
        turn = self.f.f.f.laptop();context = replace(turn.context,principal='c'*64)
        with self.assertRaises(PermissionError):self.activate(turn=replace(turn,context=context,_resolve=lambda:context))
        turn._cancelled.set()
        with self.assertRaises(InterruptedError):self.activate(turn=turn)
        self.assertEqual(self.state(),before)

    def test_tampered_missing_or_unacknowledged_restore_is_rejected(self):
        before = self.state();original = self.restored.read_bytes()
        damaged = bytearray(original);damaged[len(damaged)//2] ^= 1;self.restored.write_bytes(damaged)
        with self.assertRaises(ValueError):self.activate()
        self.restored.unlink()
        with self.assertRaises(OSError):self.activate()
        with self.assertRaises(ValueError):self.activate(restored=self.f.f.path)
        self.assertEqual(self.state(),before)
        self.restored.write_bytes(original);self.activate()

    def test_second_restore_supersedes_the_first_activation_receipt(self):
        old_epoch = self.recovery['writer_epoch'];old_path = self.restored
        destination = old_path.with_name('new-quarantine.sqlite')
        self.recovery = self.f.a.restore(self.f.anchor.lineage,destination,expected_anchor=self.f.anchor,approved=True)
        self.assertGreater(self.recovery['writer_epoch'],old_epoch)
        before = self.state()
        with self.assertRaises(Conflict):self.activate(expected_epoch=old_epoch)
        with self.assertRaises(ValueError):self.activate(restored=old_path)
        self.assertEqual(self.state(),before)
        self.restored = destination;self.activate()
        with self.assertRaises(Conflict):self.activate()

    def test_reactivation_does_not_bind_other_owners_automatically(self):
        other = self.f.f.m.create_owner('c'*64)
        turn = self.f.f.f.laptop();context = replace(turn.context,principal='c'*64)
        other_turn = replace(turn,context=context,_resolve=lambda:context)
        other_record = self.f.f.call(self.f.f.save_packet(key='other-owner'),turn=other_turn)
        path = self.f.path.with_name('multi-owner-authority')
        self.f.a = SyntheticAuthority(path,recovery=self.f.r,storage_key=self.f.key,synthetic_only=True,clock=lambda:self.f.f.now)
        self.f.path = path;self.f.anchor = self.f.a.register(self.f.f.m,approved=True)
        self.restored = self.restored.with_name('multi-quarantine.sqlite')
        self.recovery = self.f.a.restore(self.f.anchor.lineage,self.restored,expected_anchor=self.f.anchor,approved=True)
        self.activate()
        self.assertNotEqual(other,self.f.f.owner)
        self.assertEqual(self.f.get(self.f.seed['id'])['owner'],self.f.f.owner)
        with self.assertRaises(PermissionError):
            self.f.call(dict(op='get',project='alpha',id=other_record['id']),turn=other_turn)

    def test_publication_failure_or_cancellation_keeps_recovery_pending(self):
        before = self.state();original_hash = hashlib.sha256(self.restored.read_bytes()).hexdigest()
        with patch.object(self.f.r,'bundle',side_effect=OSError('synthetic unavailable destination')):
            with self.assertRaises(OSError):self.activate()
        self.assertEqual(self.state(),before)
        cancelled = threading.Event();original = self.f.r.bundle
        def stop(*args,**kwargs):
            result = original(*args,**kwargs);cancelled.set();return result
        with patch.object(self.f.r,'bundle',side_effect=stop):
            with self.assertRaises(InterruptedError):self.activate(cancelled=cancelled.is_set)
        self.assertEqual(self.state(),before)
        self.assertEqual(hashlib.sha256(self.restored.read_bytes()).hexdigest(),original_hash)
        self.activate()

    def test_owner_proof_revoked_during_publication_cannot_activate(self):
        before = self.state();turn = self.f.f.f.phone_turn();original = self.f.r.bundle
        def revoke(*args,**kwargs):
            result = original(*args,**kwargs)
            self.f.f.f.phone.app.session(self.f.f.f.token)['owner_until'] = 0
            return result
        with patch.object(self.f.r,'bundle',side_effect=revoke):
            with self.assertRaises(PermissionError):self.activate(turn=turn)
        self.assertEqual(self.state(),before)

    def test_catalogue_failure_after_publication_rolls_back_binding_pointer_and_grant(self):
        before = self.state()
        with self.f.a._repository._db() as db:
            db.execute("CREATE TRIGGER stop_activation BEFORE DELETE ON recoveries BEGIN SELECT RAISE(ABORT,'synthetic full catalogue'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.activate()
        self.assertEqual(self.state(),before)
        with self.f.a._repository._db() as db:db.execute('DROP TRIGGER stop_activation')
        self.activate()

    def test_concurrent_activation_has_one_winner(self):
        barrier = threading.Barrier(2);results = [];anchor = self.f.anchor
        def run():
            barrier.wait(3)
            try:results.append(self.activate(expected_anchor=anchor))
            except Exception as error:results.append(error)
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(30)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(type(result) is dict for result in results),1)
        loser = next(result for result in results if type(result) is not dict)
        if isinstance(loser,sqlite3.OperationalError):self.assertEqual(str(loser),'database is locked')
        else:self.assertIsInstance(loser,Conflict)
        before = self.state()
        with self.assertRaises(Conflict):self.activate(expected_anchor=anchor)
        self.assertEqual(self.state(),before)
        self.assertFalse(self.f.a.head(self.f.anchor.lineage)['recovery_pending'])

    def test_child_death_before_and_after_activation_commit(self):
        program = '''
from contextlib import contextmanager
import json,os,sys,threading,time
from brain.conversation import Context,PublicTurn
from brain.memory_authority import SyntheticAuthority
from brain.memory_recovery import CheckpointAnchor,SyntheticRecovery
path,key,recovery_key,binding,anchor_json,epoch,restored,now,mode = sys.argv[1:]
now = float(now);anchor = CheckpointAnchor(**json.loads(anchor_json))
authority = SyntheticAuthority(path,storage_key=bytes.fromhex(key),recovery=SyntheticRecovery(bytes.fromhex(recovery_key),synthetic_only=True,clock=lambda:now),synthetic_only=True,clock=lambda:now)
context = Context(binding,'phone','a'*64,binding,now+300,True)
turn = PublicTurn('f'*32,'SYNTHETIC_ACTIVATION',context,time.monotonic()+30,lambda:context,lambda:now,threading.Event())
original = authority._repository._db
@contextmanager
def die(*args,**kwargs):
    with original(*args,**kwargs) as db:
        yield db
        if mode == 'before':os._exit(17)
    os._exit(18)
authority._repository._db = die
authority.activate_restored(anchor.lineage,restored,turn,'b'*32,expected_anchor=anchor,expected_epoch=int(epoch),approved=True)
'''
        env = dict(os.environ);env['PYTHONPATH'] = str(Path(fixtures.cipher.__file__).resolve().parents[1])
        before = self.state();anchor = self.f.anchor;old_grant = self.f.grant
        for mode,code in (('before',17),('after',18)):
            run = subprocess.run([sys.executable,'-c',program,str(self.f.path),self.f.key.hex(),self.f.recovery_key.hex(),
                                  self.f.f.f.binding,json.dumps(asdict(anchor)),str(self.recovery['writer_epoch']),str(self.restored),
                                  str(self.f.f.now),mode],cwd=Path(__file__).resolve().parent,env=env,
                                 capture_output=True,text=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,code,run.stderr)
            self.f.a = self.f.open()
            if mode == 'before':self.assertEqual(self.state(),before)
        head = self.f.a.head(anchor.lineage)
        self.assertFalse(head['recovery_pending']);self.assertEqual(head['anchor'].sequence,anchor.sequence+2)
        self.f.anchor = head['anchor']
        with self.assertRaises(PermissionError):self.f.call(self.f.f.save_packet(),grant=old_grant)
        self.f.grant = self.f.a.acquire(anchor.lineage,'d'*32,expected_epoch=head['writer_epoch'],approved=True)
        self.assertEqual(self.f.get(self.f.seed['id'])['owner'],self.f.f.owner)

    def test_unacknowledged_restore_destination_cannot_replace_acknowledged_quarantine(self):
        before = self.state();destination = self.restored.with_name('unacknowledged.sqlite')
        with self.f.a._repository._db() as db:
            db.execute("CREATE TRIGGER fail_recovery BEFORE INSERT ON recoveries BEGIN SELECT RAISE(ABORT,'synthetic receipt failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.f.a.restore(self.f.anchor.lineage,destination,expected_anchor=self.f.anchor,approved=True)
        self.assertTrue(destination.exists());self.assertEqual(self.state(),before)
        with self.assertRaises(ValueError):self.activate(restored=destination)
        self.assertEqual(self.state(),before)

    def test_authority_schema_one_is_refused_without_migration(self):
        with self.f.a._repository._db() as db:db.execute('UPDATE authority_meta SET version=1')
        original = self.f.a._repository.catalog.read_bytes()
        with self.assertRaises(ValueError):self.f.open()
        self.assertEqual(self.f.a._repository.catalog.read_bytes(),original)

    def test_changed_candidate_copy_cannot_activate(self):
        before = self.state();original = self.f.a._clone
        def changed(*args):
            result = original(*args)
            with result._db() as db:db.execute('UPDATE memories SET value=?',('{"text":"SYNTHETIC_CHANGED_COPY"}',))
            return result
        with patch.object(self.f.a,'_clone',side_effect=changed):
            with self.assertRaises(ValueError):self.activate()
        self.assertEqual(self.state(),before)

    def test_source_loss_restore_and_reactivation_preserve_correction_forget_and_expiry(self):
        self.activate()
        kept = self.f.call(self.f.f.save_packet(key='kept',value='SYNTHETIC_BEFORE_CORRECTION'))
        self.f.call(dict(op='correct',project='alpha',request_id=self.f.f.rid(),id=kept['id'],
                         expected_revision=1,value={'text':'SYNTHETIC_AFTER_CORRECTION'}),turn=self.f.f.f.phone_turn())
        self.f.call(dict(op='forget',project='alpha',request_id=self.f.f.rid(),id=self.f.seed['id'],expected_revision=1))
        expired = self.f.call(self.f.f.save_packet(key='expires',retention={'mode':'until','expires_at':self.f.f.now+1}))
        self.f.f.now += 2;self.f.current_path().unlink()
        self.restored = self.restored.with_name('after-source-loss.sqlite')
        self.recovery = self.f.a.restore(self.f.anchor.lineage,self.restored,expected_anchor=self.f.anchor,approved=True)
        self.assertEqual((self.recovery['result']['suppressed_deleted'],self.recovery['result']['suppressed_expired']),(1,1))
        self.activate()
        self.assertIsNone(self.f.get(self.f.seed['id']));self.assertIsNone(self.f.get(expired['id']))
        record = self.f.call(dict(op='get',project='alpha',id=kept['id']),turn=self.f.f.f.phone_turn())['record']
        self.assertEqual((record['value']['text'],record['revision'],record['owner']),
                         ('SYNTHETIC_AFTER_CORRECTION',2,self.f.f.owner))
        current = SyntheticMemory(self.f.current_path(),synthetic_only=True,encryption_key=self.f.key)
        with current._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM deletions').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT count(*) FROM outbox').fetchone()[0],0)


if __name__ == '__main__':unittest.main()
