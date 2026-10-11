"""Explicit separate Oracle install/activation. No owner enrollment or provider calls.

Stage creates only the new app account/files, a fixed inference sudo rule and a
private venv. Network installs Tailscale from its signed Ubuntu repository; account
sign-in remains human-controlled. Activate refuses public Funnel/existing Serve.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

STAGE=r'''
import hashlib,json,os,pathlib,pwd,subprocess,sys
os.umask(0o077)
body=json.load(sys.stdin)
base=pathlib.Path('/opt/lya-connect');home=pathlib.Path('/var/lib/lya-connect')
unit=pathlib.Path('/etc/systemd/system/lya-connect.service')
rule=pathlib.Path('/etc/sudoers.d/lya-connect')
assert not any(p.exists() or p.is_symlink() for p in (base,home,unit,rule))
try: pwd.getpwnam('lya-connect');raise RuntimeError('account already exists')
except KeyError:pass
source=pathlib.Path('/home/ubuntu/lya/inference.py')
before=hashlib.sha256(source.read_bytes()).hexdigest()
for p in (pathlib.Path('/home/ubuntu'),source.parent,source):
 assert not p.is_symlink() and not p.stat().st_mode & 0o022
assert set(body)=={'files'} and set(body['files'])=={'cloud/__init__.py','cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/ssh_session.py'}
for name,text in body['files'].items():
 assert isinstance(text,str) and len(text.encode())<100000
 if name.endswith('.py'):compile(text,name,'exec')
subprocess.run(['useradd','--system','--user-group','--home-dir',str(home),'--shell','/usr/sbin/nologin','lya-connect'],check=True,capture_output=True)
account=pwd.getpwnam('lya-connect')
base.mkdir(mode=0o755);base.chmod(0o755)
home.mkdir(mode=0o700);os.chown(home,account.pw_uid,account.pw_gid)
(base/'cloud').mkdir(mode=0o755)
for name,text in body['files'].items():
 path=base/name;path.write_text(text,encoding='utf-8');path.chmod(0o644)
entry=base/'control.py'
entry.write_text("import sys\nsys.path.insert(0,'/opt/lya-connect')\nfrom cloud.mobile_runtime import main\nif __name__=='__main__':\n try:main()\n except Exception:raise SystemExit('LYA connection operation failed.')\n")
entry.chmod(0o644)
subprocess.run(['/usr/bin/python3','-m','venv',str(base/'venv')],check=True,capture_output=True,timeout=45)
subprocess.run([str(base/'venv/bin/python'),'-m','pip','install','--disable-pip-version-check','--index-url','https://pypi.org/simple','fido2==2.2.1'],check=True,capture_output=True,timeout=100)
# Public application/dependency files are root-owned and readable by the service.
for path in base.rglob('*'):
 if not path.is_symlink():path.chmod(0o755 if path.is_dir() or path.parent==base/'venv/bin' else 0o644)
# Inference keys/config remain with their existing account; command arguments are exact.
rule.write_text('lya-connect ALL=(ubuntu) NOPASSWD: /usr/bin/python3 /home/ubuntu/lya/inference.py\n')
rule.chmod(0o440)
subprocess.run(['/usr/sbin/visudo','-cf',str(rule)],check=True,capture_output=True)
unit.write_text('[Unit]\nDescription=LYA private mobile connection\nAfter=network-online.target tailscaled.service\n[Service]\nUser=lya-connect\nGroup=lya-connect\nWorkingDirectory=/opt/lya-connect\nExecStart=/opt/lya-connect/venv/bin/python -I /opt/lya-connect/control.py serve\nRestart=on-failure\nRestartSec=5\nUMask=0077\nPrivateTmp=yes\nProtectSystem=full\nProtectKernelTunables=yes\nProtectKernelModules=yes\nProtectControlGroups=yes\nRestrictAddressFamilies=AF_UNIX AF_INET AF_INET6\nMemoryMax=256M\nTasksMax=40\nLimitNOFILE=128\n[Install]\nWantedBy=multi-user.target\n')
unit.chmod(0o644)
subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
test=subprocess.run(['sudo','-n','-u','lya-connect',str(base/'venv/bin/python'),'-I','-c',"import sys;sys.path.insert(0,'/opt/lya-connect');from cloud.mobile import AuthStore;from pathlib import Path;import tempfile; t=tempfile.TemporaryDirectory();s=AuthStore(Path(t.name)/'check.sqlite');assert s.credential() is None;t.cleanup()"],capture_output=True,timeout=10)
assert test.returncode==0
denied=subprocess.run(['sudo','-n','-u','lya-connect','sudo','-n','-u','ubuntu','/usr/bin/python3','-c','raise SystemExit(0)'],capture_output=True,timeout=5)
assert denied.returncode!=0
print(json.dumps({'staged':True,'separate_account':True,'fido2_import':True,'temporary_store_check':True,'inference_unchanged':True,'service_started':False}))
'''

NETWORK=r'''
import json,pathlib,shutil,subprocess,urllib.request
if not shutil.which('tailscale'):
 release=dict(line.split('=',1) for line in pathlib.Path('/etc/os-release').read_text().splitlines() if '=' in line)
 assert release.get('ID','').strip('"')=='ubuntu'
 codename=release.get('VERSION_CODENAME','').strip('"')
 assert codename in ('focal','jammy','noble')
 key=pathlib.Path('/usr/share/keyrings/tailscale-archive-keyring.gpg')
 listing=pathlib.Path('/etc/apt/sources.list.d/tailscale.list')
 assert not key.exists() and not listing.exists()
 with urllib.request.urlopen('https://pkgs.tailscale.com/stable/ubuntu/'+codename+'.noarmor.gpg',timeout=15) as r:data=r.read(16385)
 assert 0<len(data)<=16384
 key.write_bytes(data);key.chmod(0o644)
 listing.write_text('deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/ubuntu '+codename+' main\n');listing.chmod(0o644)
 subprocess.run(['apt-get','update','-qq'],check=True,capture_output=True,timeout=100)
 subprocess.run(['apt-get','install','-y','tailscale'],check=True,capture_output=True,timeout=100)
subprocess.run(['systemctl','enable','--now','tailscaled'],check=True,capture_output=True)
print(json.dumps({'tailscale_installed':True,'signed_repository':True,'signed_in':False,'lya_service_started':False}))
'''

ACTIVATE=r'''
import http.client,json,pathlib,re,subprocess,time
state=json.loads(subprocess.run(['tailscale','status','--json'],check=True,capture_output=True,timeout=5).stdout)
assert state.get('BackendState')=='Running'
host=state['Self']['DNSName'].rstrip('.')
assert re.fullmatch(r'[a-z0-9-]+\.[a-z0-9-]+\.ts\.net',host)
origin='https://'+host
config=pathlib.Path('/etc/lya-connect.json')
assert not config.is_symlink()
if config.exists():
 assert config.stat().st_uid==0 and not config.stat().st_mode & 0o022
 assert json.loads(config.read_text())=={'origin':origin}
existing=json.loads(subprocess.run(['tailscale','serve','status','--json'],check=True,capture_output=True,timeout=5).stdout)
assert not any(existing.get('AllowFunnel',{}).values())
if existing.get('TCP') or existing.get('Web'):
 assert config.exists()
 assert existing.get('TCP')=={'443':{'HTTPS':True}}
 assert existing.get('Web')=={host+':443':{'Handlers':{'/':{'Proxy':'http://127.0.0.1:8766'}}}}
if not config.exists():
 with config.open('x') as output:json.dump({'origin':origin},output)
 config.chmod(0o644)
subprocess.run(['systemctl','enable','--now','lya-connect'],check=True,capture_output=True,timeout=10)
for attempt in range(20):
 try:
  c=http.client.HTTPConnection('127.0.0.1',8766,timeout=2);c.request('GET','/',headers={'Host':host});r=c.getresponse();body=r.read(65536);assert r.status==200 and b'LYA' in body;c.close();break
 except OSError:time.sleep(.1)
else:raise RuntimeError('service unavailable')
# This may ask the owner to enable tailnet HTTPS; never enable public Funnel.
run=subprocess.run(['tailscale','serve','--bg','--https=443','http://127.0.0.1:8766'],capture_output=True,timeout=15)
assert run.returncode==0
served=json.loads(subprocess.run(['tailscale','serve','status','--json'],check=True,capture_output=True,timeout=5).stdout)
assert not any(served.get('AllowFunnel',{}).values())
print(json.dumps({'activated':True,'origin':origin,'loopback_page':True,'public_funnel':False,'phone_verified':False}))
'''


def operator(program,body=None,timeout=180):
    config=json.loads((ROOT/'desktop/oracle.local.json').read_text())
    key=(ROOT/config['key_file']).resolve();key.relative_to(ROOT)
    assert key.is_file() and (ROOT/'oracle_known_hosts.local').is_file()
    command=['ssh','-T','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=7',
        '-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ForwardAgent=no',
        '-o','ClearAllForwardings=yes','-o','ControlMaster=no','-o','ControlPath=none',
        '-o','UserKnownHostsFile='+str(ROOT/'oracle_known_hosts.local'),'-i',str(key),
        'ubuntu@'+str(ipaddress.ip_address(config['host'])),'sudo -n /usr/bin/python3 -c '+shlex.quote(program)]
    run=subprocess.run(command,input=json.dumps(body).encode() if body is not None else b'',
        capture_output=True,timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if run.returncode:raise RuntimeError('Connection setup failed; raw output withheld. Inspect the separate installation before retrying.')
    return json.loads(run.stdout)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=['stage','network','activate'])
    args=parser.parse_args()
    for program in (STAGE,NETWORK,ACTIVATE):compile(program,'remote-setup','exec')
    if args.operation=='stage':
        names=['cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/ssh_session.py']
        files={name:(ROOT/name).read_text(encoding='utf-8') for name in names};files['cloud/__init__.py']=''
        result=operator(STAGE,{'files':files})
    elif args.operation=='network':result=operator(NETWORK,timeout=240)
    else:
        config=ROOT/'desktop/mobile.local.json'
        if config.exists():raise RuntimeError('Local mobile configuration already exists; inspect it before replacing.')
        result=operator(ACTIVATE)
        from cloud.mobile import checked_origin
        origin=checked_origin(result.pop('origin'))
        with config.open('x',encoding='utf-8') as output:json.dump({'origin':origin,'enabled':True},output)
    out=ROOT/'review/2026-10-10-mobile-connection'/('host-'+args.operation+'.json')
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
