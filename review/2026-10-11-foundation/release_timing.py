"""Stage fake Linux timing checks, then atomically release only mobile.py."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tools.setup_mobile_connection import operator

STAGE=r'''
import hashlib,json,pathlib,subprocess,sys
body=json.load(sys.stdin)
base=pathlib.Path('/opt/lya-connect');stage=base/'updates/timing-20261011'
assert not stage.exists() and not stage.is_symlink()
assert hashlib.sha256((base/'cloud/mobile.py').read_bytes()).hexdigest()==body['expected']
compile(body['source'],'mobile.py','exec');compile(body['checks'],'check.py','exec')
stage.mkdir(mode=0o755);(stage/'cloud').mkdir(mode=0o755)
for name,source in {'cloud/__init__.py':'','cloud/mobile.py':body['source'],'check.py':body['checks']}.items():
 p=stage/name;p.write_text(source,encoding='utf-8');p.chmod(0o644)
check=subprocess.run(['sudo','-n','-u','lya-connect','/opt/lya-connect/venv/bin/python','-I',str(stage/'check.py')],
 capture_output=True,timeout=30)
assert check.returncode==0,'Synthetic Linux timing checks failed; live source untouched'
result=json.loads(check.stdout);assert result['success'] and result['tests']==4
print(json.dumps(dict(staged=True,checks=result,source_sha256=hashlib.sha256((stage/'cloud/mobile.py').read_bytes()).hexdigest(),live_changed=False)))
'''

ACTIVATE=r'''
import hashlib,http.client,json,os,pathlib,subprocess,sys,time
body=json.load(sys.stdin);base=pathlib.Path('/opt/lya-connect');stage=base/'updates/timing-20261011'
target=base/'cloud/mobile.py';assert not target.is_symlink() and not target.parent.is_symlink()
assert hashlib.sha256(target.read_bytes()).hexdigest()==body['expected']
assert hashlib.sha256((stage/'cloud/mobile.py').read_bytes()).hexdigest()==body['new']
assert not (stage/'previous.py').exists()
protected=[base/name for name in ('cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/mobile_tts.py')]
protected += [pathlib.Path('/home/ubuntu/lya/inference.py'),pathlib.Path('/etc/lya-connect.json'),pathlib.Path('/etc/systemd/system/lya-connect.service')]
before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
auth=pathlib.Path('/var/lib/lya-connect/auth.sqlite');inode=auth.stat().st_ino
previous=target.read_bytes();backup=stage/'previous.py';backup.write_bytes(previous);backup.chmod(0o600)
host=json.loads(pathlib.Path('/etc/lya-connect.json').read_text())['origin'].split('://')[1]
def install(content):
 p=target.with_name('mobile.py.timing-update');assert not p.exists() and not p.is_symlink()
 p.write_bytes(content);p.chmod(0o644);os.replace(p,target)
def ready():
 for attempt in range(30):
  try:
   c=http.client.HTTPConnection('127.0.0.1',8766,timeout=2)
   c.request('POST','/session','{}',headers={'Host':host,'Origin':'https://'+host,'Content-Type':'application/json'})
   r=c.getresponse();raw=r.read();timing=r.getheader('Server-Timing');c.close()
   assert r.status==403 and json.loads(raw).get('error') and timing.startswith('request;dur=')
   return
  except OSError:time.sleep(.1)
 raise RuntimeError('Timing release health check failed')
try:
 install((stage/'cloud/mobile.py').read_bytes())
 subprocess.run(['systemctl','restart','lya-connect'],capture_output=True,check=True,timeout=15)
 ready()
 assert auth.stat().st_ino==inode
 assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 result=subprocess.run(['systemctl','show','lya-connect','-p','MemoryCurrent','-p','MemoryMax','-p','ActiveState'],capture_output=True,check=True,timeout=5)
 print(json.dumps(dict(deployed=True,one_restart=True,pairing_file_preserved=True,protected_sources_unchanged=True,
  unsigned_session_rejected=True,timing_header_present=True,provider_call=False,
  service=dict(line.split('=',1) for line in result.stdout.decode().splitlines() if '=' in line))))
except BaseException:
 install(previous);subprocess.run(['systemctl','restart','lya-connect'],capture_output=True,timeout=15)
 raise
'''


def checks():
    source=(ROOT/'test_mobile.py').read_text(encoding='utf-8')
    native=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='NativeMobileChecks')
    base='\n'.join(source.splitlines()[:native.lineno-1]).replace('from test_passkeys import SyntheticPasskeys','')
    voice=(ROOT/'test_mobile_voice.py').read_text(encoding='utf-8')
    sound=next(n for n in ast.parse(voice).body if isinstance(n,ast.FunctionDef) and n.name=='sound')
    sound_source=ast.get_source_segment(voice,sound)
    timing=(ROOT/'test_mobile_timing.py').read_text(encoding='utf-8')
    return ("import sys,types,json,unittest;sys.path.insert(0,'/opt/lya-connect/updates/timing-20261011')\n"
        "fixture=types.ModuleType('test_mobile');sys.modules['test_mobile']=fixture\nexec("+repr(base)+",fixture.__dict__)\n"
        "voice=types.ModuleType('test_mobile_voice');sys.modules['test_mobile_voice']=voice\nexec("+repr('import io,wave\n'+sound_source)+",voice.__dict__)\n"
        "timing=types.ModuleType('test_mobile_timing');sys.modules['test_mobile_timing']=timing\nexec("+repr(timing)+",timing.__dict__)\n"
        "r=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(timing.TimingChecks))\n"
        "print(json.dumps(dict(success=r.wasSuccessful(),tests=r.testsRun,provider_call=False)))\nraise SystemExit(0 if r.wasSuccessful() else 1)\n")


if __name__=='__main__':
    operation=sys.argv[1];assert operation in ('stage','activate')
    source=(ROOT/'cloud/mobile.py').read_bytes()
    expected=json.loads((HERE/'readiness.json').read_text())['deployed_source']['hashes']['cloud/mobile.py']
    if operation=='stage':
        result=operator(STAGE,{'expected':expected,'source':source.decode('utf-8'),'checks':checks()},timeout=45)
    else:
        staged=json.loads((HERE/'stage.json').read_text())
        digest=hashlib.sha256(source).hexdigest();assert digest==staged['source_sha256']
        result=operator(ACTIVATE,{'expected':expected,'new':digest},timeout=40)
    (HERE/(operation+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
