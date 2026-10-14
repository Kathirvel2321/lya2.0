"""Explicit read-only Oracle screening; never install, enroll or read private stores."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

PROGRAM = r'''
import sys
sys.dont_write_bytecode = True
import json,os,pathlib,platform,shutil,subprocess
memory = {}
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
    key,value = line.split(':',1)
    if key in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):
        memory[key] = int(value.split()[0])*1024
disk = shutil.disk_usage('/var/lib')
run = subprocess.run(['systemctl','show','lya-connect.service','-p','ActiveState',
    '-p','MemoryCurrent','-p','MemoryMax','-p','TasksCurrent','-p','TasksMax'],
    capture_output=True,text=True,timeout=5,check=True)
service = dict(line.split('=',1) for line in run.stdout.splitlines() if '=' in line)
probe = "import importlib.util,json,sqlite3,sys;print(json.dumps(dict(python=list(sys.version_info[:3]),sqlite=sqlite3.sqlite_version,modules={name:importlib.util.find_spec(name) is not None for name in ('sqlcipher3','pysqlcipher3','cryptography')})))"
runtimes = {}
for name,executable in (('system','/usr/bin/python3'),('mobile','/opt/lya-connect/venv/bin/python')):
    if pathlib.Path(executable).is_file():
        run = subprocess.run([executable,'-I','-B','-c',probe],capture_output=True,text=True,timeout=5,check=True)
        runtimes[name] = json.loads(run.stdout)
print(json.dumps(dict(architecture=platform.machine(),logical_cpus=os.cpu_count(),
    memory_bytes=memory,disk_bytes=dict(total=disk.total,free=disk.free),
    mobile_service=service,runtimes=runtimes,read_only=True)))
'''


def assess(observed):
    """Publish only fixed capability flags; detailed counters stay ignored locally."""
    if observed['read_only'] is not True:raise ValueError('Read-only observation required.')
    memory,disk = observed['memory_bytes'],observed['disk_bytes']
    for value in (memory['MemTotal'],memory['MemAvailable'],disk['total'],disk['free']):
        if type(value) is not int or value<0:raise ValueError('Invalid resource observation.')
    if memory['MemAvailable']>memory['MemTotal'] or disk['free']>disk['total']:
        raise ValueError('Inconsistent resource observation.')
    runtime = observed['runtimes']['system'];modules = runtime['modules']
    if any(type(modules[name]) is not bool for name in ('sqlcipher3','pysqlcipher3','cryptography')):
        raise ValueError('Invalid runtime observation.')
    # shortcut: minimum screening thresholds only; qualify bounded load before deployment.
    checks = dict(memory_screen_256_mib=memory['MemAvailable']>=256*1024**2,
                  disk_screen_1_gib=disk['free']>=1024**3,
                  system_sqlcipher_candidate=modules['sqlcipher3'] or modules['pysqlcipher3'],
                  system_cryptography=modules['cryptography'],
                  existing_mobile_active=observed['mobile_service'].get('ActiveState')=='active')
    return dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),read_only=True,
        checks=checks,screening_only=True,production_ready=False,
        billing_eligibility_verified=False,independent_latest_state_qualified=False,
        protected_key_custody_configured=False,linux_encrypted_engine_qualified=False,
        real_device_acceptance_verified=False,remote_runtime_changed=False,
        private_memory_or_keys_transferred=False,
        gates=['free-account eligibility','separate restricted memory service and budgets',
               'Linux encrypted engine and failure qualification','protected independent keys',
               'independent latest-state/rollback policy','clean-host and real-device recovery'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-read-only',action='store_true',required=True)
    parser.parse_args()
    output = HERE/'oracle-screening.json'
    private = HERE/'.private/oracle-observed.json'
    if output.exists() or private.exists():raise SystemExit('Evidence exists; preserve it before another assessment.')
    from cloud.t02_remote import ssh_command
    from cloud.ssh_session import exchange
    command = ssh_command(PROGRAM)
    command[1:1] = ['-o','UpdateHostKeys=no','-o','ForwardAgent=no','-o','ClearAllForwardings=yes',
                    '-o','ControlMaster=no','-o','ControlPath=none']
    try:
        run = exchange(command,'',timeout=30,close_stdin=True,output_limit=65536)
        if run.returncode:raise RuntimeError('SSH failed')
        observed = json.loads(run.stdout)
        report = assess(observed)
    except Exception:
        raise SystemExit('Read-only screening failed; raw host output withheld, no readiness claim.') from None
    private.parent.mkdir(exist_ok=True)
    private.write_text(json.dumps(observed,indent=2)+'\n',encoding='utf-8')
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
