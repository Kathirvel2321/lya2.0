"""One explicitly approved fake-pack B2 qualification; never creates a key."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TRANSFER=HERE.parent/'2026-10-17-memory-b2-transfer'
sys.path[:0]=[str(ROOT),str(HERE.parent/'2026-10-13-memory-linux'),
              str(HERE.parent/'2026-10-12-memory-hardening/.drivers')]
from brain import memory_b2_credential as custody
from brain.memory_b2_backup import _B2,B2RequestRefused
from brain.memory_custody import WitnessState
from brain.memory_prototype import _unlinked
from brain.memory_recovery import CheckpointAnchor
from brain.memory_recovery_pack import NAMES,RecoveryPins,inspect_pack


def pins_from(local):
    state=local['pins']['state']
    return RecoveryPins(WitnessState(CheckpointAnchor(**state['anchor']),state['writer_epoch']),
                        local['pins']['keys_digest'],local['pins']['backup_sha256'])


def fixture():
    prepared=json.loads((TRANSFER/'prepared.json').read_text(encoding='utf-8'))
    if prepared['fake_data_only'] is not True or prepared['encrypted_bytes']!=5395:
        raise ValueError('Only the reviewed 5395-byte fake pack is allowed.')
    for name,digest in prepared['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Prepared source changed.')
    local_path=Path(prepared['local_only_inputs']).absolute();pack=Path(prepared['upload_folder']).absolute()
    for path in (local_path,pack):
        _unlinked(path)
        if not path.is_relative_to(TRANSFER/'.fake-local'):raise ValueError('Reviewed fake fixture required.')
    local=json.loads(local_path.read_text(encoding='utf-8'));pins=pins_from(local)
    if Path(local['lost_source']).exists():raise ValueError('Original synthetic source must be absent.')
    checked=inspect_pack(pack,pins=pins,unlock_key=local['unlock'].encode(),synthetic_only=True,approved=True)
    if checked['encrypted_bytes']!=5395:raise ValueError('Unexpected fake pack size.')
    for name in NAMES:
        blob=(pack/name).read_bytes()
        if len(blob)!=prepared['files'][name]['bytes'] or hashlib.sha256(blob).hexdigest()!=prepared['files'][name]['sha256']:
            raise ValueError('Reviewed fake ciphertext changed.')
    return prepared,local_path,pins,pack


def recover(folder,name):
    spec=importlib.util.spec_from_file_location('reviewed_b2_readback_verifier',TRANSFER/'verify.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=ROOT
    return module.verify(folder,name)


def run(credential_path,bucket_id,bucket_name,name,*,approved=False):
    if approved is not True:raise PermissionError('Exact fake-data transfer approval required.')
    if type(name) is not str or not re.fullmatch(r'[a-z0-9-]{1,50}',name):raise ValueError('Simple new run name required.')
    custody._scope(bucket_id,bucket_name)
    prepared,local_path,pins,pack=fixture()
    report_path=HERE/(name+'.json');recovery_name=name+'-recovery'
    home=local_path.parent/name
    if report_path.exists() or home.exists() or (TRANSFER/(recovery_name+'.json')).exists():
        raise FileExistsError('Preserve earlier attempts; no automatic retry.')
    _unlinked(home);home.mkdir();readback=home/'readback';readback.mkdir()
    data=custody._load(credential_path,bucket_id,bucket_name)
    client=_B2(lambda:False)
    client.authorize(data['key_id'],data['key'],bucket_id,bucket_name,custody.PREFIX)
    denials={}
    # Read-only probes: no deletion/key-management request and no private object name.
    probes={'outside_prefix':lambda:client.get('backup.enc',prepared['files']['backup.enc']['bytes']),
            'file_listing':lambda:client.call('b2_list_file_names',{'bucketId':bucket_id,'prefix':custody.PREFIX,'maxFileCount':1})}
    for label,probe in probes.items():
        try:probe()
        except B2RequestRefused as error:
            if error.status not in (401,403):raise ValueError('Permission refusal was not established.') from None
            denials[label]=error.status
        else:raise ValueError('A requested read-only scope restriction was not enforced.')
    receipt=custody.backup_with_credential(pack,home/'receipt.json',credential_path=credential_path,
        bucket_id=bucket_id,bucket_name=bucket_name,pins=pins,
        observe=lambda:pins_from(json.loads(local_path.read_text(encoding='utf-8'))),
        synthetic_only=True,approved=True)
    for filename in NAMES:
        blob=client.get(receipt['object_prefix']+filename,prepared['files'][filename]['bytes'])
        if blob is None or hashlib.sha256(blob).hexdigest()!=prepared['files'][filename]['sha256']:
            raise ValueError('Separate remote download differs.')
        (readback/filename).write_bytes(blob)
    verification=recover(readback,recovery_name)
    report=dict(passed=True,fake_data_only=True,encrypted_bytes=5395,artifacts=list(NAMES),
        uploader_receipt_verified=receipt['verified'],scope_read_denials_http=denials,
        downloaded_hashes_match=True,fresh_process=verification['fresh_process'],
        extra_client_calls=client.calls,prior_manual_verifier_reused=True,
        credential_printed=False,master_key_used=False,new_key_created=False,delete_requested=False,
        independent_trust_or_clean_machine_qualified=False,
        pilot_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with report_path.open('x',encoding='utf-8') as output:output.write(json.dumps(report,indent=2)+'\n')
    client.headers.clear();return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved',action='store_true')
    parser.add_argument('--credential');parser.add_argument('--bucket-id');parser.add_argument('--bucket-name')
    parser.add_argument('--name',default='native-pilot-20261021')
    args=parser.parse_args()
    try:
        if not args.approved:
            p,_,_,_=fixture()
            print(json.dumps({'prepared':True,'fake_data_only':True,'files':{n:p['files'][n]['bytes'] for n in NAMES},
                'encrypted_bytes':5395,'credential_read':False,'network_requested':False}));return 0
        if not all((args.credential,args.bucket_id,args.bucket_name)):parser.error('Explicit credential path and lab destination required.')
        result=run(args.credential,args.bucket_id,args.bucket_name,args.name,approved=True)
        print(json.dumps({'passed':result['passed'],'encrypted_bytes':5395,'fresh_process_recovered':result['fresh_process']['recovered']}));return 0
    except Exception:
        print('Pilot qualification did not complete. Preserve its artifacts; do not retry automatically. Private details withheld.');return 1


if __name__=='__main__':raise SystemExit(main())
