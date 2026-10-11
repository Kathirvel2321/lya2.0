"""Read-only readiness checks. Never print host, identity paths or raw SSH errors."""
import ipaddress
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[2]
config = json.loads((ROOT / 'desktop/oracle.local.json').read_text())
host = str(ipaddress.ip_address(config['host']))
key = (ROOT / config['key_file']).resolve()
key.relative_to(ROOT)
pins = ROOT / 'oracle_known_hosts.local'
assert key.is_file() and pins.is_file()
options = ['-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=7',
           '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no', '-o', 'ForwardAgent=no',
           '-o', 'ClearAllForwardings=yes', '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
           '-o', 'UserKnownHostsFile='+str(pins), '-i', str(key)]
program = '''import importlib.util,json,os,pwd,sqlite3,subprocess
db=sqlite3.connect(':memory:')
db.execute('CREATE VIRTUAL TABLE t USING fts5(body)')
db.close()
try: pwd.getpwnam('lya-archive'); exists=True
except KeyError: exists=False
result={'fts5':True,'sudo_available':subprocess.run(['sudo','-n','true'],capture_output=True).returncode==0,
'archive_account_exists':exists,'archive_path_exists':os.path.lexists('/opt/lya-public'),
'onnxruntime_present':importlib.util.find_spec('onnxruntime') is not None}
print(json.dumps(result))'''
run = subprocess.run(['ssh', *options, 'ubuntu@'+host, '/usr/bin/python3 -c '+shlex.quote(program)],
                     capture_output=True, timeout=15, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
if run.returncode:
    raise SystemExit('Pinned Oracle readiness check failed; raw errors withheld.')
result = json.loads(run.stdout)
(Path(__file__).parent / 'readiness.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
