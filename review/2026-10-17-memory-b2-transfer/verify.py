"""Verify a supplied fake pack; browser evidence must establish its cloud origin."""
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
from brain.memory_custody import WitnessState
from brain.memory_recovery import CheckpointAnchor
from brain.memory_recovery_pack import NAMES,RecoveryPins,inspect_pack,stage_pack
from test_memory_recovery_pack import WORKER


def verify(folder,report_name):
    if not report_name.replace('-','').isalnum():raise ValueError('Simple evidence name required.')
    report_path=HERE/(report_name+'.json')
    if report_path.exists():raise FileExistsError('Preserve previous evidence.')
    prepared=json.loads((HERE/'prepared.json').read_text(encoding='utf-8'))
    for name,digest in prepared['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Prepared source changed.')
    local_path=Path(prepared['local_only_inputs'])
    if not local_path.resolve().is_relative_to((HERE/'.fake-local').resolve()):raise ValueError('Not a local fake fixture.')
    local=json.loads(local_path.read_text(encoding='utf-8'))
    state=local['pins']['state']
    pins=RecoveryPins(WitnessState(CheckpointAnchor(**state['anchor']),state['writer_epoch']),
                      local['pins']['keys_digest'],local['pins']['backup_sha256'])
    folder=Path(folder).absolute()
    if folder.resolve()==Path(prepared['upload_folder']).resolve():raise ValueError('Supply a separate readback folder.')
    unlock=local['unlock'].encode()
    inspect_pack(folder,pins=pins,unlock_key=unlock,synthetic_only=True,approved=True)
    home=Path(tempfile.mkdtemp(prefix='verify-',dir=local_path.parent))
    staged=home/'verified-input'
    stage_pack(staged,backup=folder/'backup.enc',checkpoint=folder/'checkpoint.enc',capsule=folder/'keys.enc',
               pins=pins,unlock_key=unlock,synthetic_only=True,approved=True)
    hashes={n:hashlib.sha256((staged/n).read_bytes()).hexdigest() for n in NAMES}
    if any(hashes[n]!=prepared['files'][n]['sha256'] for n in NAMES):raise ValueError('Readback byte mismatch.')
    local.update(pack=str(staged),destination=str(home/'restored.sqlite'))
    run=subprocess.run([sys.executable,'-I','-B','-c',WORKER],input=json.dumps(local),
        capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if run.returncode:raise RuntimeError('Fresh fake restore failed; raw output withheld.')
    result=json.loads(run.stdout)
    assert all(result[k] for k in ('recovered','quarantined','correction_preserved','forgotten_absent','expired_absent','old_binding_denied'))
    assert result['active_bindings']==result['resumed_jobs']==0
    report=dict(fake_data_only=True,input_sha256=hashes,all_prepared_bytes_match=True,
        fresh_process=result,remote_provenance_established_by_script=False,
        verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        prepared_report_sha256=hashlib.sha256((HERE/'prepared.json').read_bytes()).hexdigest())
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: verify.py READBACK_FOLDER NEW_EVIDENCE_NAME')
    print(json.dumps(verify(sys.argv[1],sys.argv[2])))
