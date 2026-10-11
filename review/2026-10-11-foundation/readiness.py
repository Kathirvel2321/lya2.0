"""Read only machine counters and code hashes; never keys, auth DB or provider data."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.setup_mobile_connection import operator

spec=importlib.util.spec_from_file_location('capacity_reader',ROOT/'review/2026-10-11-system-architecture/inspect_capacity.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

EXTRA=r'''
import hashlib
base=pathlib.Path('/opt/lya-connect')
paths=['cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/mobile_tts.py']
print(json.dumps(dict(hashes={name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in paths},
    timing_present='Server-Timing' in (base/'cloud/mobile.py').read_text())))
'''


if __name__=='__main__':
    counters=operator(module.PROGRAM,timeout=25)
    # Separate program output, so only the public code hashes are inspected here.
    hashes=operator('import json,pathlib\n'+EXTRA,timeout=20)
    disk=shutil.disk_usage(ROOT)
    result={'date':'2026-10-11','read_only':True,'oracle':counters,'deployed_source':hashes,
        'laptop_disk_bytes':{'total':disk.total,'free':disk.free},
        'gates':{'billing_eligibility':'unverified; machine counters are not account entitlement',
                 'independent_recovery':'not configured by this phase','shared_memory':'not enabled'}}
    assert counters['read_only'] and counters['disk_bytes']['free']>0
    Path(__file__).with_name('readiness.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'success':True,'oracle_active':counters['mobile_service']['ActiveState'],
        'timing_present':hashes['timing_present'],'cost_eligibility_verified':False}))
