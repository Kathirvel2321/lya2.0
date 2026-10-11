"""Full fake-session public reply under the unchanged deployed service cap."""
import json
from pathlib import Path
from tools.setup_mobile_connection import operator
PROGRAM=r'''
import json,pathlib,subprocess,sys
base=pathlib.Path('/opt/lya-connect');stage=base/'updates/mobile-conversation-20261010';body=json.load(sys.stdin)
assert (base/'cloud/mobile_tts.py').read_bytes()==(stage/'before-tts-chunk.py').read_bytes()
candidate=stage/'cloud/mobile_tts.py';compile(body['source'],'mobile_tts.py','exec');candidate.write_text(body['source']);candidate.chmod(0o644)
probe=r"""
import sys,json,pathlib,time,tempfile,resource
sys.path.insert(0,'/opt/lya-connect/updates/mobile-conversation-20261010')
from cloud.mobile import Connection,AuthStore,digest
from cloud import mobile_runtime
real_exchange=mobile_runtime.exchange
def exchange(command,*args,**kw):
 assert command==['/opt/lya-connect/tts-venv/bin/python','-I','/opt/lya-connect/reply.py']
 return real_exchange(command[:-1]+['/opt/lya-connect/updates/mobile-conversation-20261010/reply.py'],*args,**kw)
mobile_runtime.exchange=exchange
with tempfile.TemporaryDirectory() as folder:
 store=AuthStore(pathlib.Path(folder)/'fake.sqlite');record=dict(data='fake-credential',stamp='fake-stamp');store.credential=lambda:record
 app=Connection('https://lya.synthetic.ts.net',store,lambda *args:'public voice memory test without punctuation '*24,speak=mobile_runtime.speak)
 token='A'*43;app.sessions[digest(token)]=dict(until=time.time()+900,credential=record['data'],stamp=record['stamp'],active=None,history=[],used=set(),owner_until=0)
 start=time.monotonic();answer=app.chat(token,'1'*32,'Public synthetic question',spoken=True)
 assert answer.get('audio') and not answer.get('voice_unavailable')
 cg=pathlib.Path('/sys/fs/cgroup')/pathlib.Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
 print(json.dumps(dict(success=True,elapsed_seconds=round(time.monotonic()-start,2),encoded_audio_bytes=len(answer['audio']),cgroup_peak_bytes=int((cg/'memory.peak').read_text()),parent_peak_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),enforced_memory_limit_mib=256,provider_call=False,synthetic_identity=True)))
"""
p=subprocess.run(['systemd-run','--quiet','--wait','--pipe','--collect','--unit=lya-amy-complete-bounded-probe-20261010','-p','User=lya-connect','-p','MemoryMax=256M','-p','CPUQuota=100%','-p','TasksMax=40','-p','RuntimeMaxSec=35','/opt/lya-connect/venv/bin/python','-I','-c',probe],capture_output=True,timeout=45)
if p.returncode:
 print(json.dumps(dict(success=False,returncode=p.returncode,error=p.stderr.decode()[-1000:])));raise SystemExit()
result=json.loads(p.stdout);assert result['success']
target=base/'cloud/mobile_tts.py';temp=target.with_suffix('.next');temp.write_text(body['source']);temp.chmod(0o644);temp.replace(target)
result['hot_update']=True;print(json.dumps(result))
'''
if __name__=='__main__':
    result=operator(PROGRAM,{'source':Path('cloud/mobile_tts.py').read_text()},timeout=55)
    Path('review/2026-10-10-mobile-conversation/final-full-reply-resource-check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))

