"""Fake-only latest-state/crash/replay checks; temporary stores and no network."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict,replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from brain import memory_recovery_latest as latest
from brain import memory_recovery_pack as pack
from brain.memory_custody import WitnessState
from brain.memory_prototype import Conflict
from brain.memory_recovery import CheckpointAnchor
from brain.memory_recovery_trust import seal_trust
from test_memory_recovery_pack import RecoveryPackChecks

EVIDENCE={}
CRASH=r'''
import json,os,sys
from contextlib import contextmanager
from unittest.mock import patch
p=json.load(sys.stdin);sys.path[:0]=p['imports']
from brain import memory_recovery_latest as latest
store=latest.SyntheticRecoveryLatest(p['store'],synthetic_only=True)
old=latest._decode(json.dumps(p['previous']));new=latest._decode(json.dumps(p['candidate']))
original=store._db
@contextmanager
def interrupted():
    with original() as db:
        yield db
        if p['boundary']=='before':os._exit(71)
    os._exit(72)
with patch.object(store,'_db',interrupted),patch.object(latest,'open_trust',return_value=new.pins),patch.object(latest,'inspect_pack'):
    if p['action']=='begin':store.begin(old,new,approved=True)
    else:store.finish(new,'unused-fake-pack','unused-fake-trust',b'FAKE_UNUSED',approved=True)
raise AssertionError('Expected synchronized fake process exit')
'''
RESTORE=r'''
import io,json,pathlib,sys
from dataclasses import asdict
from unittest.mock import patch
p=json.load(sys.stdin);sys.path[:0]=p['imports']
assert 'pins' not in p and 'storage_key' not in p and 'trust_digest' not in p
from brain.memory_recovery_latest import SyntheticRecoveryLatest
from brain.memory_custody import open_keys
from test_memory_recovery_pack import WORKER
store=SyntheticRecoveryLatest(p.pop('latest_store'),synthetic_only=True)
lineage=p.pop('lineage');head=store.head(lineage);trust=p.pop('trust')
keys=open_keys(pathlib.Path(p['pack'])/'keys.enc',p['unlock'].encode(),lineage=lineage,
    trusted_digest=head.pins.keys_digest,synthetic_only=True,approved=True)
p['pins']=asdict(head.pins);p['storage_key']=keys.storage_key.hex()
def gated_restore(folder,destination,**kwargs):
    return store.restore(lineage,folder,trust,destination,kwargs['unlock_key'],approved=True,clock=kwargs['clock'])
sys.stdin=io.StringIO(json.dumps(p))
# Reuse record/search/encryption/old-binding assertions; the actual restore goes through the latest-store gate.
with patch('brain.memory_recovery_pack.restore_pack',side_effect=gated_restore):exec(WORKER)
'''


class LatestRecoveryChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='fake-latest-');self.addCleanup(temp.cleanup);self.home=Path(temp.name)
        self.path=self.home/'separate-latest.sqlite'
        self.store=latest.SyntheticRecoveryLatest.create(self.path,synthetic_only=True,approved=True)
        pins=pack.RecoveryPins(WitnessState(CheckpointAnchor('1'*32,4,'2'*32,'3'*64),7),'4'*64,'5'*64)
        self.old=latest.RecoveryHead(pins,'6'*64)
        new=pack.RecoveryPins(WitnessState(CheckpointAnchor('1'*32,5,'7'*32,'8'*64),8),'4'*64,'9'*64)
        self.new=latest.RecoveryHead(new,'a'*64);self.lineage=pins.state.anchor.lineage

    def finish_metadata(self,store,head,**kw):
        with patch.object(latest,'open_trust',return_value=head.pins),patch.object(latest,'inspect_pack'):
            return store.finish(head,'unused-fake-pack','unused-fake-trust',b'FAKE_UNUSED',approved=True,**kw)

    def bootstrap(self,store=None):
        store=store or self.store;store.begin(None,self.old,approved=True);self.finish_metadata(store,self.old)

    def inputs(self):
        f=RecoveryPackChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp()
        old_pins,_=f.pins();old_pack=self.home/'old-pack';f.stage(old_pack);old_trust=self.home/'old-trust.enc'
        old_digest=seal_trust(old_trust,old_pins,f.unlock,synthetic_only=True,approved=True)
        old=latest.RecoveryHead(old_pins,old_digest)
        self.store.begin(None,old,approved=True);self.store.finish(old,old_pack,old_trust,f.unlock,approved=True)
        f.latest();pins,_=f.pins();trust=self.home/'current-trust.enc'
        digest=seal_trust(trust,pins,f.unlock,synthetic_only=True,approved=True)
        return f,old,old_pack,old_trust,latest.RecoveryHead(pins,digest),trust

    def test_pending_restart_exact_retry_and_confirmed_reply_loss(self):
        self.bootstrap();self.store.begin(self.old,self.new,approved=True)
        reopened=latest.SyntheticRecoveryLatest(self.path,synthetic_only=True)
        with self.assertRaises(Conflict):reopened.head(self.lineage)
        self.assertEqual(reopened.begin(self.old,self.new,approved=True),self.new)
        self.assertEqual(self.finish_metadata(reopened,self.new),self.new)
        self.assertEqual(reopened.head(self.lineage),self.new)
        self.assertEqual(reopened.begin(self.old,self.new,approved=True),self.new)
        self.assertEqual(self.finish_metadata(reopened,self.new),self.new)
        with self.assertRaises(Conflict):reopened.begin(None,self.old,approved=True)

    def test_approval_validation_missing_and_corrupt_store_do_not_bootstrap(self):
        for flag in (False,1):
            with self.assertRaises(PermissionError):self.store.begin(None,self.old,approved=flag)
            with self.assertRaises(PermissionError):self.store.finish(self.old,'x','y',b'FAKE',approved=flag)
            with self.assertRaises(PermissionError):self.store.restore(self.lineage,'x','y',self.home/'out',b'FAKE',approved=flag)
        with self.assertRaises(ValueError):self.store.begin(None,None,approved=True)
        with self.assertRaises(ValueError):self.store.head(self.lineage)
        missing=self.home/'missing.sqlite'
        with self.assertRaises(sqlite3.DatabaseError):latest.SyntheticRecoveryLatest(missing,synthetic_only=True)
        self.assertFalse(missing.exists())
        bad=self.home/'bad.sqlite';bad.write_bytes(b'FAKE_KEEP')
        with self.assertRaises((sqlite3.DatabaseError,ValueError)):latest.SyntheticRecoveryLatest(bad,synthetic_only=True)
        self.assertEqual(bad.read_bytes(),b'FAKE_KEEP')
        with self.assertRaises(FileExistsError):latest.SyntheticRecoveryLatest.create(self.path,synthetic_only=True,approved=True)

    def test_rollback_divergence_key_rotation_and_stale_compare_are_refused(self):
        self.bootstrap()
        bad=[self.old,replace(self.new,pins=replace(self.new.pins,keys_digest='b'*64)),
            replace(self.new,pins=replace(self.new.pins,state=replace(self.new.pins.state,writer_epoch=6))),
            replace(self.old,trust_digest='c'*64),
            replace(self.old,pins=replace(self.old.pins,state=replace(self.old.pins.state,writer_epoch=8,
                anchor=replace(self.old.pins.state.anchor,sha256='d'*64)))),
            replace(self.old,pins=replace(self.old.pins,state=replace(self.old.pins.state,writer_epoch=8),backup_sha256='e'*64))]
        for candidate in bad:
            with self.subTest(candidate=candidate),self.assertRaises(Conflict):self.store.begin(self.old,candidate,approved=True)
            self.assertEqual(self.store.head(self.lineage),self.old)
        self.store.begin(self.old,self.new,approved=True);self.finish_metadata(self.store,self.new)
        with self.assertRaises(Conflict):self.store.begin(self.new,self.old,approved=True)
        with self.assertRaises(Conflict):self.store.begin(self.old,replace(self.new,trust_digest='f'*64),approved=True)
        epoch_store=latest.SyntheticRecoveryLatest.create(self.home/'epoch-only.sqlite',synthetic_only=True,approved=True)
        self.bootstrap(epoch_store)
        epoch_head=replace(self.old,pins=replace(self.old.pins,state=replace(self.old.pins.state,writer_epoch=8)),trust_digest='e'*64)
        epoch_store.begin(self.old,epoch_head,approved=True);self.finish_metadata(epoch_store,epoch_head)
        self.assertEqual(epoch_store.head(self.lineage),epoch_head)

    def test_competing_publications_have_one_pending_winner(self):
        self.bootstrap();other=replace(self.new,trust_digest='b'*64)
        def begin(candidate):
            try:self.store.begin(self.old,candidate,approved=True);return candidate
            except Conflict:return None
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(begin,(self.new,other)))
        winners=[value for value in results if value is not None];self.assertEqual(len(winners),1)
        with self.assertRaises(Conflict):self.store.head(self.lineage)
        self.finish_metadata(self.store,winners[0]);self.assertEqual(self.store.head(self.lineage),winners[0])

    def test_cancel_or_failed_verification_preserves_pending_and_refuses_restore(self):
        self.bootstrap()
        with self.assertRaises(InterruptedError):self.store.begin(self.old,self.new,approved=True,cancelled=lambda:True)
        self.assertEqual(self.store.head(self.lineage),self.old);self.store.begin(self.old,self.new,approved=True)
        with patch.object(latest,'open_trust',side_effect=ValueError('FAKE bad trust')),self.assertRaises(ValueError):
            self.store.finish(self.new,'x','y',b'FAKE',approved=True)
        stopped=[False]
        def stop(*args,**kwargs):stopped[0]=True
        with patch.object(latest,'open_trust',return_value=self.new.pins),patch.object(latest,'inspect_pack',side_effect=stop),self.assertRaises(InterruptedError):
            self.store.finish(self.new,'x','y',b'FAKE',approved=True,cancelled=lambda:stopped[0])
        with self.assertRaises(Conflict):self.store.restore(self.lineage,'x','y',self.home/'out',b'FAKE',approved=True)
        self.assertFalse((self.home/'out').exists());self.finish_metadata(self.store,self.new)

    def test_process_exit_before_and_after_begin_and_finish_commits(self):
        imports=[str(Path(__file__).resolve().parent)]
        for action in ('begin','finish'):
            for boundary in ('before','after'):
                path=self.home/(action+'-'+boundary+'.sqlite')
                store=latest.SyntheticRecoveryLatest.create(path,synthetic_only=True,approved=True);self.bootstrap(store)
                if action=='finish':store.begin(self.old,self.new,approved=True)
                packet=dict(imports=imports,store=str(path),previous=asdict(self.old),candidate=asdict(self.new),action=action,boundary=boundary)
                run=subprocess.run([sys.executable,'-I','-B','-c',CRASH],input=json.dumps(packet),capture_output=True,text=True,timeout=20,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertEqual(run.returncode,71 if boundary=='before' else 72,'Fake crash boundary failed; raw output withheld.')
                reopened=latest.SyntheticRecoveryLatest(path,synthetic_only=True)
                if action=='begin' and boundary=='before':self.assertEqual(reopened.head(self.lineage),self.old)
                elif action=='finish' and boundary=='after':self.assertEqual(reopened.head(self.lineage),self.new)
                else:
                    with self.assertRaises(Conflict):reopened.head(self.lineage)
                reopened.begin(self.old,self.new,approved=True);self.finish_metadata(reopened,self.new)
                self.assertEqual(reopened.head(self.lineage),self.new)

    def test_partial_copy_stays_pending_across_restart_until_exact_completion(self):
        f,old,old_pack,old_trust,new,trust=self.inputs();self.store.begin(old,new,approved=True)
        original=pack._publish
        def fail(path,writer,cancelled):
            if Path(path).name=='checkpoint.enc':raise OSError('FAKE interrupted copy')
            return original(path,writer,cancelled)
        partial=self.home/'partial'
        with patch.object(pack,'_publish',side_effect=fail),self.assertRaises(OSError):f.stage(partial)
        reopened=latest.SyntheticRecoveryLatest(self.path,synthetic_only=True)
        with self.assertRaises(ValueError):reopened.finish(new,partial,trust,f.unlock,approved=True)
        for folder,record in ((old_pack,old_trust),(partial,trust)):
            with self.assertRaises(Conflict):reopened.restore(new.pins.state.anchor.lineage,folder,record,self.home/'out',f.unlock,approved=True)
        self.assertFalse((self.home/'out').exists());complete=self.home/'complete';f.stage(complete)
        reopened.begin(old,new,approved=True);reopened.finish(new,complete,trust,f.unlock,approved=True)
        self.assertEqual(reopened.head(new.pins.state.anchor.lineage),new)

    def test_rolling_back_pack_and_trust_together_cannot_change_separate_latest(self):
        f,old,old_pack,old_trust,new,trust=self.inputs();current=self.home/'current';f.stage(current)
        self.store.begin(old,new,approved=True);self.store.finish(new,current,trust,f.unlock,approved=True)
        lineage=new.pins.state.anchor.lineage
        for folder,record in ((old_pack,old_trust),(old_pack,trust),(current,old_trust)):
            with self.assertRaises(ValueError):self.store.restore(lineage,folder,record,self.home/'refused',f.unlock,approved=True,clock=lambda:f.f.now)
            self.assertFalse((self.home/'refused').exists());self.assertEqual(self.store.head(lineage),new)
        result=self.store.restore(lineage,current,trust,self.home/'restored',f.unlock,approved=True,clock=lambda:f.f.now)
        self.assertTrue(result['quarantined']);self.assertEqual((result['active_bindings'],result['resumed_jobs']),(0,0))

    def test_fresh_process_uses_surviving_latest_store_after_source_loss(self):
        f,old,old_pack,old_trust,new,trust=self.inputs();current=self.home/'current';f.stage(current)
        self.store.begin(old,new,approved=True);self.store.finish(new,current,trust,f.unlock,approved=True)
        root=Path(__file__).resolve().parent;imports=[str(root),str(root/'review/2026-10-13-memory-linux')]
        if sys.platform=='win32':imports.append(str(root/'review/2026-10-12-memory-hardening/.drivers'))
        packet=dict(imports=imports,latest_store=str(self.path),lineage=new.pins.state.anchor.lineage,trust=str(trust),
            lost_source=str(f.f.home),pack=str(current),destination=str(self.home/'restored.sqlite'),unlock=f.unlock.decode(),
            now=f.f.now,kept=f.kept['id'],forgotten=f.forgotten['id'],expired=f.expired['id'])
        f.doCleanups();self.assertFalse(Path(packet['lost_source']).exists())
        run=subprocess.run([sys.executable,'-I','-B','-c',RESTORE],input=json.dumps(packet),capture_output=True,text=True,timeout=30,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(run.returncode,0,'Fresh latest-gated fake restore failed; raw output withheld.')
        result=json.loads(run.stdout);self.assertTrue(result['recovered']);self.assertTrue(result['old_binding_denied']);EVIDENCE.update(result)


if __name__=='__main__':unittest.main()
