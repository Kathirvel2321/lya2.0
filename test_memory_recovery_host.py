"""Cold fake recovery from a reviewed code archive; no working-project child imports."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from cryptography.fernet import Fernet
from brain.memory_prototype import SyntheticMemory,Conflict,_unlinked
from brain.memory_recovery_latest import RecoveryHead,SyntheticRecoveryLatest
from brain.memory_recovery_trust import seal_trust
from test_memory_recovery_pack import RecoveryPackChecks
from tools import memory_recovery_host_bundle as bundle

CODE_ARCHIVE=None
EVIDENCE={}
BOOTSTRAP="""import runpy,sys
if sys.argv[2]:sys.path.insert(0,sys.argv[2])
if sys.argv[3]=='disable':sys.modules['sqlcipher3']=None
runpy.run_path(sys.argv[1],run_name='__main__')
"""


class RecoveryHostChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='fake-cold-host-');self.addCleanup(temp.cleanup);self.home=Path(temp.name)
        self.archive=self.home/'recovery-code.zip'
        if CODE_ARCHIVE is None:bundle.build(self.archive,synthetic_only=True,approved=True)
        else:shutil.copyfile(CODE_ARCHIVE,self.archive)
        self.driver=''
        if sys.platform=='win32':
            import sqlcipher3
            source=Path(sqlcipher3.__file__).parent;target=self.home/'runtime/sqlcipher3';target.mkdir(parents=True)
            copied=[]
            for path in source.iterdir():
                if path.suffix in ('.py','.pyd','.dll'):
                    _unlinked(path);shutil.copyfile(path,target/path.name);copied.append(path.name)
                    self.assertEqual(hashlib.sha256(path.read_bytes()).digest(),hashlib.sha256((target/path.name).read_bytes()).digest())
            self.assertTrue(any(name.endswith('.pyd') for name in copied));self.driver=str(target.parent)
        self.cwd=self.home/'empty-cwd';self.cwd.mkdir()

    def child(self,packet,*,disabled=False,raw=None):
        result=subprocess.run([sys.executable,'-I','-B','-c',BOOTSTRAP,str(self.archive),self.driver,'disable' if disabled else 'normal'],
            input=json.dumps(packet) if raw is None else raw,capture_output=True,text=True,cwd=self.cwd,timeout=30,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertNotIn('FAKE_DO_NOT_ECHO',result.stdout+result.stderr)
        self.assertEqual(result.stderr,'','Cold fake worker stderr withheld.')
        return result,json.loads(result.stdout)

    def inputs(self):
        f=RecoveryPackChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp()
        for name in ('backup','offline','latest','recovered'):(self.home/name).mkdir()
        old_pack=self.home/'backup/old';f.stage(old_pack);old_pins,_=f.pins()
        old_trust=self.home/'offline/old.enc'
        old_digest=seal_trust(old_trust,old_pins,f.unlock,synthetic_only=True,approved=True)
        store=SyntheticRecoveryLatest.create(self.home/'latest/head.sqlite',synthetic_only=True,approved=True)
        old=RecoveryHead(old_pins,old_digest);store.begin(None,old,approved=True);store.finish(old,old_pack,old_trust,f.unlock,approved=True)
        f.latest();pins,_=f.pins();pack=self.home/'backup/current';f.stage(pack)
        trust=self.home/'offline/current.enc';digest=seal_trust(trust,pins,f.unlock,synthetic_only=True,approved=True)
        current=RecoveryHead(pins,digest);store.begin(old,current,approved=True);store.finish(current,pack,trust,f.unlock,approved=True)
        packet=dict(version=1,synthetic_only=True,approved=True,latest_store=str(store.path),lineage=pins.state.anchor.lineage,
            pack=str(pack),trust=str(trust),destination=str(self.home/'recovered/result.sqlite'),unlock=f.unlock.decode(),now=f.f.now)
        return f,store,packet,old_pack,old_trust

    def test_bundle_contains_only_fixed_code_and_preserves_existing_output(self):
        output=self.home/'other.zip';first=bundle.build(output,synthetic_only=True,approved=True)
        second=bundle.build(self.home/'repeat.zip',synthetic_only=True,approved=True)
        self.assertEqual(first['sha256'],second['sha256'])
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()),set(first['files']));self.assertEqual(len(first['files']),9)
            self.assertTrue(all(name.endswith('.py') for name in archive.namelist()))
            self.assertEqual(archive.read('brain/__init__.py'),b'')
        with self.assertRaises(FileExistsError):bundle.build(output,synthetic_only=True,approved=True)
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),first['sha256'])
        for values in ({'synthetic_only':True,'approved':1},{'synthetic_only':1,'approved':True},{'synthetic_only':False,'approved':True}):
            with self.assertRaises(PermissionError):bundle.build(self.home/'refused.zip',**values)
        self.assertFalse((self.home/'refused.zip').exists())

    def test_cold_archive_restore_after_source_loss_preserves_record_semantics(self):
        f,store,packet,old_pack,old_trust=self.inputs();lost=f.f.home;f.doCleanups();self.assertFalse(lost.exists())
        run,result=self.child(packet);self.assertEqual(run.returncode,0);self.assertTrue(result['passed'])
        self.assertTrue(result['archive_only_project_imports']);self.assertTrue(result['quarantined'])
        memory=SyntheticMemory(packet['destination'],synthetic_only=True,encryption_key=f.f.key,clock=lambda:f.f.now)
        with memory._db() as db:
            rows={row['id']:dict(row) for row in db.execute('SELECT * FROM memories')}
            self.assertEqual(json.loads(rows[f.kept['id']]['value']),{'text':'SYNTHETIC_PACK_CORRECTION'})
            self.assertEqual(rows[f.kept['id']]['revision'],2)
            for mid in (f.forgotten['id'],f.expired['id']):
                self.assertEqual(rows[mid]['deleted'],1);self.assertIsNone(rows[mid]['value'])
            for term in ('SYNTHETIC_PACK_FORGOTTEN','SYNTHETIC_PACK_EXPIRED'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM memory_search WHERE memory_search MATCH ?',(term,)).fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bindings WHERE active=1').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)
        with self.assertRaises(PermissionError):memory.handle(f.f.turn(),dict(op='get',project='alpha',id=f.kept['id']),approved=True)
        blob=Path(packet['destination']).read_bytes();self.assertFalse(blob.startswith(b'SQLite format 3'))
        self.assertNotIn(b'SYNTHETIC_PACK_CORRECTION',blob)
        EVIDENCE.update(result,source_fixture_removed=True,correction_forget_expiry_and_old_binding_checked=True)

    def test_old_copies_wrong_unlock_missing_or_pending_latest_refuse_in_archive(self):
        f,store,packet,old_pack,old_trust=self.inputs()
        variants=[dict(packet,pack=str(old_pack),trust=str(old_trust)),dict(packet,unlock=Fernet.generate_key().decode()),
            dict(packet,latest_store=str(self.home/'missing.sqlite'))]
        for value in variants:
            run,result=self.child(value);self.assertEqual(run.returncode,1);self.assertFalse(result['passed'])
            self.assertFalse(Path(packet['destination']).exists())
        current=store.head(packet['lineage'])
        from dataclasses import replace
        pending=replace(current,pins=replace(current.pins,state=replace(current.pins.state,writer_epoch=current.pins.state.writer_epoch+1)),trust_digest='e'*64)
        store.begin(current,pending,approved=True)
        run,result=self.child(packet);self.assertEqual(run.returncode,1);self.assertFalse(result['passed'])
        self.assertFalse(Path(packet['destination']).exists())
        with self.assertRaises(Conflict):store.head(packet['lineage'])

    def test_bounded_exact_protocol_and_approval_do_not_echo_input(self):
        packet=dict(version=1,synthetic_only=True,approved=True,latest_store='FAKE_DO_NOT_ECHO',lineage='1'*32,
            pack='FAKE_DO_NOT_ECHO',trust='FAKE_DO_NOT_ECHO',destination='FAKE_DO_NOT_ECHO',unlock='FAKE_DO_NOT_ECHO',now=1)
        raws=['{',json.dumps(dict(packet,approved=1)),json.dumps(dict(packet,synthetic_only=False)),
            json.dumps(dict(packet,extra='FAKE_DO_NOT_ECHO')),json.dumps(dict(packet,unlock=None)),
            '{"version":1,"version":1}', 'x'*16385]
        for raw in raws:
            run,result=self.child(None,raw=raw);self.assertEqual(run.returncode,1);self.assertEqual(result,{'passed':False,'details_withheld':True})
        self.assertFalse((self.cwd/'FAKE_DO_NOT_ECHO').exists())

    def test_missing_sqlcipher_refuses_without_plaintext_fallback(self):
        f,store,packet,old_pack,old_trust=self.inputs()
        run,result=self.child(packet,disabled=True);self.assertEqual(run.returncode,1);self.assertFalse(result['passed'])
        self.assertFalse(Path(packet['destination']).exists())


if __name__=='__main__':unittest.main()
