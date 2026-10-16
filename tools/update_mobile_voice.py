"""Owner-authorized private mobile update; never change desktop behavior or pairing."""
import argparse
import ast
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.setup_mobile_connection import operator

STAGE=r'''
import hashlib,json,os,pathlib,subprocess,sys
body=json.load(sys.stdin);base=pathlib.Path('/opt/lya-connect');stage=base/'updates/mobile-voice-20261010'
assert base.stat().st_uid==0 and not base.is_symlink() and not stage.exists()
assert set(body)=={'files','checks'}
allowed={'cloud/__init__.py','cloud/answering.py','cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/ssh_session.py','audio/__init__.py','audio/nvidia_asr.py','audio/voice.py'}
assert set(body['files'])==allowed
before=hashlib.sha256(pathlib.Path('/home/ubuntu/lya/inference.py').read_bytes()).hexdigest()
stage.mkdir(mode=0o755,parents=True)
for name,text in body['files'].items():
 assert isinstance(text,str) and len(text.encode())<150000
 if name.endswith('.py'):compile(text,name,'exec')
 path=stage/name;path.parent.mkdir(mode=0o755,exist_ok=True);path.write_text(text,encoding='utf-8');path.chmod(0o644)
venv=base/'speech-venv'
if not venv.exists():
 subprocess.run(['/usr/bin/python3','-m','venv',str(venv)],check=True,capture_output=True,timeout=45)
 subprocess.run([str(venv/'bin/python'),'-m','pip','install','--disable-pip-version-check','--index-url','https://pypi.org/simple','nvidia-riva-client==2.27.0'],check=True,capture_output=True,timeout=120)
 for path in venv.rglob('*'):
  if not path.is_symlink():path.chmod(0o755 if path.is_dir() or path.parent==venv/'bin' else 0o644)
check=stage/'check.py';check.write_text(body['checks']);check.chmod(0o644)
p=subprocess.run(['sudo','-n','-u','lya-connect',str(base/'venv/bin/python'),'-I',str(check)],capture_output=True,timeout=50)
if p.returncode:raise RuntimeError('Synthetic Linux voice checks failed; not activated')
result=json.loads(p.stdout);assert result['success']
p=subprocess.run(['sudo','-n','-u','ubuntu',str(venv/'bin/python'),'-I','-c',"import riva.client,resource,json;from importlib.metadata import version;print(json.dumps(dict(sdk=version('nvidia-riva-client'),peak_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2))))"],capture_output=True,timeout=15,check=True)
sdk=json.loads(p.stdout);assert sdk['sdk']=='2.27.0'
assert hashlib.sha256(pathlib.Path('/home/ubuntu/lya/inference.py').read_bytes()).hexdigest()==before
print(json.dumps(dict(staged=True,linux_checks=result,sdk_import=sdk,provider_call=False,service_restarted=False)))
'''

ACTIVATE=r'''
import hashlib,hmac,http.client,json,os,pathlib,pwd,subprocess,sys,time
body=json.load(sys.stdin);assert set(body)=={'speech_key'}
key=body['speech_key'];assert key is None or isinstance(key,str) and 16<=len(key)<=4096
base=pathlib.Path('/opt/lya-connect');stage=base/'updates/mobile-voice-20261010';backup=stage/'previous'
assert stage.is_dir() and not stage.is_symlink() and not backup.exists()
account=pwd.getpwnam('ubuntu');credential=pathlib.Path('/home/ubuntu/lya/speech.json')
assert not credential.is_symlink() and not credential.parent.is_symlink()
if key:
 if credential.exists():
  info=credential.stat();assert info.st_uid==account.pw_uid and not info.st_mode & 0o077
  assert hmac.compare_digest(json.loads(credential.read_text())['nvidia_api_key'],key)
 else:
  fd=os.open(credential,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w') as output:json.dump({'nvidia_api_key':key},output)
  os.chown(credential,account.pw_uid,account.pw_gid)
  credential.chmod(0o600)
 key=None;body.clear()
config=pathlib.Path('/etc/lya-connect.json');rule=pathlib.Path('/etc/sudoers.d/lya-connect')
assert not config.is_symlink() and not rule.is_symlink()
settings=json.loads(config.read_text());assert set(settings)=={'origin'}
assert rule.read_text()=='lya-connect ALL=(ubuntu) NOPASSWD: /usr/bin/python3 /home/ubuntu/lya/inference.py\n'
inference=pathlib.Path('/home/ubuntu/lya/inference.py');before=hashlib.sha256(inference.read_bytes()).hexdigest()
auth=pathlib.Path('/var/lib/lya-connect/auth.sqlite');inode=auth.stat().st_ino
backup.mkdir(mode=0o700)
names=['cloud/__init__.py','cloud/answering.py','cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/ssh_session.py','audio/__init__.py','audio/nvidia_asr.py','audio/voice.py','speech.py']
old={}
for name in names:
 path=base/name;assert not path.is_symlink()
 old[name]=path.read_bytes() if path.exists() else None
 if old[name] is not None:
  dest=backup/name;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);dest.write_bytes(old[name])
old_config=config.read_bytes();old_rule=rule.read_bytes()
(backup/'config.json').write_bytes(old_config);(backup/'sudoers').write_bytes(old_rule)
try:
 for name in names:
  path=base/name;path.parent.mkdir(mode=0o755,exist_ok=True)
  content=("import sys\nsys.path.insert(0,'/opt/lya-connect')\nfrom cloud.mobile_speech import main\ntry:main()\nexcept Exception:raise SystemExit('Phone speech unavailable; private details withheld.')\n".encode() if name=='speech.py' else (stage/name).read_bytes())
  temporary=path.with_name(path.name+'.update');temporary.write_bytes(content);temporary.chmod(0o644);os.replace(temporary,path)
 enabled=credential.exists()
 settings['speech_enabled']=enabled
 config.write_text(json.dumps(settings));config.chmod(0o644)
 rule.write_text(old_rule.decode()+'lya-connect ALL=(ubuntu) NOPASSWD: /opt/lya-connect/speech-venv/bin/python -I -u /opt/lya-connect/speech.py\n');rule.chmod(0o440)
 subprocess.run(['/usr/sbin/visudo','-cf',str(rule)],check=True,capture_output=True)
 denied=subprocess.run(['sudo','-n','-u','lya-connect','sudo','-n','-u','ubuntu',str(base/'speech-venv/bin/python'),'-c','raise SystemExit(0)'],capture_output=True,timeout=5)
 assert denied.returncode!=0
 if enabled:
  probe="import sys;sys.path.insert(0,'/opt/lya-connect');from cloud.mobile_speech import credential;assert credential();print('ready')"
  subprocess.run(['sudo','-n','-u','ubuntu',str(base/'speech-venv/bin/python'),'-I','-c',probe],check=True,capture_output=True,timeout=5)
  denied=subprocess.run(['sudo','-n','-u','lya-connect','cat',str(credential)],capture_output=True,timeout=5)
  assert denied.returncode!=0
 subprocess.run(['systemctl','restart','lya-connect'],check=True,capture_output=True,timeout=15)
 host=settings['origin'].split('://')[1]
 for _ in range(30):
  try:
   c=http.client.HTTPConnection('127.0.0.1',8766,timeout=2);c.request('GET','/',headers={'Host':host});r=c.getresponse();html=r.read();assert r.status==200 and b'Verify owner' in html and b'Finish' in html;c.close();break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Service not ready')
 c=http.client.HTTPConnection('127.0.0.1',8766,timeout=2);c.request('POST','/transcribe',b'fake',headers={'Host':host,'Origin':settings['origin'],'Content-Type':'audio/wav','X-LYA-Request':'a'*32});r=c.getresponse();assert r.status==403;r.read();c.close()
 assert auth.stat().st_ino==inode and hashlib.sha256(inference.read_bytes()).hexdigest()==before
 stats=subprocess.run(['systemctl','show','lya-connect','-p','MemoryCurrent','-p','MemoryMax','-p','TasksCurrent','-p','ActiveState'],check=True,capture_output=True,timeout=5).stdout.decode()
 print(json.dumps(dict(deployed=True,speech_enabled=enabled,pairing_preserved=True,inference_unchanged=True,key_read_denied=True if enabled else None,arbitrary_command_denied=True,unsigned_audio_denied=True,service_stats=dict(line.split('=',1) for line in stats.splitlines()),provider_call=False)))
except BaseException:
 for name,content in old.items():
  path=base/name
  if content is None:path.unlink(missing_ok=True)
  else:path.write_bytes(content);path.chmod(0o644)
 config.write_bytes(old_config);config.chmod(0o644);rule.write_bytes(old_rule);rule.chmod(0o440)
 subprocess.run(['systemctl','restart','lya-connect'],capture_output=True,timeout=15)
 raise
'''


def checks():
    source=(ROOT/'test_mobile.py').read_text(encoding='utf-8')
    native=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='NativeMobileChecks')
    base='\n'.join(source.splitlines()[:native.lineno-1]).replace('from test_passkeys import SyntheticPasskeys','')
    voice=(ROOT/'test_mobile_voice.py').read_text(encoding='utf-8')
    return ("import sys,types,json,unittest;sys.path.insert(0,'/opt/lya-connect/updates/mobile-voice-20261010')\n"
            "fixture=types.ModuleType('test_mobile');sys.modules['test_mobile']=fixture\nexec("+repr(base)+",fixture.__dict__)\n"
            +voice+"\nsuite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(fixtures.MobileChecks),unittest.defaultTestLoader.loadTestsFromTestCase(PhoneChecks)])\nr=unittest.TextTestRunner().run(suite)\nprint(json.dumps(dict(tests=r.testsRun,success=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),provider_call=False)))\nraise SystemExit(0 if r.wasSuccessful() else 1)\n")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('stage','activate'))
    parser.add_argument('--copy-approved-speech-key',action='store_true')
    args=parser.parse_args()
    if args.operation=='stage':
        files={name:(ROOT/name).read_text(encoding='utf-8') for name in ('cloud/answering.py','cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/ssh_session.py','audio/nvidia_asr.py','audio/voice.py')}
        files['audio/__init__.py']=files['cloud/__init__.py']=''
        result=operator(STAGE,{'files':files,'checks':checks()},timeout=240)
    else:
        key=None
        if args.copy_approved_speech_key:
            from tools.start_nvidia_lya import configured_key
            key=configured_key()
            if not key:raise RuntimeError('No configured speech key. Nothing uploaded.')
        try:result=operator(ACTIVATE,{'speech_key':key},timeout=60)
        finally:key=None
    out=ROOT/'review/2026-10-10-mobile-voice';out.mkdir(exist_ok=True)
    (out/('host-'+args.operation+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
