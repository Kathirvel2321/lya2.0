"""Read-only pinned-SSH capacity checks; no secrets, prompts or host names emitted."""
import ipaddress
import json
from pathlib import Path
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[2]
config=json.loads((ROOT/'desktop/oracle.local.json').read_text())
key=(ROOT/config['key_file']).resolve()
key.relative_to(ROOT)
assert key.is_file() and (ROOT/'oracle_known_hosts.local').is_file()
program='''import importlib.util,json,os,pathlib,shutil,subprocess
disk=shutil.disk_usage('/'); available=0
for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
 if line.startswith('MemAvailable:'): available=int(line.split()[1])*1024
t=shutil.which('tailscale'); state={}
if t:
 try: state=json.loads(subprocess.run([t,'status','--json'],capture_output=True,timeout=4).stdout)
 except Exception: pass
print(json.dumps({'pinned_ssh':True,'python_fido2':importlib.util.find_spec('fido2') is not None,
'venv_available':importlib.util.find_spec('venv') is not None,
'tailscale_installed':bool(t),'tailscale_running':state.get('BackendState')=='Running',
'tailscale_dns_configured':bool(state.get('Self',{}).get('DNSName')),
'memory_headroom_256_mib':available>=256*1024**2,'disk_headroom_1_gib':disk.free>=1024**3,
'inference_source_exists':pathlib.Path('/home/ubuntu/lya/inference.py').is_file(),
'mobile_install_exists':os.path.lexists('/opt/lya-connect'),
'sudo_available':subprocess.run(['sudo','-n','true'],capture_output=True).returncode==0}))'''
command=['ssh','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=7',
    '-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ForwardAgent=no',
    '-o','ClearAllForwardings=yes','-o','ControlMaster=no','-o','ControlPath=none',
    '-o','UserKnownHostsFile='+str(ROOT/'oracle_known_hosts.local'),'-i',str(key),
    'ubuntu@'+str(ipaddress.ip_address(config['host'])),'/usr/bin/python3 -c '+shlex.quote(program)]
run=subprocess.run(command,capture_output=True,timeout=20,
                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
if run.returncode:raise SystemExit('Pinned host check failed; raw errors withheld.')
report=json.loads(run.stdout)
Path(__file__).with_name('host-readiness.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
