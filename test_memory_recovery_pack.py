"""Fake encrypted transfer/restore, generated keys, temporary paths and fresh children."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from brain import memory_recovery_pack as pack
from brain.memory_custody import RecoveryKeys, SyntheticWitness, WitnessState, seal_keys
from brain.memory_recovery import SyntheticRecovery
import test_qualification as portable

EVIDENCE={}


WORKER=r'''
import json,pathlib,sys,threading,time
p=json.load(sys.stdin);sys.path[:0]=p['imports']
from brain.memory_recovery_pack import RecoveryPins,restore_pack
from brain.memory_custody import WitnessState
from brain.memory_recovery import CheckpointAnchor
from brain.memory_prototype import SyntheticMemory
from brain.conversation import Context,PublicTurn
assert not pathlib.Path(p['lost_source']).exists()
state=WitnessState(CheckpointAnchor(**p['pins']['state']['anchor']),p['pins']['state']['writer_epoch'])
pins=RecoveryPins(state,p['pins']['keys_digest'],p['pins']['backup_sha256'])
out=restore_pack(p['pack'],p['destination'],pins=pins,unlock_key=p['unlock'].encode(),
                 synthetic_only=True,approved=True,clock=lambda:p['now'])
assert out['quarantined'] and out['active_bindings']==0 and out['resumed_jobs']==0
# Reopen with the separately supplied fake storage key only to inspect the quarantined result.
memory=SyntheticMemory(p['destination'],synthetic_only=True,encryption_key=bytes.fromhex(p['storage_key']),clock=lambda:p['now'])
with memory._db() as db:
    assert db.execute('SELECT COUNT(*) FROM bindings WHERE active=1').fetchone()[0]==0
    assert db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]==0
    rows={row['id']:dict(row) for row in db.execute('SELECT * FROM memories')}
    assert json.loads(rows[p['kept']]['value'])=={'text':'SYNTHETIC_PACK_CORRECTION'}
    assert rows[p['kept']]['revision']==2
    for mid in (p['forgotten'],p['expired']):assert rows[mid]['deleted']==1 and rows[mid]['value'] is None
    for term in ('SYNTHETIC_PACK_FORGOTTEN','SYNTHETIC_PACK_EXPIRED'):
        assert db.execute('SELECT COUNT(*) FROM memory_search WHERE memory_search MATCH ?',(term,)).fetchone()[0]==0
context=Context('1'*64,'phone','2'*64,'1'*64,p['now']+300,True)
turn=PublicTurn('3'*32,'SYNTHETIC_PACK_READ',context,time.monotonic()+30,lambda:context,lambda:p['now'],threading.Event())
try:memory.handle(turn,dict(op='get',project='alpha',id=p['kept']),approved=True)
except PermissionError:pass
else:raise AssertionError('Restored quarantine granted an old binding access')
blob=pathlib.Path(p['destination']).read_bytes()
assert not blob.startswith(b'SQLite format 3') and b'SYNTHETIC_PACK_CORRECTION' not in blob
print(json.dumps({'recovered':True,'quarantined':True,'correction_preserved':True,'forgotten_absent':True,
                  'expired_absent':True,'old_binding_denied':True,'active_bindings':0,'resumed_jobs':0}))
'''


class RecoveryPackChecks(unittest.TestCase):
    def setUp(self):
        self.f=portable.StorageChecks(methodName='runTest');self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.key=SyntheticRecovery.new_key()
        self.f.recovery=SyntheticRecovery(self.key,synthetic_only=True,clock=lambda:self.f.now)
        self.kept=self.f.call(self.f.packet('kept'))
        p=self.f.packet('forgotten');p['value']={'text':'SYNTHETIC_PACK_FORGOTTEN'};self.forgotten=self.f.call(p)
        p=self.f.packet('expired');p['value']={'text':'SYNTHETIC_PACK_EXPIRED'}
        p['retention']={'mode':'until','expires_at':self.f.now+1};self.expired=self.f.call(p)
        self.f.authority();self.unlock=Fernet.generate_key();self.capsule=self.f.home/'keys.enc'
        self.keys_digest=seal_keys(self.capsule,self.unlock,RecoveryKeys(self.f.anchor.lineage,self.f.key,self.key),
                                   synthetic_only=True,approved=True)
        self.witness=SyntheticWitness.create(self.f.home/'witness.sqlite',synthetic_only=True,approved=True)
        self.state=WitnessState(self.f.anchor,self.f.grant.epoch)
        self.witness.register(self.state,self.keys_digest,approved=True)

    def pins(self):
        state,digest=self.witness.head(self.f.anchor.lineage)
        with self.f.a._repository._db() as db:
            row=dict(db.execute('SELECT * FROM latest WHERE lineage=?',(state.anchor.lineage,)).fetchone())
        self.assertEqual((row['sequence'],row['sha256']),(state.anchor.sequence,state.anchor.sha256))
        return pack.RecoveryPins(state,digest,row['backup_sha256']),self.f.a._repository.path/'objects'/row['object_id']

    def stage(self,destination,**kwargs):
        pins,folder=self.pins()
        values=dict(backup=folder/'backup.enc',checkpoint=folder/'checkpoint.enc',capsule=self.capsule,
                    pins=pins,unlock_key=self.unlock,synthetic_only=True,approved=True)
        values.update(kwargs);return pack.stage_pack(destination,**values)

    def latest(self):
        self.f.request(dict(op='correct',project='alpha',request_id=self.f.packet()['request_id'],
            id=self.kept['id'],expected_revision=1,value={'text':'SYNTHETIC_PACK_CORRECTION'}))
        self.f.request(dict(op='forget',project='alpha',request_id=self.f.packet()['request_id'],
            id=self.forgotten['id'],expected_revision=1))
        self.f.now+=2
        target=WitnessState(self.f.anchor,self.f.grant.epoch)
        self.witness.advance(self.state,target,self.keys_digest,approved=True);self.state=target

    def test_three_encrypted_files_roundtrip_without_plaintext_keys_or_records(self):
        destination=self.f.home/'pack';result=self.stage(destination)
        self.assertEqual({p.name for p in destination.iterdir()},set(pack.NAMES))
        pins,_=self.pins();self.assertEqual(result,pack.inspect_pack(destination,pins=pins,unlock_key=self.unlock,
            synthetic_only=True,approved=True))
        for name in pack.NAMES:
            data=(destination/name).read_bytes()
            for marker in (self.unlock,self.key,self.f.key,self.f.key.hex().encode(),b'SYNTHETIC_LINUX_VALUE',b'SYNTHETIC_PACK_FORGOTTEN'):
                self.assertNotIn(marker,data)

    def test_fresh_process_restores_after_source_catalogue_and_witness_are_lost(self):
        import tempfile
        self.latest();pins,_=self.pins()
        with tempfile.TemporaryDirectory(prefix='fake-pack-destination-') as folder:
            target=Path(folder);self.stage(target/'pack')
            imports=[str(Path(__file__).resolve().parent)]
            if sys.platform=='win32':imports.append(str(Path(__file__).resolve().parent/'review/2026-10-12-memory-hardening/.drivers'))
            packet=dict(imports=imports,lost_source=str(self.f.home),pack=str(target/'pack'),destination=str(target/'restored.sqlite'),
                        pins=asdict(pins),unlock=self.unlock.decode(),storage_key=self.f.key.hex(),now=self.f.now,
                        kept=self.kept['id'],forgotten=self.forgotten['id'],expired=self.expired['id'])
            self.f.doCleanups();self.assertFalse(Path(packet['lost_source']).exists())
            result=subprocess.run([sys.executable,'-I','-B','-c',WORKER],input=json.dumps(packet),capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,'Fresh fake-data restore failed: '+result.stderr[-1800:])
            report=json.loads(result.stdout);self.assertTrue(report['recovered']);self.assertTrue(report['old_binding_denied'])
            EVIDENCE.update(report)

    def test_exact_opt_in_and_approval_are_required_before_io(self):
        for values in ({'approved':False},{'approved':1},{'synthetic_only':False},{'synthetic_only':1}):
            with self.subTest(values=values),self.assertRaises(PermissionError):self.stage(self.f.home/'refused',**values)
            self.assertFalse((self.f.home/'refused').exists())

    def test_missing_corrupt_and_extra_artifacts_refuse_without_restore_output(self):
        folder=self.f.home/'pack';self.stage(folder);pins,_=self.pins()
        for name in pack.NAMES:
            path=folder/name;original=path.read_bytes()
            for kind in ('missing','corrupt'):
                with self.subTest(name=name,kind=kind):
                    if kind=='missing':path.unlink()
                    else:path.write_bytes(original[:-1]+bytes([original[-1]^1]))
                    with self.assertRaises((ValueError,OSError)):
                        pack.restore_pack(folder,self.f.home/'refused.sqlite',pins=pins,unlock_key=self.unlock,
                                          synthetic_only=True,approved=True)
                    self.assertFalse((self.f.home/'refused.sqlite').exists());path.write_bytes(original)
        (folder/'plaintext-key.txt').write_text('FAKE_UNACCEPTABLE_EXTRA_FILE')
        with self.assertRaises(ValueError):pack.inspect_pack(folder,pins=pins,unlock_key=self.unlock,synthetic_only=True,approved=True)

    def test_stale_pack_is_rejected_against_new_independent_pins(self):
        folder=self.f.home/'old-pack';self.stage(folder);self.latest();pins,_=self.pins()
        with self.assertRaises(ValueError):pack.restore_pack(folder,self.f.home/'refused.sqlite',pins=pins,
            unlock_key=self.unlock,synthetic_only=True,approved=True)
        self.assertFalse((self.f.home/'refused.sqlite').exists())

    def test_older_authenticated_snapshot_cannot_be_staged_as_complete_latest_pack(self):
        _,old=self.pins();self.latest();pins,current=self.pins()
        mixed=pack.RecoveryPins(pins.state,pins.keys_digest,hashlib.sha256((old/'backup.enc').read_bytes()).hexdigest())
        with self.assertRaises(ValueError):pack.stage_pack(self.f.home/'mixed',backup=old/'backup.enc',
            checkpoint=current/'checkpoint.enc',capsule=self.capsule,pins=mixed,unlock_key=self.unlock,
            synthetic_only=True,approved=True)
        self.assertFalse((self.f.home/'mixed').exists())

    def test_wrong_unlock_missing_pins_and_replaced_capsule_are_rejected(self):
        folder=self.f.home/'pack';self.stage(folder);pins,_=self.pins()
        for values in ({'unlock_key':Fernet.generate_key()},{'pins':None}):
            kwargs=dict(pins=pins,unlock_key=self.unlock);kwargs.update(values)
            with self.assertRaises(ValueError):pack.inspect_pack(folder,**kwargs,synthetic_only=True,approved=True)
        replacement=self.f.home/'replacement.enc'
        seal_keys(replacement,self.unlock,RecoveryKeys(self.f.anchor.lineage,self.f.key,self.key),synthetic_only=True,approved=True)
        (folder/'keys.enc').write_bytes(replacement.read_bytes())
        with self.assertRaises(ValueError):pack.inspect_pack(folder,pins=pins,unlock_key=self.unlock,synthetic_only=True,approved=True)

    def test_interrupted_copy_has_no_acknowledgement_and_cannot_be_overwritten(self):
        folder=self.f.home/'partial';original=pack._publish
        def failed(path,writer,cancelled):
            if Path(path).name=='checkpoint.enc':raise OSError('Synthetic interrupted copy')
            return original(path,writer,cancelled)
        with patch.object(pack,'_publish',side_effect=failed),self.assertRaises(OSError):self.stage(folder)
        self.assertEqual({p.name for p in folder.iterdir()},{'backup.enc'});pins,_=self.pins()
        with self.assertRaises(ValueError):pack.inspect_pack(folder,pins=pins,unlock_key=self.unlock,synthetic_only=True,approved=True)
        before=(folder/'backup.enc').read_bytes()
        with self.assertRaises(FileExistsError):self.stage(folder)
        self.assertEqual((folder/'backup.enc').read_bytes(),before);self.assertTrue(self.stage(self.f.home/'new-pack')['verified'])

    def test_cancellation_during_copy_never_returns_a_transfer_acknowledgement(self):
        stopped=[False];original=pack._publish
        def cancel_after_first(path,writer,cancelled):
            result=original(path,writer,cancelled);stopped[0]=True;return result
        folder=self.f.home/'cancelled'
        with patch.object(pack,'_publish',side_effect=cancel_after_first),self.assertRaises(InterruptedError):
            self.stage(folder,cancelled=lambda:stopped[0])
        self.assertEqual({p.name for p in folder.iterdir()},{'backup.enc'})
        with self.assertRaises(InterruptedError):self.stage(self.f.home/'not-created',cancelled=lambda:True)
        self.assertFalse((self.f.home/'not-created').exists())

    def test_oversized_pack_and_existing_restore_target_are_preserved(self):
        folder=self.f.home/'pack';self.stage(folder);pins,_=self.pins();target=self.f.home/'existing.sqlite'
        target.write_bytes(b'FAKE_EXISTING_DO_NOT_REPLACE')
        with self.assertRaises(FileExistsError):pack.restore_pack(folder,target,pins=pins,unlock_key=self.unlock,
            synthetic_only=True,approved=True,clock=lambda:self.f.now)
        self.assertEqual(target.read_bytes(),b'FAKE_EXISTING_DO_NOT_REPLACE')
        with (folder/'backup.enc').open('r+b') as output:output.truncate(pack.MAX_PACK_BYTES+1)
        with self.assertRaises(ValueError):pack.inspect_pack(folder,pins=pins,unlock_key=self.unlock,synthetic_only=True,approved=True)


if __name__=='__main__':unittest.main()
