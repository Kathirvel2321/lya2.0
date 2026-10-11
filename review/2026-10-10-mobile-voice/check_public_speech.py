"""One generated public fixture through the deployed fixed worker; no human audio."""
import base64
import io
import json
from math import gcd
from pathlib import Path
import sys
import wave

import numpy as np
from scipy.signal import resample_poly

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.setup_mobile_connection import operator

with wave.open(str(ROOT/'review/2026-10-03-voice-conversation/current-public-preview.wav')) as f:
    assert f.getnchannels()==1 and f.getsampwidth()==2
    rate=f.getframerate();samples=np.frombuffer(f.readframes(f.getnframes()),np.int16).astype(np.float32)/32768
divisor=gcd(rate,16000);samples=resample_poly(samples,16000//divisor,rate//divisor)
out=io.BytesIO()
with wave.open(out,'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
    f.writeframes((np.clip(samples,-1,1)*32767).astype('<i2').tobytes())
program=r'''
import json,subprocess,sys,time
body=json.load(sys.stdin)
script="import sys,json,base64,threading;sys.path.insert(0,'/opt/lya-connect');from cloud.mobile_runtime import transcribe;packet=json.load(sys.stdin);print(json.dumps({'text':transcribe(base64.b64decode(packet['audio']),threading.Event())}))"
start=time.monotonic()
p=subprocess.run(['sudo','-n','-u','lya-connect','/opt/lya-connect/venv/bin/python','-I','-c',script],input=json.dumps(body).encode(),capture_output=True,timeout=40)
assert p.returncode==0,'Public fixture speech path failed; private details withheld'
text=json.loads(p.stdout)['text']
assert 'take your time' in text.casefold() and 'what you need' in text.casefold()
stats=subprocess.run(['systemctl','show','lya-connect','-p','MemoryCurrent','-p','TasksCurrent','-p','ActiveState'],check=True,capture_output=True).stdout.decode()
print(json.dumps(dict(success=True,generated_public_audio=True,owner_audio=False,provider_call=True,elapsed_seconds=round(time.monotonic()-start,2),text=text,service_stats=dict(line.split('=',1) for line in stats.splitlines()))))
'''
result=operator(program,{'audio':base64.b64encode(out.getvalue()).decode()},timeout=50)
Path(__file__).with_name('public-speech.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
