"""Generated fake keys/temp stores only; no vault, DPAPI, provider or network use."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from brain import memory_recovery_trust as trust
from brain import memory_recovery_pack as pack
from brain.memory_custody import WitnessState
from brain.memory_recovery import CheckpointAnchor
from test_memory_recovery_pack import RecoveryPackChecks

EVIDENCE={}
WORKER=r'''
import io,json,pathlib,sys
p=json.load(sys.stdin);sys.path[:0]=p['imports']
assert 'pins' not in p and 'storage_key' not in p
assert not pathlib.Path(p['lost_source']).exists()
from brain.memory_recovery_trust import open_trust
from brain.memory_custody import open_keys
from test_memory_recovery_pack import WORKER
from dataclasses import asdict
pins=open_trust(p.pop('trust'),p['unlock'].encode(),trusted_digest=p.pop('trust_digest'),synthetic_only=True,approved=True)
keys=open_keys(pathlib.Path(p['pack'])/'keys.enc',p['unlock'].encode(),lineage=pins.state.anchor.lineage,
               trusted_digest=pins.keys_digest,synthetic_only=True,approved=True)
p['pins']=asdict(pins);p['storage_key']=keys.storage_key.hex()
sys.stdin=io.StringIO(json.dumps(p))
exec(WORKER)
'''


class RecoveryTrustChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='fake-trust-');self.addCleanup(temp.cleanup)
        self.home=Path(temp.name);self.key=Fernet.generate_key();self.path=self.home/'trust.enc'
        self.pins=pack.RecoveryPins(WitnessState(CheckpointAnchor('1'*32,4,'2'*32,'3'*64),7),'4'*64,'5'*64)

    def seal(self,**values):
        args=dict(synthetic_only=True,approved=True);args.update(values)
        return trust.seal_trust(self.path,self.pins,self.key,**args)

    def read(self,digest,**values):
        args=dict(trusted_digest=digest,synthetic_only=True,approved=True);args.update(values)
        return trust.open_trust(self.path,self.key,**args)

    def fixture(self):
        fixture=RecoveryPackChecks(methodName='runTest');self.addCleanup(fixture.doCleanups);fixture.setUp()
        return fixture

    def test_encrypted_pins_roundtrip_contains_no_unlock_or_plaintext_pins(self):
        digest=self.seal();self.assertEqual(self.read(digest),self.pins)
        blob=self.path.read_bytes();self.assertLessEqual(len(blob),trust.MAX_BYTES)
        for marker in (self.key,self.pins.backup_sha256.encode(),self.pins.state.anchor.lineage.encode()):
            self.assertNotIn(marker,blob)
        raw=Fernet(self.key).decrypt(blob[len(trust.MAGIC):])
        self.assertEqual(json.loads(raw),{'version':1,'pins':asdict(self.pins)})

    def test_exact_approval_cancellation_and_pins_validation_precede_io(self):
        for values in ({'approved':False},{'approved':1},{'synthetic_only':False},{'synthetic_only':1}):
            with self.subTest(values=values),patch.object(trust,'_publish') as publish,patch.object(trust,'_blob') as blob:
                with self.assertRaises(PermissionError):self.seal(**values)
                with self.assertRaises(PermissionError):self.read('0'*64,**values)
                publish.assert_not_called();blob.assert_not_called()
        with self.assertRaises(InterruptedError):self.seal(cancelled=lambda:True)
        with self.assertRaises(InterruptedError):self.read('0'*64,cancelled=lambda:True)
        with self.assertRaises(ValueError):trust.seal_trust(self.path,None,self.key,synthetic_only=True,approved=True)
        self.assertFalse(self.path.exists())

    def test_missing_wrong_trust_wrong_unlock_corruption_and_limits_are_refused(self):
        digest=self.seal();original=self.path.read_bytes()
        for value in (None,'','0'*64):
            with self.subTest(value=value),self.assertRaises(ValueError):self.read(value)
        with self.assertRaises(ValueError):trust.open_trust(self.path,Fernet.generate_key(),trusted_digest=digest,synthetic_only=True,approved=True)
        self.path.write_bytes(original+b'x')
        with self.assertRaises(ValueError):self.read(digest)
        damaged=bytearray(original);damaged[len(damaged)//2]^=1
        for blob in (original[:-1],bytes(damaged),b'wrong',trust.MAGIC+b'x'*(trust.MAX_BYTES+1)):
            self.path.write_bytes(blob)
            with self.assertRaises(ValueError):self.read(hashlib.sha256(blob).hexdigest())
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):self.read(digest)

    def test_authenticated_duplicate_unknown_and_invalid_schema_is_refused(self):
        good={'version':1,'pins':asdict(self.pins)}
        values=[{},dict(good,version=True),dict(good,version=2),dict(good,secret='FAKE_PRIVATE'),dict(good,pins=[])]
        for fields in ({'extra':'FAKE_PRIVATE'},{'state':None},{'keys_digest':'bad'},
                       {'state':dict(good['pins']['state'],writer_epoch=True)},
                       {'state':dict(good['pins']['state'],anchor={})}):
            values.append(dict(good,pins=dict(good['pins'],**fields)))
        payloads=[json.dumps(value).encode() for value in values]+[b'{"version":1,"version":1,"pins":{}}',b'not json']
        for raw in payloads:
            blob=trust.MAGIC+Fernet(self.key).encrypt(raw);self.path.write_bytes(blob)
            with self.subTest(raw=raw),self.assertRaises(ValueError) as error:self.read(hashlib.sha256(blob).hexdigest())
            self.assertNotIn('FAKE_PRIVATE',str(error.exception))

    def test_existing_destination_and_interrupted_publication_are_preserved(self):
        self.path.write_bytes(b'FAKE_KEEP')
        with self.assertRaises(FileExistsError):self.seal()
        self.assertEqual(self.path.read_bytes(),b'FAKE_KEEP');self.path.unlink()
        def interrupted(path,writer,cancelled):
            stage=self.home/'fake-stage';writer(stage);raise OSError('FAKE interrupted publication')
        with patch.object(trust,'_publish',side_effect=interrupted),self.assertRaises(OSError):self.seal()
        self.assertFalse(self.path.exists())
        digest=self.seal();self.assertEqual(self.read(digest),self.pins)
        with patch.object(trust,'_blob',return_value=b'changed'),self.assertRaises(ValueError):
            trust.seal_trust(self.home/'refused.enc',self.pins,self.key,synthetic_only=True,approved=True)
        self.assertFalse((self.home/'refused.enc').exists())

    def test_old_authenticated_record_and_old_pack_refuse_against_current_trust(self):
        f=self.fixture();old_pins,_=f.pins();f.stage(self.home/'old-pack')
        old=self.home/'old-trust.enc'
        old_digest=trust.seal_trust(old,old_pins,f.unlock,synthetic_only=True,approved=True)
        f.latest();current,_=f.pins()
        digest=trust.seal_trust(self.path,current,f.unlock,synthetic_only=True,approved=True)
        with self.assertRaises(ValueError):trust.open_trust(old,f.unlock,trusted_digest=digest,synthetic_only=True,approved=True)
        pins=trust.open_trust(self.path,f.unlock,trusted_digest=digest,synthetic_only=True,approved=True)
        with self.assertRaises(ValueError):pack.restore_pack(self.home/'old-pack',self.home/'refused.sqlite',
            pins=pins,unlock_key=f.unlock,synthetic_only=True,approved=True,clock=lambda:f.f.now)
        self.assertFalse((self.home/'refused.sqlite').exists())
        # shortcut: a rolled-back trusted digest cannot be detected locally; independent latest-state custody is still required.
        self.assertEqual(trust.open_trust(old,f.unlock,trusted_digest=old_digest,synthetic_only=True,approved=True),old_pins)

    def test_fresh_process_recovers_from_separate_inputs_after_source_loss(self):
        f=self.fixture();f.latest();pins,_=f.pins()
        cloud=self.home/'fake-cloud';cloud.mkdir();f.stage(cloud/'pack')
        offline=self.home/'fake-offline';offline.mkdir();record=offline/'trust.enc'
        digest=trust.seal_trust(record,pins,f.unlock,synthetic_only=True,approved=True)
        imports=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parent/'review/2026-10-13-memory-linux')]
        if sys.platform=='win32':imports.append(str(Path(__file__).resolve().parent/'review/2026-10-12-memory-hardening/.drivers'))
        packet=dict(imports=imports,lost_source=str(f.f.home),pack=str(cloud/'pack'),destination=str(self.home/'restored.sqlite'),
            trust=str(record),trust_digest=digest,unlock=f.unlock.decode(),now=f.f.now,
            kept=f.kept['id'],forgotten=f.forgotten['id'],expired=f.expired['id'])
        f.doCleanups();self.assertFalse(Path(packet['lost_source']).exists())
        run=subprocess.run([sys.executable,'-I','-B','-c',WORKER],input=json.dumps(packet),capture_output=True,text=True,timeout=30,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(run.returncode,0,'Fresh fake trust restore failed; raw output withheld.')
        result=json.loads(run.stdout)
        self.assertTrue(all(result[key] for key in ('recovered','quarantined','correction_preserved','forgotten_absent','expired_absent','old_binding_denied')))
        self.assertEqual((result['active_bindings'],result['resumed_jobs']),(0,0));EVIDENCE.update(result)

    def test_trust_record_does_not_become_a_fourth_pack_artifact(self):
        f=self.fixture();pins,_=f.pins();folder=self.home/'pack';f.stage(folder)
        trust.seal_trust(folder/'trust.enc',pins,f.unlock,synthetic_only=True,approved=True)
        with self.assertRaises(ValueError):pack.inspect_pack(folder,pins=pins,unlock_key=f.unlock,synthetic_only=True,approved=True)


if __name__=='__main__':unittest.main()
