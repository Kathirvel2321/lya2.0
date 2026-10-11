"""Measure the real loopback HTTP path with fake providers and temporary auth only."""
import base64
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from test_mobile_timing import TimingChecks
from test_mobile_voice import sound


def summary(values):
    ordered=sorted(values)
    return {'samples':len(values),'p50_ms':round(statistics.median(values),3),
            'p95_ms':round(ordered[math.ceil(.95*len(ordered))-1],3)}


def main():
    check=TimingChecks();check.setUp()
    samples=[]
    try:
        token=check.start_http()
        audio=base64.b64encode(sound(rate=22050)).decode()
        def fail(*args):raise RuntimeError('FAKE_PROVIDER_ERROR')
        def cancel(messages,event):event.set();return 'discarded fake answer'
        for scenario in ('text','spoken','asr','provider_failure','cancelled','voice_fallback'):
            for _ in range(8):
                rid=f'{len(samples)+1:032x}'
                check.app.infer=fail if scenario=='provider_failure' else cancel if scenario=='cancelled' else lambda *args:'Synthetic public fixture.'
                check.app.speaker=fail if scenario=='voice_fallback' else lambda *args:audio
                check.app.transcriber=lambda *args:'Synthetic public question.'
                path='/transcribe' if scenario=='asr' else '/chat'
                data=sound() if scenario=='asr' else {'id':rid,'text':'Synthetic public fixture.',
                    'spoken':scenario in ('spoken','voice_fallback')}
                code,body,stages,first,total=check.request(token,path,data,request_id=rid)
                expected=503 if scenario=='provider_failure' else 409 if scenario=='cancelled' else 200
                assert code==expected,(scenario,code)
                assert bool(body.get('voice_unavailable'))==(scenario=='voice_fallback')
                samples.append({'scenario':scenario,'status':code,'voice_unavailable':bool(body.get('voice_unavailable')),
                    'headers_ms':round(first,3),'http_total_ms':round(total,3),'server_ms':stages})
    finally:check.doCleanups()
    groups={name:{'http_total':summary([s['http_total_ms'] for s in samples if s['scenario']==name]),
        'http_headers':summary([s['headers_ms'] for s in samples if s['scenario']==name])}
        for name in sorted({s['scenario'] for s in samples})}
    result={'date':'2026-10-11','mode':'synthetic_loopback','providers_called':False,'real_audio':False,
        'counts':{'attempts':len(samples),'http_2xx':sum(200<=s['status']<300 for s in samples),
            'http_errors':sum(s['status']>=400 for s in samples),'voice_fallback':sum(s['voice_unavailable'] for s in samples)},
        'conditions':{'network':'loopback','model_state':'fake callbacks; cold/warm model latency unmeasured',
            'excluded':['endpointing','real upload/download','provider latency','audio playback','owner accuracy']},
        'scenarios':groups,'samples':samples}
    serialized=json.dumps(result,indent=2)
    assert not any(marker in serialized for marker in ('Synthetic public','FAKE_PROVIDER_ERROR','__Host-lya'))
    assert all(set(s)=={'scenario','status','voice_unavailable','headers_ms','http_total_ms','server_ms'} for s in samples)
    assert result['counts']=={'attempts':48,'http_2xx':32,'http_errors':16,'voice_fallback':8}
    Path(__file__).with_name('baseline.json').write_text(serialized+'\n',encoding='utf-8')
    print(json.dumps({'success':True,'counts':result['counts'],'scenarios':groups,'real_latency_qualified':False}))


if __name__=='__main__':main()
