"""Replace only the approved mobile presentation; preserve script and service state."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.setup_mobile_connection import operator

PROGRAM=r'''
import hashlib,http.client,json,os,pathlib,re,subprocess,sys
body=json.load(sys.stdin)
assert set(body)=={'html','sha256'}
source=body['html'];assert isinstance(source,str) and len(source.encode())<100000
assert hashlib.sha256(source.encode()).hexdigest()==body['sha256']
base=pathlib.Path('/opt/lya-connect');page=base/'cloud/mobile.html'
assert page.is_file() and not page.is_symlink() and page.stat().st_uid==0
old=page.read_bytes();previous=old.decode('utf-8')
assert 'async function beginConversation' in source
assert 'window.addEventListener(\'pagehide\'' in source
assert 'id="consent"' not in source and 'id="conversation"' not in source
assert 'id="stop"' not in source and 'id="send"' not in source
assert 'id="talk"' not in source and 'id="composer"' not in source
assert source.count('nonce="__NONCE__"')==previous.count('nonce="__NONCE__"')==2
for marker in ('class="panel"','class="dots diamond"','class="dots thought"','class="dots wave"'):
 assert marker in source
config=pathlib.Path('/etc/lya-connect.json');settings=json.loads(config.read_text())
assert settings.get('speech_enabled') is True and settings.get('reply_voice_enabled') is True
pid=lambda:subprocess.run(['systemctl','show','lya-connect','-p','MainPID','--value'],capture_output=True,check=True).stdout.strip()
before_pid=pid();assert before_pid!=b'0'
auth=pathlib.Path('/var/lib/lya-connect/auth.sqlite');before_inode=auth.stat().st_ino
names=['cloud/mobile.py','cloud/mobile_runtime.py','cloud/mobile_speech.py','cloud/mobile_tts.py','cloud/ssh_session.py','reply.py']
hashes={name:hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names}
inference=pathlib.Path('/home/ubuntu/lya/inference.py');inference_hash=hashlib.sha256(inference.read_bytes()).hexdigest()
backup=base/'updates/mobile-visual-20261011'
assert not backup.exists();backup.mkdir(mode=0o700)
(backup/'previous.html').write_bytes(old);(backup/'previous.html').chmod(0o600)
try:
 temporary=page.with_name(page.name+'.visual-update')
 assert not temporary.exists()
 temporary.write_text(source,encoding='utf-8');temporary.chmod(0o644);os.replace(temporary,page)
 c=http.client.HTTPConnection('127.0.0.1',8766,timeout=5)
 c.request('GET','/',headers={'Host':settings['origin'].split('://')[1]})
 r=c.getresponse();served=r.read().decode('utf-8');assert r.status==200
 assert re.sub(r'nonce="[^"]+"','nonce="__NONCE__"',served)==source
 assert r.getheader('Cache-Control')=='no-store'
 assert r.getheader('Permissions-Policy')=='camera=(), microphone=(self)'
 assert "frame-ancestors 'none'" in r.getheader('Content-Security-Policy');c.close()
 assert pid()==before_pid and auth.stat().st_ino==before_inode
 assert all(hashlib.sha256((base/name).read_bytes()).hexdigest()==value for name,value in hashes.items())
 assert hashlib.sha256(inference.read_bytes()).hexdigest()==inference_hash
except BaseException:
 temporary=page.with_name(page.name+'.visual-rollback');temporary.write_bytes(old);temporary.chmod(0o644);os.replace(temporary,page)
 raise
print(json.dumps(dict(deployed=True,page_sha256=body['sha256'],voice_first=True,manual_controls_removed=True,
 service_restarted=False,auth_file_preserved=True,runtime_sources_unchanged=True,inference_unchanged=True,
 backup_created=True,no_store=True,camera_disabled=True,provider_call=False)))
'''

if __name__=='__main__':
    page=(ROOT/'cloud/mobile.html').read_text(encoding='utf-8')
    compile(PROGRAM,'remote-page-update','exec')
    result=operator(PROGRAM,{'html':page,'sha256':hashlib.sha256(page.encode()).hexdigest()},timeout=25)
    Path(__file__).with_name('page-update.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))
