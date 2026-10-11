"""Public generated speech only; checked TTS module replacement, no service restart."""
import json
from pathlib import Path
from tools.setup_mobile_connection import operator
PROGRAM=r'''
import json,pathlib,subprocess,sys
base=pathlib.Path('/opt/lya-connect');stage=base/'updates/mobile-conversation-20261010';body=json.load(sys.stdin)
assert (base/'cloud/mobile_tts.py').read_bytes()==(stage/'before-tts-chunk.py').read_bytes()
candidate=stage/'cloud/mobile_tts.py';compile(body['source'],'mobile_tts.py','exec');candidate.write_text(body['source']);candidate.chmod(0o644)
probe=r"""
import json,sys,resource,time,io,wave,pathlib
sys.path.insert(0,'/opt/lya-connect/updates/mobile-conversation-20261010')
from piper import PiperVoice
original=PiperVoice.synthesize;spans=[]
def checked(self,text,*args,**kwargs):
 assert len(text)<=81;spans.append(len(text));return original(self,text,*args,**kwargs)
PiperVoice.synthesize=checked
from cloud.mobile_tts import synthesize
start=time.monotonic();audio=synthesize('public voice memory test without punctuation '*24)
with wave.open(io.BytesIO(audio)) as f:assert f.getframerate()==22050 and f.getnchannels()==1
cg=pathlib.Path('/sys/fs/cgroup')/pathlib.Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
print(json.dumps(dict(success=True,largest_span=max(spans),spans=len(spans),wav_bytes=len(audio),elapsed_seconds=round(time.monotonic()-start,2),peak_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),cgroup_peak_bytes=int((cg/'memory.peak').read_text()),enforced_memory_limit_mib=192,provider_call=False)))
"""
p=subprocess.run(['systemd-run','--quiet','--wait','--pipe','--collect','--unit=lya-amy-bounded-sentence-probe-20261010','-p','User=lya-connect','-p','MemoryMax=192M','-p','CPUQuota=100%','-p','TasksMax=12','-p','RuntimeMaxSec=35','/opt/lya-connect/tts-venv/bin/python','-I','-c',probe],capture_output=True,timeout=45)
if p.returncode:
 print(json.dumps(dict(success=False,returncode=p.returncode)));raise SystemExit()
result=json.loads(p.stdout);assert result['success']
target=base/'cloud/mobile_tts.py';temp=target.with_suffix('.next');temp.write_text(body['source']);temp.chmod(0o644);temp.replace(target)
result['hot_update']=True;print(json.dumps(result))
'''
if __name__=='__main__':
    result=operator(PROGRAM,{'source':Path('cloud/mobile_tts.py').read_text()},timeout=55)
    Path('review/2026-10-10-mobile-conversation/amy-sentence-resource-check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
