"""Generated fake keys and temporary stores only; no real password manager access."""
from contextlib import closing
from dataclasses import asdict,replace
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from brain.memory_custody import MAGIC,RecoveryKeys,SyntheticWitness,WitnessState,open_keys,seal_keys
from brain.memory_prototype import Conflict
from brain.memory_recovery import CheckpointAnchor,SyntheticRecovery
from brain.memory_authority import SyntheticAuthority


class CustodyChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.home = Path(temp.name)
        self.unlock = Fernet.generate_key();self.keys = RecoveryKeys('1'*32,os.urandom(32),Fernet.generate_key())
        self.capsule = self.home/'keys.enc'
        self.digest = seal_keys(self.capsule,self.unlock,self.keys,synthetic_only=True,approved=True)
        self.witness = SyntheticWitness.create(self.home/'witness.sqlite',synthetic_only=True,approved=True)
        self.state = WitnessState(CheckpointAnchor(self.keys.lineage,1,'2'*32,'3'*64),1)
        self.witness.register(self.state,self.digest,approved=True)

    def unlock_keys(self, **kwargs):
        values = dict(lineage=self.keys.lineage,trusted_digest=self.digest,synthetic_only=True,approved=True)
        values.update(kwargs)
        return open_keys(self.capsule,self.unlock,**values)

    def next(self, **kwargs):
        values = dict(anchor=replace(self.state.anchor,sequence=2,checkpoint_id='4'*32,sha256='5'*64),writer_epoch=2)
        values.update(kwargs);return WitnessState(**values)

    def test_encrypted_roundtrip_restart_and_secret_free_witness_and_repr(self):
        self.assertEqual(self.unlock_keys(),self.keys)
        witness = SyntheticWitness(self.witness.path,synthetic_only=True)
        self.assertEqual(witness.head(self.keys.lineage),(self.state,self.digest))
        blob = self.capsule.read_bytes();catalog = self.witness.path.read_bytes()
        for key in (self.unlock,self.keys.storage_key,self.keys.recovery_key):
            self.assertNotIn(key,blob);self.assertNotIn(key,catalog);self.assertNotIn(key.hex(),repr(self.keys))
        self.assertNotIn(self.keys.storage_key.hex().encode(),blob)
        self.assertNotIn(self.keys.recovery_key.decode(),repr(self.keys))

    def test_explicit_approval_synthetic_opt_in_and_independent_unlock_key(self):
        for value in (False,1,'yes',None):
            with self.assertRaises(PermissionError):self.unlock_keys(approved=value)
            with self.assertRaises(PermissionError):self.witness.advance(self.state,self.next(),self.digest,approved=value)
        with self.assertRaises(PermissionError):self.unlock_keys(synthetic_only=False)
        for unlock in (self.keys.recovery_key,base64.urlsafe_b64encode(self.keys.storage_key)):
            with self.assertRaises(ValueError):seal_keys(self.home/'bad.enc',unlock,self.keys,synthetic_only=True,approved=True)
        with self.assertRaises(PermissionError):SyntheticWitness(self.witness.path)

    def test_wrong_unlock_tampered_replaced_and_wrong_lineage_capsules_are_rejected(self):
        with self.assertRaises(ValueError):open_keys(self.capsule,Fernet.generate_key(),lineage=self.keys.lineage,
            trusted_digest=self.digest,synthetic_only=True,approved=True)
        with self.assertRaises(ValueError):self.unlock_keys(lineage='6'*32)
        original = self.capsule.read_bytes();self.capsule.write_bytes(original[:-5]+b'wrong')
        with self.assertRaises(ValueError):self.unlock_keys()
        self.capsule.unlink()
        new_digest = seal_keys(self.capsule,self.unlock,self.keys,synthetic_only=True,approved=True)
        self.assertNotEqual(new_digest,self.digest)
        with self.assertRaises(ValueError):self.unlock_keys()
        with self.assertRaises(Conflict):self.witness.require(self.state,new_digest)

    def test_malformed_authenticated_and_oversized_envelopes_fail_closed(self):
        cipher = Fernet(self.unlock)
        for raw in (b'{}',b'{"version":1,"version":1}',b'{"version":true,"lineage":"bad","storage_key":"","recovery_key":""}'):
            blob = MAGIC+cipher.encrypt(raw);self.capsule.write_bytes(blob)
            with self.assertRaises(ValueError):self.unlock_keys(trusted_digest=hashlib.sha256(blob).hexdigest())
        self.capsule.write_bytes(MAGIC+b'x'*8193)
        with self.assertRaises(ValueError):self.unlock_keys()

    def test_no_overwrite_missing_witness_and_schema_refusal_preserve_files(self):
        original = self.capsule.read_bytes()
        with self.assertRaises(FileExistsError):seal_keys(self.capsule,self.unlock,self.keys,synthetic_only=True,approved=True)
        self.assertEqual(self.capsule.read_bytes(),original)
        with self.witness._db() as db:db.execute('PRAGMA user_version=999')
        before = self.witness.path.read_bytes()
        with self.assertRaises(ValueError):SyntheticWitness(self.witness.path,synthetic_only=True)
        self.assertEqual(self.witness.path.read_bytes(),before)
        self.witness.path.unlink()
        with self.assertRaises(sqlite3.OperationalError):self.witness.require(self.state,self.digest)
        with self.assertRaises(sqlite3.OperationalError):SyntheticWitness(self.witness.path,synthetic_only=True)
        self.assertFalse(self.witness.path.exists())

    def test_monotonic_advance_retry_and_key_pin(self):
        target = self.next();self.witness.advance(self.state,target,self.digest,approved=True)
        self.assertEqual(self.witness.advance(self.state,target,self.digest,approved=True),target)
        with self.assertRaises(Conflict):self.witness.require(self.state,self.digest)
        with self.assertRaises(Conflict):self.witness.advance(target,self.state,self.digest,approved=True)
        with self.assertRaises(Conflict):self.witness.advance(target,self.next(writer_epoch=3),'f'*64,approved=True)
        self.assertEqual(self.witness.require(target,self.digest),target)
        with self.assertRaises(Conflict):self.witness.register(self.state,self.digest,approved=True)

    def test_writer_epoch_only_advance_detects_same_anchor_authority_rollback(self):
        target = replace(self.state,writer_epoch=2)
        self.witness.advance(self.state,target,self.digest,approved=True)
        with self.assertRaises(Conflict):self.witness.require(self.state,self.digest)
        with self.assertRaises(Conflict):self.witness.advance(target,self.next(writer_epoch=1),self.digest,approved=True)
        divergent = replace(target,anchor=replace(target.anchor,sha256='6'*64))
        with self.assertRaises(Conflict):self.witness.advance(target,divergent,self.digest,approved=True)
        self.assertEqual(self.witness.head(self.keys.lineage)[0],target)

    def test_cancel_and_catalogue_failure_do_not_advance_witness(self):
        with self.assertRaises(InterruptedError):self.witness.advance(self.state,self.next(),self.digest,approved=True,cancelled=lambda:True)
        with self.witness._db() as db:
            db.execute("CREATE TRIGGER fail_advance BEFORE UPDATE ON heads BEGIN SELECT RAISE(ABORT,'synthetic full'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.witness.advance(self.state,self.next(),self.digest,approved=True)
        self.assertEqual(self.witness.head(self.keys.lineage),(self.state,self.digest))
        with self.assertRaises(InterruptedError):seal_keys(self.home/'cancelled.enc',self.unlock,self.keys,
            synthetic_only=True,approved=True,cancelled=lambda:True)
        self.assertFalse((self.home/'cancelled.enc').exists())

    def test_process_death_before_and_after_witness_commit(self):
        program = r'''
from contextlib import contextmanager
import json,os,sys
p=json.load(sys.stdin);sys.path.insert(0,p['root'])
from brain.memory_custody import SyntheticWitness,WitnessState
from brain.memory_recovery import CheckpointAnchor
w=SyntheticWitness(p['path'],synthetic_only=True);original=w._db
@contextmanager
def die():
    with original() as db:
        yield db
        if p['mode']=='before':os._exit(17)
    os._exit(18)
w._db=die
def state(data):return WitnessState(CheckpointAnchor(**data['anchor']),data['writer_epoch'])
w.advance(state(p['previous']),state(p['target']),p['digest'],approved=True)
'''
        target = self.next()
        for mode,code in (('before',17),('after',18)):
            packet = dict(root=str(Path(__file__).resolve().parent),path=str(self.witness.path),
                previous=asdict(self.state),target=asdict(target),digest=self.digest,mode=mode)
            result = subprocess.run([sys.executable,'-I','-B','-c',program],input=json.dumps(packet),
                capture_output=True,text=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(result.returncode,code,'Synthetic witness child failed; raw output withheld.')
            self.assertEqual(self.witness.head(self.keys.lineage)[0],self.state if mode=='before' else target)
        self.assertEqual(self.witness.advance(self.state,target,self.digest,approved=True),target)

    def test_simultaneous_witness_updates_have_one_winner(self):
        barrier = threading.Barrier(2);results = []
        def run(target):
            barrier.wait(3)
            try:results.append(self.witness.advance(self.state,target,self.digest,approved=True))
            except Exception as error:results.append(error)
        targets = (self.next(),self.next(anchor=replace(self.next().anchor,checkpoint_id='7'*32)))
        threads = [threading.Thread(target=run,args=(target,)) for target in targets]
        for thread in threads:thread.start()
        for thread in threads:thread.join(10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(type(result) is WitnessState for result in results),1)
        self.assertEqual(sum(isinstance(result,Conflict) for result in results),1)

    def test_invalid_states_and_unknown_lineage_cannot_register_or_advance(self):
        for value in (-1,True,2**63):
            with self.assertRaises(ValueError):WitnessState(self.state.anchor,value)
        with self.assertRaises(ValueError):self.witness.head('8'*32)
        foreign = replace(self.state,anchor=replace(self.state.anchor,lineage='8'*32))
        with self.assertRaises(Conflict):self.witness.advance(self.state,foreign,self.digest,approved=True)
        with self.assertRaises(ValueError):self.witness.require(self.state,'not-a-digest')

    @unittest.skipUnless(importlib.util.find_spec('sqlcipher3'),'Run the isolated custody qualification runner.')
    def test_recovery_uses_unlocked_keys_and_witness_to_reject_stale_authority(self):
        # Reuse only the portable fake storage fixture, never native enrollment or a real vault.
        import test_qualification as portable
        fixture = portable.StorageChecks(methodName='runTest');self.addCleanup(fixture.doCleanups);fixture.setUp()
        recovery_key = Fernet.generate_key()
        fixture.recovery = SyntheticRecovery(recovery_key,synthetic_only=True,clock=lambda:fixture.now)
        fixture.authority();old_state = WitnessState(fixture.anchor,fixture.grant.epoch)
        keys = RecoveryKeys(fixture.anchor.lineage,fixture.key,recovery_key)
        path = self.home/'authority-keys.enc'
        digest = seal_keys(path,self.unlock,keys,synthetic_only=True,approved=True)
        witness = SyntheticWitness.create(self.home/'authority-witness.sqlite',synthetic_only=True,approved=True)
        witness.register(old_state,digest,approved=True)
        saved = fixture.request(fixture.packet())
        fixture.request(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],expected_revision=1))
        current = WitnessState(fixture.anchor,fixture.grant.epoch)
        with self.assertRaises(Conflict):witness.require(current,digest)
        witness.advance(old_state,current,digest,approved=True)
        with self.assertRaises(Conflict):witness.require(old_state,digest)
        recovered_keys = open_keys(path,self.unlock,lineage=current.anchor.lineage,trusted_digest=witness.head(current.anchor.lineage)[1],
            synthetic_only=True,approved=True)
        destination = self.home/'surviving-authority';destination.mkdir();(destination/'objects').mkdir()
        with closing(sqlite3.connect(fixture.a._repository.catalog)) as source:
            with closing(sqlite3.connect(destination/'catalog.sqlite')) as target:source.backup(target)
            object_id = source.execute('SELECT object_id FROM latest').fetchone()[0]
        folder = destination/'objects'/object_id;folder.mkdir()
        for name in ('backup.enc','checkpoint.enc'):shutil.copyfile(fixture.a._repository.path/'objects'/object_id/name,folder/name)
        recovered = SyntheticAuthority(destination,synthetic_only=True,storage_key=recovered_keys.storage_key,
            recovery=SyntheticRecovery(recovered_keys.recovery_key,synthetic_only=True,clock=lambda:fixture.now),clock=lambda:fixture.now)
        head = recovered.head(current.anchor.lineage)
        witness.require(WitnessState(head['anchor'],head['writer_epoch']),digest)
        restored = recovered.restore(current.anchor.lineage,self.home/'restored.sqlite',expected_anchor=current.anchor,approved=True)
        self.assertEqual(restored['result']['suppressed_deleted'],1)
        with self.assertRaises(Conflict):recovered.restore(current.anchor.lineage,self.home/'old.sqlite',expected_anchor=old_state.anchor,approved=True)


if __name__=='__main__':unittest.main()
