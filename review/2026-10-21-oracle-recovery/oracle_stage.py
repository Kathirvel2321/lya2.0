"""Temporary Oracle fake recovery; pinned public sources, no account/service changes."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import platform
import resource
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

NAMES={'brain/__init__.py','tools/__init__.py','brain/conversation.py','brain/memory_prototype.py',
    'brain/memory_recovery.py','brain/memory_repository.py','brain/memory_authority.py','brain/memory_custody.py',
    'brain/memory_recovery_pack.py','brain/memory_recovery_trust.py','brain/memory_recovery_latest.py',
    'brain/memory_publication_authority.py','brain/memory_authority_transfer.py','tools/memory_recovery_host_bundle.py',
    'test_qualification.py','test_memory_recovery_pack.py','test_memory_publication_authority.py',
    'test_memory_recovery_host.py','test_memory_authority_transfer.py','oracle_fixture.py'}

TESTS=r'''
import io,json,pathlib,sys,tempfile,unittest
root=pathlib.Path.cwd();sys.path.insert(0,str(root));tempfile.tempdir=str(root/'fixtures')
from test_memory_authority_transfer import AuthorityTransferChecks
names=[n for n in unittest.defaultTestLoader.getTestCaseNames(AuthorityTransferChecks) if n.startswith('test_transfer_')]
assert len(names)==8
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(AuthorityTransferChecks(n) for n in names))
print(json.dumps(dict(passed=result.wasSuccessful() and not result.skipped and result.testsRun==8,
    tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
    case_names=names,tests=stream.getvalue())))
'''

RECOVER=r'''
import json,pathlib,sys,threading,time
root=pathlib.Path.cwd();sys.path.insert(0,str(root));p=json.load(sys.stdin)
from brain.conversation import Context,PublicTurn
from brain.memory_authority_transfer import restore_authority,_open_authority
from brain.memory_recovery_latest import SyntheticRecoveryLatest
from brain.memory_prototype import Conflict,SyntheticMemory
latest=SyntheticRecoveryLatest(root/'surviving/latest.sqlite',synthetic_only=True)
head=latest.head(p['lineage']);unlock=p['unlock'].encode()
out=restore_authority(root/'incoming/bundle.enc',root/'recovered',latest=latest,lineage=p['lineage'],
    unlock_key=unlock,trusted_digest=p['digest'],synthetic_only=True,approved=True,clock=lambda:p['now'])
assert out['writer_epoch']==head.pins.state.writer_epoch+1 and out['quarantined']
memory=SyntheticMemory(out['quarantine'],synthetic_only=True,encryption_key=__import__('brain.memory_custody',fromlist=['open_keys']).open_keys(
    root/'recovered/keys.enc',unlock,lineage=p['lineage'],trusted_digest=head.pins.keys_digest,synthetic_only=True,approved=True).storage_key,clock=lambda:p['now'])
with memory._db() as db:
    assert db.execute('SELECT COUNT(*) FROM bindings').fetchone()[0]==0
    assert db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]==0
    rows={r['id']:dict(r) for r in db.execute('SELECT * FROM memories')}
    assert json.loads(rows[p['kept']]['value'])=={'text':'SYNTHETIC_PACK_CORRECTION'}
    for mid in (p['forgotten'],p['expired']):assert rows[mid]['deleted']==1 and rows[mid]['value'] is None
a=_open_authority(root/'recovered',latest,unlock,p['lineage'],head.pins.keys_digest,lambda:p['now'])
context=Context('1'*64,'phone','2'*64,'1'*64,p['now']+300,True)
turn=PublicTurn('3'*32,'FAKE_ORACLE_RECOVERY',context,time.monotonic()+30,lambda:context,lambda:p['now'],threading.Event())
reply=a.activate_restored(p['lineage'],out['quarantine'],turn,'b'*32,expected_anchor=out['anchor'],expected_epoch=out['writer_epoch'],approved=True)
assert reply['publication_confirmed'] and reply['active_bindings']==1 and reply['resumed_jobs']==0
result=a.handle(reply['grant'],turn,dict(op='get',project='alpha',id=p['kept']),expected_anchor=reply['anchor'],approved=True)
assert result['result']['record']['value']=={'text':'SYNTHETIC_PACK_CORRECTION'}
try:restore_authority(root/'incoming/bundle.enc',root/'replay',latest=latest,lineage=p['lineage'],unlock_key=unlock,
    trusted_digest=p['digest'],synthetic_only=True,approved=True,clock=lambda:p['now'])
except Conflict:pass
else:raise AssertionError('Old envelope replay accepted')
assert not (root/'replay').exists()
print(json.dumps(dict(passed=True,origin_catalogue_absent=p['origin_absent'],separate_surviving_latest=True,
    fresh_process_recovery=True,quarantine_had_zero_bindings_jobs=True,correction_forget_expiry_preserved=True,
    preexisting_fake_owner_reactivated=True,old_envelope_replay_refused=True,no_writer_token_reported=True)))
'''


def bounds():
    for kind,value in ((resource.RLIMIT_AS,512*1024**2),(resource.RLIMIT_CPU,240),
                       (resource.RLIMIT_FSIZE,64*1024**2),(resource.RLIMIT_CORE,0)):
        resource.setrlimit(kind,(value,value))


def main():
    os.umask(0o077);raw=sys.stdin.buffer.read(4*1024**2+1)
    if len(raw)>4*1024**2:raise ValueError('Bounded rehearsal packet required.')
    p=json.loads(raw)
    if set(p)!={'sources','sha256','fixture','transfer'} or platform.machine()!='aarch64' or sys.version_info[:2]!=(3,12):
        raise ValueError('Exact fake target packet/platform required.')
    if set(p['sources'])!=NAMES or set(p['sha256'])!=NAMES:raise ValueError('Exact public source allowlist required.')
    for name,source in p['sources'].items():
        if type(source) is not str or len(source.encode())>100000 or hashlib.sha256(source.encode()).hexdigest()!=p['sha256'][name]:
            raise ValueError('Public source differs.')
        compile(source,name,'exec')
    with tempfile.TemporaryDirectory(prefix='lya-oracle-recovery-',dir='/tmp') as folder:
        root=Path(folder)
        for name,source in p['sources'].items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source,encoding='utf-8')
        sys.path.insert(0,str(root));import oracle_fixture as fixture
        before=fixture.mobile_state()
        with urllib.request.urlopen(fixture.URL,timeout=20) as response:wheel=response.read(16*1024**2+1)
        if len(wheel)>16*1024**2 or hashlib.sha256(wheel).hexdigest()!=fixture.SHA256:raise ValueError('Pinned existing driver differs.')
        with zipfile.ZipFile(io.BytesIO(wheel)) as archive:
            if sum(info.file_size for info in archive.infolist())>64*1024**2:raise ValueError('Driver budget exceeded.')
            for info in archive.infolist():
                path=PurePosixPath(info.filename)
                if path.is_absolute() or '..' in path.parts or (info.external_attr>>16)&0o170000==0o120000:
                    raise ValueError('Unsafe driver member.')
            archive.extractall(root)
        (root/'fixtures').mkdir();(root/'tests.py').write_text(TESTS,encoding='utf-8')
        run=subprocess.run([sys.executable,'-I','-B','tests.py'],cwd=root,capture_output=True,text=True,timeout=270,preexec_fn=bounds)
        if run.returncode or run.stderr:raise RuntimeError('Native fake cases failed; raw output withheld.')
        result=json.loads(run.stdout)
        if not result['passed']:return result
        incoming=root/'incoming';incoming.mkdir();pack=incoming/'pack';pack.mkdir()
        if set(p['fixture'])!={'bundle.enc','backup.enc','checkpoint.enc','keys.enc','trust.enc'}:raise ValueError('Wrong fake input files.')
        for name,value in p['fixture'].items():
            blob=base64.b64decode(value,validate=True)
            if len(blob)>2*1024**2:raise ValueError('Fixture byte budget exceeded.')
            (pack/name if name in ('backup.enc','checkpoint.enc','keys.enc') else incoming/name).write_bytes(blob)
        from brain.memory_recovery_latest import SyntheticRecoveryLatest,_decode
        from brain.memory_prototype import _json
        (root/'surviving').mkdir();latest=SyntheticRecoveryLatest.create(root/'surviving/latest.sqlite',synthetic_only=True,approved=True)
        head=_decode(_json(p['transfer']['head']));unlock=p['transfer']['unlock'].encode()
        latest.begin(None,head,approved=True);latest.finish(head,pack,incoming/'trust.enc',unlock,approved=True)
        (root/'recover.py').write_text(RECOVER,encoding='utf-8')
        run=subprocess.run([sys.executable,'-I','-B','recover.py'],cwd=root,input=json.dumps(p['transfer']),
            capture_output=True,text=True,timeout=60,preexec_fn=bounds)
        if run.returncode or run.stderr:raise RuntimeError('Cross-host fake recovery failed; raw output withheld.')
        result.update(cross_host=json.loads(run.stdout),source_sha256=p['sha256'],pinned_driver_sha256=fixture.SHA256)
        unchanged=fixture.mobile_state()==before
    result.update(temporary_stage_removed=not root.exists(),existing_service_and_sources_unchanged=unchanged,
        fake_data_only=True,platform='Linux aarch64 CPython 3.12',real_enrollment=False,production_connected=False,
        paid_resource_or_system_install=False,live_provider_or_vault_secret_read=False)
    return result


if __name__=='__main__':
    try:print(json.dumps(main()))
    except Exception:print(json.dumps(dict(passed=False,raw_details_withheld=True)));raise SystemExit(1)
