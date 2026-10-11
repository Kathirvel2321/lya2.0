"""Content-free stage timing checks with synthetic auth, audio and providers only."""
import base64
import http.client
import json
import re
import threading
import time
import unittest

import test_mobile as fixtures
from test_mobile_voice import sound


class TimingChecks(unittest.TestCase):
    setUp=fixtures.MobileChecks.setUp
    response=fixtures.MobileChecks.response
    start_pair=fixtures.MobileChecks.start_pair
    pair=fixtures.MobileChecks.pair

    def start_http(self):
        token=self.pair()
        self.http=fixtures.PrivateHTTP(('127.0.0.1',0),self.app)
        thread=threading.Thread(target=self.http.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(self.http.shutdown(),self.http.server_close(),thread.join(2)))
        return token

    def request(self,token,path,data,request_id='c'*32):
        connection=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
        headers={'Host':'lya.synthetic.ts.net','Origin':fixtures.ORIGIN,
                 'Content-Type':'application/json','Cookie':fixtures.COOKIE+'='+token}
        if path=='/transcribe':
            headers.update({'Content-Type':'audio/wav','X-LYA-Request':request_id});body=data
        else:body=json.dumps(data)
        started=time.perf_counter()
        connection.request('POST',path,body,headers)
        reply=connection.getresponse();first=(time.perf_counter()-started)*1000
        raw=reply.read();elapsed=(time.perf_counter()-started)*1000
        header=reply.getheader('Server-Timing');connection.close()
        self.assertRegex(header,r'^(?:(?:asr|inference|tts|request);dur=\d+\.\d{3})(?:, (?:asr|inference|tts|request);dur=\d+\.\d{3})*$')
        values={name:float(value) for name,value in re.findall(r'(\w+);dur=([\d.]+)',header)}
        self.assertTrue(all(0<=n<=elapsed+1 for n in values.values()))
        return reply.status,json.loads(raw),values,first,elapsed

    def test_spoken_stages_and_content_free_header(self):
        token=self.start_http()
        self.app.speaker=lambda text,cancel:base64.b64encode(sound(rate=22050)).decode()
        code,body,values,_,_=self.request(token,'/chat',{'id':'a'*32,'text':'FAKE_PRIVATE_MARKER','spoken':True})
        self.assertEqual(code,200);self.assertIn('audio',body)
        self.assertEqual(set(values),{'inference','tts','request'})
        self.assertGreaterEqual(values['request']+.001,values['inference']+values['tts'])
        self.assertNotIn(b'FAKE_PRIVATE_MARKER',self.store.path.read_bytes())
        self.assertIsNone(getattr(self.app.timings,'values',None))

    def test_failures_cancellation_and_voice_fallback_are_measured(self):
        token=self.start_http()
        def fail(messages,cancel):raise RuntimeError('FAKE_SECRET')
        self.app.infer=fail
        code,body,values,_,_=self.request(token,'/chat',{'id':'a'*32,'text':'fake'})
        self.assertEqual(code,503);self.assertEqual(set(values),{'inference','request'})
        self.assertNotIn('FAKE_SECRET',json.dumps(body))
        def cancel(messages,event):event.set();return 'discard'
        self.app.infer=cancel
        code,_,values,_,_=self.request(token,'/chat',{'id':'b'*32,'text':'fake'})
        self.assertEqual(code,409);self.assertIn('inference',values)
        self.app.infer=lambda *args:'Synthetic reply.'
        self.app.speaker=lambda *args:(_ for _ in ()).throw(RuntimeError('FAKE_SECRET'))
        code,body,values,_,_=self.request(token,'/chat',{'id':'d'*32,'text':'fake','spoken':True})
        self.assertEqual(code,200);self.assertTrue(body['voice_unavailable']);self.assertIn('tts',values)

    def test_transcription_and_auth_rejection_do_not_reuse_other_stage_timings(self):
        token=self.start_http();self.app.transcriber=lambda *args:'Synthetic words'
        code,_,values,_,_=self.request(token,'/transcribe',sound())
        self.assertEqual(code,200);self.assertEqual(set(values),{'asr','request'})
        code,_,values,_,_=self.request('x'*43,'/chat',{'id':'a'*32,'text':'fake'})
        self.assertEqual(code,403);self.assertEqual(set(values),{'request'})
        code,_,values,_,_=self.request(token,'/chat',{'id':'b'*32,'text':'fake'})
        self.assertEqual(code,200);self.assertEqual(set(values),{'inference','request'})

    def test_timers_are_thread_local_and_monotonic(self):
        from unittest.mock import patch
        self.app.timings.values={}
        seen=[]
        def worker():
            seen.append(getattr(self.app.timings,'values',None))
            self.app.timings.values={'tts':42}
        thread=threading.Thread(target=worker);thread.start();thread.join(2)
        self.assertEqual(seen,[None]);self.assertEqual(self.app.timings.values,{})
        with patch('cloud.mobile.time.perf_counter',side_effect=[10,10.025]):
            with self.app.measure('inference'):pass
        self.assertAlmostEqual(self.app.timings.values['inference'],25)


if __name__=='__main__':unittest.main()
