"""One temporary cross-host fake-data rehearsal on the owner-selected Oracle host."""
import argparse
import base64
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(HERE.parent/'2026-10-13-memory-linux')]
if sys.platform=='win32':sys.path.insert(2,str(HERE.parent/'2026-10-12-memory-hardening/.drivers'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--temporary-fake-only',action='store_true',required=True)
    args=parser.parse_args();report=HERE/'oracle-validation.json';log=HERE/'oracle-tests.txt'
    if report.exists() or log.exists():parser.error('Preserve preceding evidence.')
    manifest=json.loads((HERE/'oracle-source-manifest-3.json').read_text())
    def check():
        for name,digest in manifest['reviewed_normalized_sha256'].items():
            path=ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            assert hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
    check()
    names=['brain/conversation.py','brain/memory_prototype.py','brain/memory_recovery.py','brain/memory_repository.py',
        'brain/memory_authority.py','brain/memory_custody.py','brain/memory_recovery_pack.py','brain/memory_recovery_trust.py',
        'brain/memory_recovery_latest.py','brain/memory_publication_authority.py','brain/memory_authority_transfer.py',
        'tools/memory_recovery_host_bundle.py','test_memory_recovery_pack.py','test_memory_publication_authority.py',
        'test_memory_recovery_host.py','test_memory_authority_transfer.py']
    sources={name:(ROOT/name).read_text(encoding='utf-8') for name in names}
    sources.update({'test_qualification.py':(HERE.parent/'2026-10-13-memory-linux/test_qualification.py').read_text(encoding='utf-8'),
        'oracle_fixture.py':(HERE.parent/'2026-10-13-memory-linux/remote_stage.py').read_text(encoding='utf-8'),
        'brain/__init__.py':'','tools/__init__.py':''})
    from test_memory_authority_transfer import AuthorityTransferChecks
    old=tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.or-',dir=ROOT) as folder:
        tempfile.tempdir=folder;test=AuthorityTransferChecks(methodName='runTest')
        try:
            test.setUp();f,a,latest,bundle,receipt=test.sealed();pack,trust=test.files(a,latest,f.f.anchor.lineage)
            fixture={'bundle.enc':base64.b64encode(bundle.read_bytes()).decode(),
                'trust.enc':base64.b64encode(trust.read_bytes()).decode()}
            fixture.update({name:base64.b64encode((pack/name).read_bytes()).decode() for name in ('backup.enc','checkpoint.enc','keys.enc')})
            transfer=dict(head=asdict(receipt['head']),lineage=f.f.anchor.lineage,unlock=f.unlock.decode(),digest=receipt['sha256'],
                now=f.f.now,kept=f.kept['id'],forgotten=f.forgotten['id'],expired=f.expired['id'])
            lost=f.f.home;test.doCleanups();transfer['origin_absent']=not lost.exists()
            if not transfer['origin_absent']:raise ValueError('Original fake source still exists.')
        finally:test.doCleanups();tempfile.tempdir=old
    packet=dict(sources=sources,sha256={name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()},
        fixture=fixture,transfer=transfer)
    program=(HERE/'oracle_stage.py').read_text(encoding='utf-8');compile(program,'oracle-stage','exec')
    from cloud.t02_remote import ssh_command
    from cloud.ssh_session import exchange
    command=ssh_command(program);command[1:1]=['-o','UpdateHostKeys=no','-o','ForwardAgent=no','-o','ClearAllForwardings=yes',
        '-o','ControlMaster=no','-o','ControlPath=none']
    try:
        run=exchange(command,json.dumps(packet),timeout=360,close_stdin=True,output_limit=65536)
        if run.returncode:raise ValueError('SSH rehearsal refused')
        result=json.loads(run.stdout)
    except Exception:result=dict(passed=False,raw_details_withheld=True)
    check()
    if 'tests' in result:
        with log.open('x',encoding='utf-8') as output:output.write(result.pop('tests'))
    result['reviewed_local_sources_match_before_after']=True
    with report.open('x') as output:json.dump(result,output,indent=2);output.write('\n')
    passed=(result.get('passed') is True and result.get('tests_run')==8 and result.get('cross_host',{}).get('passed') is True
        and result.get('temporary_stage_removed') is True and result.get('existing_service_and_sources_unchanged') is True)
    print(json.dumps(dict(passed=passed,report=report.name,tests_run=result.get('tests_run'),
        cross_host=result.get('cross_host'),temporary_stage_removed=result.get('temporary_stage_removed'))))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
