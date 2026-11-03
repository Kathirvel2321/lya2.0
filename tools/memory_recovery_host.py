"""Packaged fake-only cold-recovery entry point; private inputs arrive over stdin."""
import json
from pathlib import Path
import sys

from brain.memory_custody import _approval
from brain.memory_prototype import _time
from brain.memory_recovery import _unique
from brain.memory_recovery_latest import SyntheticRecoveryLatest


def main():
    try:
        raw=sys.stdin.buffer.read(16385)
        if len(raw)>16384:raise ValueError('Recovery input budget exceeded.')
        packet=json.loads(raw,object_pairs_hook=_unique)
        fields={'version','synthetic_only','approved','latest_store','lineage','pack','trust','destination','unlock','now'}
        if (type(packet) is not dict or set(packet)!=fields or type(packet['version']) is not int
                or packet['version']!=1):raise ValueError('Exact fake-recovery protocol required.')
        _approval(packet['synthetic_only'],packet['approved'],lambda:False);_time(packet['now'])
        if any(type(packet[key]) is not str or not packet[key] for key in fields-{'version','synthetic_only','approved','now'}):
            raise ValueError('Explicit recovery inputs required.')
        archive=str(Path(__file__).parent)
        modules=[module for name,module in sys.modules.items() if name=='brain' or name.startswith('brain.')]
        if not modules or any(not str(getattr(module,'__file__','')).startswith(archive+'/')
                              and not str(getattr(module,'__file__','')).startswith(archive+'\\') for module in modules):
            raise ValueError('Run the reviewed code archive in an isolated interpreter.')
        store=SyntheticRecoveryLatest(packet['latest_store'],synthetic_only=True)
        result=store.restore(packet['lineage'],packet['pack'],packet['trust'],packet['destination'],
            packet['unlock'].encode('ascii'),approved=True,clock=lambda:packet['now'])
        print(json.dumps({'passed':True,'fake_data_only':True,'archive_only_project_imports':True,
            'quarantined':result['quarantined'],'active_bindings':result['active_bindings'],'resumed_jobs':result['resumed_jobs']}))
        return 0
    except Exception:
        print(json.dumps({'passed':False,'details_withheld':True}));return 1


if __name__=='__main__':raise SystemExit(main())
