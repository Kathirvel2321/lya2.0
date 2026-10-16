"""Synthetic WebAuthn, temporary metadata/stores and loopback HTTP only."""
import hashlib
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fido2.cose import ES256
from fido2.utils import websafe_decode,websafe_encode
from fido2.webauthn import AttestedCredentialData,AttestationObject,AuthenticatorData,CollectedClientData
from cloud.mobile import AuthStore,Connection,PrivateHTTP,checked_origin,COOKIE
from test_passkeys import SyntheticPasskeys

ORIGIN='https://lya.synthetic.ts.net'
BINDING='a'*64


class MobileChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.store=AuthStore(Path(temp.name)/'auth.sqlite')
        self.now=10000.
        self.calls=[]
        self.app=Connection(ORIGIN,self.store,lambda messages,cancelled:self.calls.append(messages) or 'Synthetic reply.',clock=lambda:self.now)
        self.key=ec.generate_private_key(ec.SECP256R1())
        self.credential=AttestedCredentialData.create(bytes(16),b'synthetic-mobile-key',ES256.from_cryptography_key(self.key.public_key()))

    def response(self,ticket,*,origin=ORIGIN,rp='lya.synthetic.ts.net',flags=None,counter=0,handle=None,key=None,challenge=None,cross=False):
        c=self.app.ceremonies[ticket];create=c['mode']=='pair'
        client=CollectedClientData.create('webauthn.create' if create else 'webauthn.get',
            challenge or websafe_decode(c['state']['challenge']),origin,cross_origin=cross)
        auth=AuthenticatorData.create(hashlib.sha256(rp.encode()).digest(),
            flags if flags is not None else 0x4d if create else 0x0d,counter,self.credential if create else b'')
        response={'clientDataJSON':websafe_encode(bytes(client))}
        if create:response['attestationObject']=websafe_encode(bytes(AttestationObject.create('none',auth,{})))
        else:response.update(authenticatorData=websafe_encode(bytes(auth)),
            signature=websafe_encode((key or self.key).sign(bytes(auth)+client.hash,ec.ECDSA(hashes.SHA256()))),
            userHandle=websafe_encode(c['handle'] if handle is None else handle))
        return dict(id=websafe_encode(self.credential.credential_id),rawId=websafe_encode(self.credential.credential_id),
                    type='public-key',response=response)

    def start_pair(self):
        self.invite=self.store.control('invite',BINDING,self.now)['token']
        return self.app.begin('pair',self.invite)['ticket']

    def pair(self,counter=0):
        t=self.start_pair()
        body,cookie=self.app.complete(t,self.response(t))
        self.assertTrue(body['confirm']);self.assertIsNone(cookie);self.assertIsNone(self.store.credential())
        return self.app.complete(t,self.response(t,counter=counter))[1]

    def test_pair_requires_invite_signature_confirmation_and_consumes_once(self):
        with self.assertRaises(PermissionError):self.app.begin('pair','x'*43)
        token=self.pair()
        self.assertTrue(self.app.session(token))
        self.assertFalse(self.store.invited(self.invite,self.now))
        self.assertEqual(self.store.control('invite',BINDING,self.now),{'paired':True})
        with self.assertRaises(PermissionError):self.store.control('revoke','b'*64,self.now)

    def test_wrong_origin_rp_challenge_presence_verification_cross_origin_rejected(self):
        cases=[{'origin':'https://evil.test'},{'rp':'evil.test'},{'challenge':b'x'*32},
               {'flags':0x49},{'flags':0x4c},{'cross':True}]
        for case in cases:
            with self.subTest(case=case):
                t=self.start_pair()
                with self.assertRaises(Exception):self.app.complete(t,self.response(t,**case))
                self.assertIsNone(self.store.credential())

    def test_bad_confirmation_never_registers_and_expiry_loses_authority(self):
        t=self.start_pair();self.app.complete(t,self.response(t))
        with self.assertRaises(Exception):self.app.complete(t,self.response(t,key=ec.generate_private_key(ec.SECP256R1())))
        self.assertIsNone(self.store.credential())
        t=self.start_pair();response=self.response(t);self.now+=121
        with self.assertRaises(PermissionError):self.app.complete(t,response)
        self.assertIsNone(self.store.credential())
        self.now+=60
        self.assertFalse(self.store.invited(self.invite,self.now))

    def test_signin_bad_proof_and_counter_replay_fail_closed(self):
        self.pair(counter=1)
        for case in ({'handle':b'other'},{'flags':0x09},{'flags':0x15},{'counter':1},
                     {'key':ec.generate_private_key(ec.SECP256R1())},{'origin':'http://localhost'}):
            with self.subTest(case=case):
                t=self.app.begin('login')['ticket']
                bad=dict(counter=2);bad.update(case)
                with self.assertRaises(Exception):self.app.complete(t,self.response(t,**bad))
        t=self.app.begin('login')['ticket'];response=self.response(t,counter=2)
        _,token=self.app.complete(t,response)
        with self.assertRaises(PermissionError):self.app.complete(t,response)
        self.assertTrue(self.app.session(token))

    def test_revocation_invalidates_sessions_even_if_same_passkey_is_reenrolled(self):
        token=self.pair()
        t=self.app.begin('login')['ticket'];old_response=self.response(t)
        self.store.control('revoke',BINDING,self.now)
        new=self.pair()
        with self.assertRaises(PermissionError):self.app.session(token)
        with self.assertRaises(PermissionError):self.app.complete(t,old_response)
        self.assertTrue(self.app.session(new))

    def test_public_chat_context_is_bounded_ram_only_and_retries_do_not_repeat(self):
        token=self.pair()
        for i in range(5):self.app.chat(token,f'{i:032x}','SYNTHETIC_TEMPORARY_QUESTION')
        self.assertLessEqual(len(self.calls[-1]),12)
        self.assertIn('public conversation only',self.calls[-1][0]['content'])
        self.assertNotIn(b'SYNTHETIC_TEMPORARY_QUESTION',self.store.path.read_bytes())
        with self.assertRaises(PermissionError):self.app.chat(token,f'{4:032x}','duplicate')
        with self.assertRaises(ValueError):self.app.chat(token,'bad','hello')
        with self.assertRaises(ValueError):self.app.chat(token,'c'*32,'x'*4001)
        restarted=Connection(ORIGIN,self.store,self.app.infer)
        with self.assertRaises(PermissionError):restarted.session(token)

    def test_stop_before_arrival_and_during_inference_and_no_stale_answer(self):
        token=self.pair();rid='d'*32
        self.app.stop(token,rid)
        with self.assertRaises(PermissionError):self.app.chat(token,rid,'late request')
        started=threading.Event();finished=threading.Event();errors=[]
        def infer(messages,cancelled):
            started.set();self.assertTrue(cancelled.wait(2));return 'Stale reply'
        self.app.infer=infer
        def chat():
            try:self.app.chat(token,'e'*32,'hello')
            except Exception as exc:errors.append(exc)
            finally:finished.set()
        thread=threading.Thread(target=chat);thread.start();self.assertTrue(started.wait(2))
        with self.assertRaises(PermissionError):self.app.chat(token,'f'*32,'second')
        self.app.stop(token,'e'*32);self.assertTrue(finished.wait(3));thread.join()
        self.assertIsInstance(errors[0],InterruptedError)
        self.assertEqual(self.app.session(token)['history'],[])

    def test_session_expiry_logout_and_revocation_during_reply(self):
        token=self.pair()
        self.app.infer=lambda messages,cancelled:self.store.control('revoke',BINDING,self.now) and 'stale'
        with self.assertRaises(PermissionError):self.app.chat(token,'a'*32,'hello')
        token=self.pair();self.app.logout(token)
        with self.assertRaises(PermissionError):self.app.session(token)
        t=self.app.begin('login')['ticket'];_,token=self.app.complete(t,self.response(t));self.now+=901
        with self.assertRaises(PermissionError):self.app.session(token)

    def test_http_boundaries_cookie_and_no_store(self):
        http=PrivateHTTP(('127.0.0.1',0),self.app)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        self.addCleanup(lambda:(http.shutdown(),http.server_close(),thread.join(2)))
        import http.client as http_client
        def request(path,body=None,headers=None,method='POST'):
            conn=http_client.HTTPConnection('127.0.0.1',http.server_port,timeout=3)
            h={'Host':'lya.synthetic.ts.net','Origin':ORIGIN,'Content-Type':'application/json'};h.update(headers or {})
            conn.request(method,path,body,h);r=conn.getresponse();result=(r.status,r.read(),dict(r.getheaders()));conn.close();return result
        self.assertEqual(request('/',method='GET')[0],200)
        self.assertEqual(request('/../auth.sqlite',method='GET')[0],404)
        self.assertEqual(request('/',headers={'Host':'evil.test'},method='GET')[0],403)
        self.assertEqual(request('/auth/begin','{}',{'Origin':'https://evil.test'})[0],403)
        self.assertEqual(request('/auth/begin','{"mode":"login","mode":"pair"}')[0],400)
        self.assertEqual(request('/chat','{"id":"'+('a'*32)+'","text":"hello"}')[0],403)
        token=self.pair();t=self.app.begin('login')['ticket']
        code,body,headers=request('/auth/complete',json.dumps({'ticket':t,'response':self.response(t)}))
        self.assertEqual(code,200);self.assertEqual(headers['Cache-Control'],'no-store')
        for flag in ('Secure','HttpOnly','SameSite=Strict','Path=/'):
            self.assertIn(flag,headers['Set-Cookie'])
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        cookie={ 'Cookie':COOKIE+'='+token }
        self.assertEqual(request('/chat',json.dumps({'id':'b'*32,'text':'hello','tools':['shell']}),cookie)[0],400)
        self.assertEqual(request('/chat',json.dumps({'id':'b'*32,'text':'hello'}),cookie)[0],200)

    def test_origin_and_auth_rate_limits(self):
        for origin in ('http://lya.synthetic.ts.net',ORIGIN+'/path','https://evil.test','https://user@lya.synthetic.ts.net'):
            with self.assertRaises(ValueError):checked_origin(origin)
        for _ in range(20):
            with self.assertRaises(PermissionError):self.app.begin('login')
        t=self.store.control('invite',BINDING,self.now)['token']
        with self.assertRaises(PermissionError):self.app.begin('pair',t)

    def test_runtime_uses_fixed_public_inference_without_provider_keys(self):
        from cloud import mobile_runtime
        from types import SimpleNamespace
        with patch.object(mobile_runtime,'exchange',return_value=SimpleNamespace(returncode=0,stdout='{"text":"ok"}')) as exchange:
            self.assertEqual(mobile_runtime.infer([{'role':'user','content':'hello'}],threading.Event()),'ok')
        args,kwargs=exchange.call_args
        self.assertEqual(args[0],['sudo','-n','-u','ubuntu','/usr/bin/python3','/home/ubuntu/lya/inference.py'])
        self.assertEqual(json.loads(args[1])['sensitivity'],'public')
        self.assertTrue(kwargs['close_stdin'])


class NativeMobileChecks(SyntheticPasskeys,unittest.TestCase):
    def test_spoken_mobile_punctuation_routes_without_broadening_command_authority(self):
        from brain.workflow import Brain
        owner=self.enroll()
        brain=Brain(owner,approve=lambda *a:True,client=lambda _: 'ordinary reply',db_path=self.db)
        with patch('cloud.mobile_client.control',return_value={'url':ORIGIN+'/#'+'x'*43,'origin':ORIGIN}) as control:
            for text in ('Connect my phone.','Pair my phone!','Connect my phone?'):
                self.assertEqual(brain.respond(text).route,'mobile-pairing')
                self.assertEqual(control.call_args.args[0],'invite')
            control.return_value={'revoked':True}
            self.assertIn('revoked',brain.respond('Disconnect my phone.').text)
            self.assertEqual(control.call_args.args[0],'revoke')
            control.reset_mock()
            for text in ('do not connect my phone.','"connect my phone"','what does connect my phone mean?'):
                self.assertEqual(brain.respond(text).text,'ordinary reply')
            control.assert_not_called()

    def test_control_pins_ssh_binds_current_owner_and_rejects_changed_origin(self):
        from cloud import mobile_client
        from types import SimpleNamespace
        owner=self.enroll()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();(root/'desktop').mkdir();(root/'fake.key').write_text('FAKE_ONLY')
            config=root/'desktop/mobile.local.json'
            config.write_text(json.dumps({'origin':ORIGIN,'enabled':True}))
            (root/'desktop/oracle.local.json').write_text(json.dumps({'host':'192.0.2.1','key_file':'fake.key'}))
            with patch.object(mobile_client,'ROOT',root),patch.object(mobile_client,'CONFIG',config), \
                 patch('cloud.ssh_session.exchange',return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'url':ORIGIN+'/#'+'x'*43}))) as exchange:
                self.assertEqual(mobile_client.control('invite',owner,self.db)['origin'],ORIGIN)
                args,kwargs=exchange.call_args
                self.assertIn('StrictHostKeyChecking=yes',args[0])
                self.assertEqual(set(json.loads(args[1])),{'binding'})
                self.assertNotIn(owner.person_id,args[1]);self.assertNotIn(owner.person,args[1])
                exchange.return_value.stdout=json.dumps({'url':'https://evil.test/#'+'x'*43})
                with self.assertRaises(ValueError):mobile_client.control('invite',owner,self.db)

    def test_only_current_signed_owner_and_exact_approval_can_pair_or_revoke(self):
        from brain.workflow import Brain
        owner=self.enroll()
        brain=Brain(owner,approve=lambda *a:False,client=lambda _:self.fail('No model for pairing'),db_path=self.db)
        with patch('cloud.mobile_client.control',return_value={'url':ORIGIN+'/#'+'x'*43,'origin':ORIGIN}) as control:
            self.assertEqual(brain.respond('connect my phone').route,'blocked');control.assert_not_called()
            brain.approve=lambda *a:True
            answer=brain.respond('connect my phone')
            self.assertEqual(answer.route,'mobile-pairing');self.assertNotIn('x'*43,answer.text)
            self.assertEqual(answer.evidence[0]['url'],ORIGIN+'/#'+'x'*43)
            control.return_value={'revoked':True}
            self.assertIn('revoked',brain.respond('disconnect my phone').text)
            from security.policy import Session
            brain.bind_session(Session(id='guest'))
            self.assertEqual(brain.respond('connect my phone').route,'blocked')


class InstallerChecks(unittest.TestCase):
    def activation(self,existing):
        import io
        from contextlib import redirect_stdout
        from types import SimpleNamespace
        from unittest.mock import Mock
        from tools.setup_mobile_connection import ACTIVATE
        config=Mock()
        config.is_symlink.return_value=False;config.exists.return_value=True
        config.stat.return_value=SimpleNamespace(st_uid=0,st_mode=0o100644)
        config.read_text.return_value=json.dumps({'origin':ORIGIN})
        state={'BackendState':'Running','Self':{'DNSName':'lya.synthetic.ts.net.'}}
        def run(command,**kwargs):
            data=state if command[:2]==['tailscale','status'] else existing
            return SimpleNamespace(returncode=0,stdout=json.dumps(data).encode())
        with patch('pathlib.Path',return_value=config),patch('subprocess.run',side_effect=run) as calls, \
             patch('http.client.HTTPConnection') as http,redirect_stdout(io.StringIO()):
            http.return_value.getresponse.return_value.status=200
            http.return_value.getresponse.return_value.read.return_value=b'LYA'
            try:exec(compile(ACTIVATE,'activation','exec'),{})
            finally:self.calls=calls.call_args_list;self.config=config

    def test_activation_resumes_only_matching_configuration(self):
        self.activation({'TCP':{'443':{'HTTPS':True}},'Web':{'lya.synthetic.ts.net:443':
            {'Handlers':{'/':{'Proxy':'http://127.0.0.1:8766'}}}}})
        self.config.open.assert_not_called()
        self.assertTrue(any(c.args[0][:2]==['systemctl','enable'] for c in self.calls))

    def test_activation_preserves_existing_other_service_and_rejects_funnel(self):
        for existing in ({'TCP':{'443':{'HTTPS':True}},'Web':{'other':{}}},
                         {'AllowFunnel':{'lya.synthetic.ts.net:443':True}}):
            with self.assertRaises(AssertionError):self.activation(existing)
            self.config.open.assert_not_called()
            self.assertFalse(any(c.args[0][:2]==['systemctl','enable'] for c in self.calls))


if __name__=='__main__':unittest.main()
