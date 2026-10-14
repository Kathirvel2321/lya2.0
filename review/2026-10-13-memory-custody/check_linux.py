"""Explicit temporary Oracle fake-data staging; no production activation or key transfer."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-fake-only',action='store_true',required=True)
    parser.add_argument('--owner-confirmed-free',action='store_true',required=True)
    parser.parse_args()
    output = HERE/'linux-validation.json'
    if output.exists():raise SystemExit('Preserve the existing qualification evidence before another run.')
    names = ('brain/conversation.py','brain/memory_prototype.py','brain/memory_recovery.py',
             'brain/memory_repository.py','brain/memory_authority.py','brain/memory_custody.py')
    sources = {name:(ROOT/name).read_text(encoding='utf-8') for name in names}
    sources['test_memory_custody.py'] = (ROOT/'test_memory_custody.py').read_text(encoding='utf-8')
    sources.update({'brain/__init__.py':'','test_qualification.py':(HERE.parent/'2026-10-13-memory-linux/test_qualification.py').read_text(encoding='utf-8')})
    packet = dict(owner_confirmed_free=True,sources=sources,
                  sha256={name:hashlib.sha256(source.encode()).hexdigest() for name,source in sources.items()})
    from cloud.t02_remote import ssh_command
    from cloud.ssh_session import exchange
    program = (HERE/'remote_stage.py').read_text(encoding='utf-8');compile(program,'remote-stage','exec')
    command = ssh_command(program)
    command[1:1] = ['-o','UpdateHostKeys=no','-o','ForwardAgent=no','-o','ClearAllForwardings=yes',
                    '-o','ControlMaster=no','-o','ControlPath=none']
    try:
        run = exchange(command,json.dumps(packet),timeout=160,close_stdin=True,output_limit=65536)
        if run.returncode:raise RuntimeError('Remote qualification failed')
        result = json.loads(run.stdout)
    except Exception:
        raise SystemExit('Temporary qualification failed; raw host output withheld. No qualification claimed.') from None
    (HERE/'linux-tests.txt').write_text(result.pop('tests'),encoding='utf-8')
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    return 0 if (result['passed'] and result['tests_run']==20 and not result['skipped']
        and result['temporary_stage_removed'] and result['mobile_state_and_source_unchanged']) else 1


if __name__=='__main__':raise SystemExit(main())
