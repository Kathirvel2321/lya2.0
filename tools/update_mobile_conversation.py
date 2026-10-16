"""Scoped mobile-only release: synthetic checks before one service restart."""
import ast
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.setup_mobile_connection import operator

FILES=['cloud/answering.py','cloud/evidence.py','cloud/public_search.py','cloud/web_reader.py','cloud/web_research.py','cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/mobile_tts.py','cloud/ssh_session.py']

STAGE=r'''
import json,pathlib,subprocess,sys
body=json.load(sys.stdin);stage=pathlib.Path('/opt/lya-connect/updates/mobile-conversation-20261010')
assert stage.is_dir() and stage.stat().st_uid==0 and not (stage/'previous').exists()
assert set(body['files'])=={'cloud/answering.py','cloud/evidence.py','cloud/public_search.py','cloud/web_reader.py','cloud/web_research.py','cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/mobile_tts.py','cloud/ssh_session.py'}
(stage/'cloud').mkdir(mode=0o755,exist_ok=True);(stage/'cloud/__init__.py').write_text('')
for name,source in body['files'].items():
 assert isinstance(source,str) and len(source.encode())<150000
 if name.endswith('.py'):compile(source,name,'exec')
 p=stage/name;assert not p.is_symlink();p.write_text(source,encoding='utf-8');p.chmod(0o644)
entry=stage/'reply.py';entry.write_text("import sys\nsys.path.insert(0,'/opt/lya-connect/updates/mobile-conversation-20261010')\nfrom cloud.mobile_tts import main\ntry:main()\nexcept Exception:raise SystemExit('LYA reply voice unavailable; details withheld.')\n");entry.chmod(0o644)
check=stage/'check.py';check.write_text(body['checks']);check.chmod(0o644)
p=subprocess.run(['sudo','-n','-u','lya-connect','/opt/lya-connect/venv/bin/python','-I',str(check)],capture_output=True,timeout=50)
assert p.returncode==0,'Synthetic Linux checks failed; not activated'
result=json.loads(p.stdout);assert result['success'];print(json.dumps(result))
'''

ACTIVATE=r'''
import hashlib,http.client,json,os,pathlib,subprocess,sys,time
body=json.load(sys.stdin);names=body['files']
assert set(names)=={'cloud/answering.py','cloud/evidence.py','cloud/public_search.py','cloud/web_reader.py','cloud/web_research.py','cloud/mobile.py','cloud/mobile.html','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/mobile_tts.py','cloud/ssh_session.py'}
base=pathlib.Path('/opt/lya-connect');stage=base/'updates/mobile-conversation-20261010';backup=stage/'previous';assert not backup.exists()
config=pathlib.Path('/etc/lya-connect.json');settings=json.loads(config.read_text());assert settings.get('speech_enabled') is True and not settings.get('reply_voice_enabled')
inference=pathlib.Path('/home/ubuntu/lya/inference.py');digest=hashlib.sha256(inference.read_bytes()).hexdigest()
auth=pathlib.Path('/var/lib/lya-connect/auth.sqlite');inode=auth.stat().st_ino
backup.mkdir(mode=0o700);old={}
for name in names+['reply.py']:
 p=base/name;assert not p.is_symlink();old[name]=p.read_bytes() if p.exists() else None
 if old[name] is not None:
  q=backup/name;q.parent.mkdir(mode=0o700,parents=True,exist_ok=True);q.write_bytes(old[name])
old_config=config.read_bytes();(backup/'config.json').write_bytes(old_config)
try:
 for name in names+['reply.py']:
  p=base/name
  content=(stage/name).read_bytes() if name!='reply.py' else (stage/'reply.py').read_bytes().replace(b'/opt/lya-connect/updates/mobile-conversation-20261010',b'/opt/lya-connect')
  q=p.with_name(p.name+'.update');q.write_bytes(content);q.chmod(0o644);os.replace(q,p)
 settings['reply_voice_enabled']=True;config.write_text(json.dumps(settings));config.chmod(0o644)
 subprocess.run(['systemctl','restart','lya-connect'],capture_output=True,check=True,timeout=15)
 host=settings['origin'].split('://')[1]
 for _ in range(30):
  try:
   c=http.client.HTTPConnection('127.0.0.1',8766,timeout=2);c.request('GET','/',headers={'Host':host});r=c.getresponse();html=r.read();assert r.status==200 and b'Start conversation' in html;c.close();break
  except OSError:time.sleep(.1)
 else:raise RuntimeError('Updated service unavailable')
 assert auth.stat().st_ino==inode and hashlib.sha256(inference.read_bytes()).hexdigest()==digest
 p=subprocess.run(['systemctl','show','lya-connect','-p','MemoryMax','-p','TasksMax','-p','ActiveState'],capture_output=True,check=True)
 print(json.dumps(dict(deployed=True,pairing_preserved=True,inference_unchanged=True,credential_files_unchanged=True,service=dict(line.split('=',1) for line in p.stdout.decode().splitlines()),provider_call=False)))
except BaseException:
 for name,content in old.items():
  p=base/name
  if content is None:p.unlink(missing_ok=True)
  else:p.write_bytes(content);p.chmod(0o644)
 config.write_bytes(old_config);config.chmod(0o644);subprocess.run(['systemctl','restart','lya-connect'],capture_output=True,timeout=15)
 raise
'''


def checks():
    source=(ROOT/'test_mobile.py').read_text(encoding='utf-8')
    native=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='NativeMobileChecks')
    base='\n'.join(source.splitlines()[:native.lineno-1]).replace('from test_passkeys import SyntheticPasskeys','')
    voice=(ROOT/'test_mobile_voice.py').read_text(encoding='utf-8')
    conversation=(ROOT/'test_mobile_conversation.py').read_text(encoding='utf-8')
    return ("import sys,types,json,unittest;sys.path.insert(0,'/opt/lya-connect/updates/mobile-conversation-20261010')\n"
        "fixture=types.ModuleType('test_mobile');sys.modules['test_mobile']=fixture\nexec("+repr(base)+",fixture.__dict__)\n"
        "voice=types.ModuleType('test_mobile_voice');sys.modules['test_mobile_voice']=voice\nexec("+repr(voice)+",voice.__dict__)\n"
        +conversation+"\nsuite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (fixtures.MobileChecks,voice.PhoneChecks,ConversationChecks))\nr=unittest.TextTestRunner().run(suite)\nprint(json.dumps(dict(tests=r.testsRun,success=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),provider_call=False)))\nraise SystemExit(0 if r.wasSuccessful() else 1)\n")


if __name__=='__main__':
    operation=sys.argv[1];assert operation in ('stage','activate')
    if operation=='stage':result=operator(STAGE,{'files':{f:(ROOT/f).read_text(encoding='utf-8') for f in FILES},'checks':checks()},timeout=75)
    else:result=operator(ACTIVATE,{'files':FILES},timeout=40)
    (ROOT/'review/2026-10-10-mobile-conversation'/('host-'+operation+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
