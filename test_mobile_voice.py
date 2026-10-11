"""Synthetic mobile sessions, audio and provider calls; never real owner material."""
import base64
import io
import json
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import wave

import test_mobile as fixtures
from test_mobile import ORIGIN,COOKIE,BINDING


def sound(rate=16000,frames=1600):
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(b'\0\0'*frames)
    return out.getvalue()


class PhoneChecks(unittest.TestCase):
    setUp=fixtures.MobileChecks.setUp
    response=fixtures.MobileChecks.response
    start_pair=fixtures.MobileChecks.start_pair
    pair=fixtures.MobileChecks.pair

    def test_restoration_never_renews_expiry_and_owner_needs_fresh_signed_proof(self):
        token=self.pair();deadline=self.app.session(token)['until']
        self.now+=50
        self.assertEqual(self.app.status(token)['expires_in'],850)
        self.assertFalse(self.app.status(token)['owner_verified'])
        with self.assertRaises(PermissionError):self.app.begin('owner')
        t=self.app.begin('owner',session_token=token)['ticket']
        with self.assertRaises(Exception):self.app.complete(t,self.response(t,flags=9))
        self.assertFalse(self.app.status(token)['owner_verified'])
        t=self.app.begin('owner',session_token=token)['ticket']
        data,cookie=self.app.complete(t,self.response(t))
        self.assertIsNone(cookie);self.assertTrue(data['owner_verified'])
        self.assertEqual(data['scope'],'public_chat');self.assertEqual(self.app.session(token)['until'],deadline)
        with self.assertRaises(PermissionError):self.app.complete(t,{})
        self.now+=301;self.assertFalse(self.app.status(token)['owner_verified'])
        self.now=deadline
        with self.assertRaises(PermissionError):self.app.status(token)

    def test_owner_challenge_is_bound_to_original_live_session_and_revocation(self):
        token=self.pair()
        t=self.app.begin('owner',session_token=token)['ticket'];response=self.response(t)
        self.app.logout(token)
        with self.assertRaises(PermissionError):self.app.complete(t,response)
        t=self.app.begin('login')['ticket'];_,token=self.app.complete(t,self.response(t))
        t=self.app.begin('owner',session_token=token)['ticket'];response=self.response(t)
        self.store.control('revoke',BINDING,self.now)
        with self.assertRaises(PermissionError):self.app.complete(t,response)

    def test_bounded_transcription_is_review_only_and_not_stored(self):
        token=self.pair();calls=[]
        self.app.transcriber=lambda audio,cancel:calls.append(audio) or 'SYNTHETIC_REVIEW_WORDS'
        self.assertTrue(self.app.status(token)['voice_available'])
        self.assertEqual(self.app.transcribe(token,'a'*32,sound())['text'],'SYNTHETIC_REVIEW_WORDS')
        self.assertEqual(calls,[sound()]);self.assertEqual(self.calls,[])
        self.assertEqual(self.app.session(token)['history'],[])
        self.assertNotIn(b'SYNTHETIC_REVIEW_WORDS',self.store.path.read_bytes())
        with self.assertRaises(PermissionError):self.app.transcribe(token,'a'*32,sound())
        for bad in (b'fake',sound(rate=8000),sound(frames=1),sound(frames=1920001),sound()[:-1]):
            with self.assertRaises(ValueError):self.app.transcribe(token,'b'*32,bad)
        self.assertEqual(len(calls),1)
        with self.assertRaises(PermissionError):self.app.transcribe(None,'c'*32,sound())
        self.assertEqual(len(calls),1)

    def test_stop_and_logout_drop_late_transcripts(self):
        for logout in (False,True):
            token=self.pair() if not self.store.credential() else self.login()
            ready=threading.Event();errors=[]
            def provider(audio,cancel):
                ready.set();cancel.wait(2);return 'Late words'
            self.app.transcriber=provider
            def run():
                try:self.app.transcribe(token,'d'*32,sound())
                except Exception as e:errors.append(e)
            thread=threading.Thread(target=run);thread.start();self.assertTrue(ready.wait(2))
            if logout:self.app.logout(token)
            else:self.app.stop(token,'d'*32)
            thread.join(3);self.assertFalse(thread.is_alive());self.assertTrue(errors)

    def login(self):
        t=self.app.begin('login')['ticket'];return self.app.complete(t,self.response(t))[1]

    def test_daily_voice_cap_survives_service_restart_without_retaining_audio(self):
        for _ in range(100):self.store.reserve_speech(self.now)
        from cloud.mobile import AuthStore
        store=AuthStore(self.store.path)
        with self.assertRaises(PermissionError):store.reserve_speech(self.now)
        store.reserve_speech(self.now+86400)

    def test_http_audio_requires_origin_cookie_and_valid_wav(self):
        from cloud.mobile import PrivateHTTP
        import http.client
        server=PrivateHTTP(('127.0.0.1',0),self.app)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(server.shutdown(),server.server_close(),thread.join(2)))
        def request(path,body,headers):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            c.request('POST',path,body,headers);r=c.getresponse();code=r.status;data=r.read();c.close();return code,json.loads(data)
        headers={'Host':'lya.synthetic.ts.net','Origin':ORIGIN,'Content-Type':'audio/wav','X-LYA-Request':'f'*32}
        self.app.transcriber=lambda audio,cancel:'Synthetic words'
        self.assertEqual(request('/transcribe',sound(),headers)[0],403)
        token=self.pair();headers['Cookie']=COOKIE+'='+token
        self.assertEqual(request('/transcribe',sound(),dict(headers,Origin='https://evil.test'))[0],403)
        self.assertEqual(request('/transcribe',b'fake',headers)[0],400)
        self.assertEqual(request('/transcribe',sound(),headers)[1]['text'],'Synthetic words')
        headers['Content-Type']='application/json'
        self.assertEqual(request('/session',b'{}',headers)[1]['scope'],'public_chat')

    def test_worker_and_runtime_never_accept_provider_or_executable_from_phone(self):
        from cloud import mobile_speech,mobile_runtime
        with patch.object(mobile_runtime,'exchange',return_value=SimpleNamespace(returncode=0,stdout='{"text":"ok"}')) as exchange:
            self.assertEqual(mobile_runtime.transcribe(sound(),threading.Event()),'ok')
        args,kwargs=exchange.call_args
        self.assertEqual(args[0],['sudo','-n','-u','ubuntu','/opt/lya-connect/speech-venv/bin/python','-I','-u','/opt/lya-connect/speech.py'])
        self.assertEqual(set(json.loads(args[1])),{'audio'});self.assertNotIn('close_stdin',kwargs)
        for fields in ({'audio':base64.b64encode(sound()).decode(),'api_key':'FAKE_ONLY'}, {'audio':'broken'}):
            with patch.object(mobile_speech.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(json.dumps(fields).encode()+b'\n'))),patch.object(mobile_speech,'credential') as key:
                with self.assertRaises(Exception):mobile_speech.main()
                key.assert_not_called()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'speech.json';path.write_text('{"nvidia_api_key":"FAKE_ONLY_NOT_A_REAL_KEY"}')
            with patch.object(mobile_speech,'CONFIG',path),patch.object(mobile_speech.os,'O_NOFOLLOW',0,create=True),patch.object(mobile_speech.os,'getuid',return_value=123,create=True),patch.object(mobile_speech.os,'fstat',return_value=SimpleNamespace(st_uid=123,st_mode=stat.S_IFREG|0o600)):
                self.assertEqual(mobile_speech.credential(),'FAKE_ONLY_NOT_A_REAL_KEY')
                with patch.object(mobile_speech.os,'fstat',return_value=SimpleNamespace(st_uid=123,st_mode=stat.S_IFREG|0o644)):
                    with self.assertRaises(PermissionError):mobile_speech.credential()
