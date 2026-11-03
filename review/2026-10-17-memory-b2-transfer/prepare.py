"""Prepare disposable fake artifacts only; no network, credentials or real stores."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(HERE.parent/'2026-10-13-memory-linux'),
              str(HERE.parent/'2026-10-12-memory-hardening/.drivers')]
from brain.memory_recovery_pack import NAMES,MAX_PACK_BYTES,inspect_pack
from test_memory_recovery_pack import RecoveryPackChecks,WORKER


def main():
    report=HERE/'prepared.json'
    if report.exists():raise FileExistsError('Preserve the previous fixture and report.')
    fixture=RecoveryPackChecks(methodName='runTest')
    original=tempfile.tempdir
    local_root=HERE/'.fake-local';local_root.mkdir(exist_ok=True)
    tempfile.tempdir=str(local_root)
    try:
        fixture.setUp()
        fixture.latest();pins,_=fixture.pins()
        home=Path(tempfile.mkdtemp(prefix='lya-fake-b2-transfer-'))
        pack=home/'upload-only'
        result=fixture.stage(pack)
        assert set(p.name for p in pack.iterdir())==set(NAMES)
        for name in NAMES:
            blob=(pack/name).read_bytes()
            for marker in (fixture.unlock,fixture.key,fixture.f.key,b'SYNTHETIC_PACK_CORRECTION'):
                assert marker not in blob
        local=dict(imports=[str(ROOT),str(HERE.parent/'2026-10-12-memory-hardening/.drivers')],
            lost_source=str(fixture.f.home),pack=str(pack),destination=str(home/'local-check.sqlite'),
            pins=asdict(pins),unlock=fixture.unlock.decode(),storage_key=fixture.f.key.hex(),now=fixture.f.now,
            kept=fixture.kept['id'],forgotten=fixture.forgotten['id'],expired=fixture.expired['id'])
        # shortcut: ignored fake-only inputs survive locally; no production key custody.
        (home/'local-only.json').write_text(json.dumps(local),encoding='utf-8')
        fixture.doCleanups()
        assert not Path(local['lost_source']).exists()
        run=subprocess.run([sys.executable,'-I','-B','-c',WORKER],input=json.dumps(local),
            capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if run.returncode:raise RuntimeError('Fresh fake restore failed; raw output withheld.')
        checked=json.loads(run.stdout)
        assert all(checked[k] for k in ('recovered','quarantined','correction_preserved','forgotten_absent','expired_absent','old_binding_denied'))
        assert checked['active_bindings']==checked['resumed_jobs']==0
        assert inspect_pack(pack,pins=pins,unlock_key=fixture.unlock,synthetic_only=True,approved=True)==result
        assert 0<result['encrypted_bytes']<=MAX_PACK_BYTES
        # Keep the original path blocked, so a later remote check must restore to a new file.
        report.write_text(json.dumps(dict(fake_data_only=True,upload_folder=str(pack),
            local_only_inputs=str(home/'local-only.json'),encrypted_bytes=result['encrypted_bytes'],
            files={n:dict(bytes=(pack/n).stat().st_size,sha256=hashlib.sha256((pack/n).read_bytes()).hexdigest()) for n in NAMES},
            source_fixture_removed=True,local_fresh_process=checked,uploaded=False,
            source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                (Path(__file__),ROOT/'brain/memory_recovery_pack.py',ROOT/'test_memory_recovery_pack.py')}),indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'prepared':True,'upload_folder':str(pack),'encrypted_bytes':result['encrypted_bytes'],
                          'local_fresh_process':checked,'uploaded':False}))
    finally:
        fixture.doCleanups()
        tempfile.tempdir=original


if __name__=='__main__':main()
