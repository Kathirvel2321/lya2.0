"""Local fresh-process loss drill: generated keys, fake identities, temporary stores."""
from contextlib import closing
from dataclasses import asdict
import io
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DRIVER = HERE.parent/'2026-10-12-memory-hardening/.drivers'
sys.path[:0] = [str(ROOT),str(DRIVER)]
import test_memory_authority as fixtures

WORKER = r'''
import json,pathlib,sqlite3,sys,threading,time
p = json.load(sys.stdin)
sys.path[:0] = [p['root'],p['driver']]
from brain.conversation import Context,PublicTurn
from brain.memory_authority import SyntheticAuthority,WriterGrant
from brain.memory_prototype import Conflict
from brain.memory_recovery import CheckpointAnchor,SyntheticRecovery
assert not pathlib.Path(p['lost_source']).exists()
try:
    recovery = SyntheticRecovery(bytes.fromhex(p['recovery_key']),synthetic_only=True,clock=lambda:p['now'])
    authority = SyntheticAuthority(p['target'],recovery=recovery,storage_key=bytes.fromhex(p['storage_key']),
                                   synthetic_only=True,clock=lambda:p['now'])
    anchor = CheckpointAnchor(**p['anchor'])
    destination = pathlib.Path(p['target']).parent/'quarantine.sqlite'
    restored = authority.restore(anchor.lineage,destination,expected_anchor=anchor,approved=True)
    if p['expect_error']:raise AssertionError('Expected recovery rejection')
    context = Context(p['principal'],'phone','a'*64,p['principal'],p['now']+300,True)
    turn = PublicTurn('f'*32,'SYNTHETIC_CLEAN_PROCESS',context,time.monotonic()+30,
                      lambda:context,lambda:p['now'],threading.Event())
    activated = authority.activate_restored(anchor.lineage,destination,turn,'b'*32,
        expected_anchor=anchor,expected_epoch=restored['writer_epoch'],approved=True)
    old = WriterGrant(**{**p['old_grant'],'token':bytes.fromhex(p['old_grant']['token'])})
    packet = dict(op='get',project='alpha',id=p['kept'])
    try:authority.handle(old,turn,packet,expected_anchor=activated['anchor'],approved=True)
    except PermissionError:pass
    else:raise AssertionError('Old writer survived cutover')
    for mid in (p['forgotten'],p['expired']):
        result = authority.handle(activated['grant'],turn,dict(op='get',project='alpha',id=mid),
                                  expected_anchor=activated['anchor'],approved=True)
        assert result['result']['record'] is None
    record = authority.handle(activated['grant'],turn,packet,expected_anchor=activated['anchor'],approved=True)['result']['record']
    assert (record['value']['text'],record['revision'],record['owner']) == ('SYNTHETIC_CORRECTED',2,p['owner'])
    assert activated['active_bindings']==1 and activated['resumed_jobs']==0
    assert restored['result']['suppressed_deleted']==1 and restored['result']['suppressed_expired']==1
    print(json.dumps(dict(recovered=True,corrected=True,forgotten_absent=True,expired_absent=True,
                         old_writer_rejected=True,active_bindings=1,resumed_jobs=0)))
except (ValueError,KeyError,OSError,sqlite3.DatabaseError,Conflict) as error:
    if not p['expect_error']:raise
    print(json.dumps(dict(recovered=False,rejection=type(error).__name__)))
'''


class CleanProcessChecks(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.AuthorityChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.home = self.f.f.path.parent
        self.old = self.image('old')
        self.kept = self.f.call(self.f.f.save_packet(key='kept'))
        self.f.call(dict(op='correct',project='alpha',request_id=self.f.f.rid(),id=self.kept['id'],
                         expected_revision=1,value={'text':'SYNTHETIC_CORRECTED'}))
        self.f.call(dict(op='forget',project='alpha',request_id=self.f.f.rid(),id=self.f.seed['id'],expected_revision=1))
        self.expired = self.f.call(self.f.f.save_packet(key='expired',retention={'mode':'until','expires_at':self.f.f.now+1}))
        self.f.f.now += 2
        self.target = self.image('fresh')
        self.packet = dict(root=str(ROOT),driver=str(DRIVER),lost_source=str(self.home),target=str(self.target),
            recovery_key=self.f.recovery_key.hex(),storage_key=self.f.key.hex(),anchor=asdict(self.f.anchor),
            now=self.f.f.now,principal=self.f.f.f.binding,owner=self.f.f.owner,kept=self.kept['id'],
            forgotten=self.f.seed['id'],expired=self.expired['id'],expect_error=False,
            old_grant=dict(lineage=self.f.grant.lineage,epoch=self.f.grant.epoch,
                           writer=self.f.grant.writer,token=self.f.grant.token.hex()))
        # Only the newly generated fixture directory moves; no real stores are read or moved.
        source = self.home.resolve();workspace = HERE.resolve()
        assert source.is_relative_to(workspace) and source.name.startswith('lya-synthetic-memory-')
        assert not source.is_symlink() and not source.is_junction()
        source.rename(source.with_name('offline-'+source.name))
        self.assertFalse(source.exists())

    def image(self, name):
        destination = Path(tempfile.mkdtemp(prefix=name+'-',dir=tempfile.gettempdir()))/'authority'
        destination.mkdir();(destination/'objects').mkdir()
        with closing(sqlite3.connect(self.f.a._repository.catalog.as_uri()+'?mode=ro',uri=True)) as source:
            with closing(sqlite3.connect(destination/'catalog.sqlite')) as target:source.backup(target)
            object_id = source.execute('SELECT object_id FROM latest').fetchone()[0]
        folder = destination/'objects'/object_id;folder.mkdir()
        for name in ('backup.enc','checkpoint.enc'):shutil.copyfile(self.f.path/'objects'/object_id/name,folder/name)
        self.assertFalse(list(destination.glob('objects/*/live.sqlite')))
        return destination

    def child(self, **changes):
        packet = {**self.packet,**changes}
        run = subprocess.run([sys.executable,'-I','-B','-c',WORKER],input=json.dumps(packet),
            capture_output=True,text=True,timeout=40,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        # Generated key material is supplied on stdin, never logged or placed in argv.
        self.assertEqual(run.returncode,0,'Disposable child rejected the drill unexpectedly; raw output withheld.')
        return json.loads(run.stdout)

    def test_latest_metadata_and_bundle_recover_without_original_source_or_live_copy(self):
        result = self.child()
        self.assertTrue(all(result[name] for name in ('recovered','corrected','forgotten_absent','expired_absent','old_writer_rejected')))
        self.assertEqual((result['active_bindings'],result['resumed_jobs']),(1,0))

    def test_missing_or_wrong_keys_and_missing_catalogue_never_recover(self):
        for keys in (dict(storage_key=''),dict(storage_key='00'*32),dict(recovery_key=''),dict(recovery_key='00'*32)):
            with self.subTest(fields=tuple(keys)):
                self.assertFalse(self.child(expect_error=True,**keys)['recovered'])
        (self.target/'catalog.sqlite').unlink()
        self.assertFalse(self.child(expect_error=True)['recovered'])
        self.assertFalse((self.target/'catalog.sqlite').exists())

    def test_old_catalogue_is_rejected_when_latest_anchor_survives_separately(self):
        self.assertFalse(self.child(target=str(self.old),expect_error=True)['recovered'])


def main():
    from sqlcipher3 import dbapi2
    compile(WORKER,'fresh-process-worker','exec')
    original = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        tempfile.tempdir = folder
        try:
            log = io.StringIO();result = unittest.TextTestRunner(stream=log,verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(CleanProcessChecks))
        finally:tempfile.tempdir = original
    (HERE/'recovery-tests.txt').write_text(log.getvalue(),encoding='utf-8')
    report = dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        skipped=len(result.skipped),passed=result.wasSuccessful() and not result.skipped,
        fake_data_only=True,fresh_process=True,same_physical_host=True,source_path_unavailable=True,
        live_database_copied=False,real_key_custody_tested=False,off_host_durability_tested=False)
    (HERE/'recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
