"""Fake issuer/child credentials and temporary DPAPI files only; no live B2."""
import base64
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from brain import memory_b2_credential as custody,memory_b2_backup as backup
from test_memory_b2_backup import FakeB2,Response,B2BackupChecks


class IssuerB2(FakeB2):
    prefix=custody.PREFIX
    def __init__(self):
        super().__init__();self.creates=0;self.issuer_caps=sorted(custody.CAPABILITIES|{'writeKeys'})
        self.created_override={};self.lose_create_reply=False;self.child_expiry=None
        self.issuer_status=None
    def request(self,method,url,**kw):
        if url.endswith('/b2_authorize_account'):
            identity=base64.b64decode(kw['headers']['Authorization'][6:]).decode().split(':',1)[0]
            if identity=='FAKEISSUER':
                self.calls.append((method,url,kw))
                if self.issuer_status:return Response({'message':'FAKE_ISSUER_SECRET_DO_NOT_PRINT'},self.issuer_status)
                return Response({'accountId':'FAKEACCOUNT','authorizationToken':'FAKE_ISSUER_AUTH',
                    'apiInfo':{'storageApi':{'apiUrl':self.api_url,'allowed':{'capabilities':self.issuer_caps}}}})
            if self.child_expiry is not None:self.expiry=self.child_expiry
        if url.endswith('/b2_create_key'):
            self.calls.append((method,url,kw));self.creates+=1
            if self.lose_create_reply:raise OSError('FAKE_ISSUER_SECRET_DO_NOT_PRINT')
            value=dict(accountId='FAKEACCOUNT',keyName='lya-memory-lab-worker-pilot',
                bucketIds=[self.bucket],namePrefix=self.prefix,capabilities=sorted(custody.CAPABILITIES),
                applicationKeyId='FAKECHILD',applicationKey='FAKE_CHILD_SECRET_DO_NOT_PRINT',expirationTimestamp=self.expiry)
            value.update(self.created_override);return Response(value)
        return super().request(method,url,**kw)


@unittest.skipUnless(sys.platform=='win32','Real DPAPI requires Windows.')
class CredentialChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='lya-fake-b2-credential-')
        self.addCleanup(self.temp.cleanup);self.home=Path(self.temp.name);self.path=self.home/'pilot.dpapi'
        self.service=IssuerB2()
        mocked=patch.object(backup.http.client,'HTTPSConnection',side_effect=self.service.connection)
        mocked.start();self.addCleanup(mocked.stop)

    def provision(self,**changes):
        args=dict(issuer_id='FAKEISSUER',issuer_key='FAKE_ISSUER_SECRET_DO_NOT_PRINT',
            bucket_id=self.service.bucket,bucket_name=self.service.name,synthetic_only=True,approved=True)
        args.update(changes)
        return custody.provision(self.path,**args)

    def load(self):return custody._load(self.path,self.service.bucket,self.service.name)

    def test_real_dpapi_stores_only_child_and_new_process_can_load(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):result=self.provision()
        self.assertEqual(output.getvalue(),'');self.assertEqual(set(result),{'stored','expires_ms','synthetic_only'})
        blob=self.path.read_bytes();self.assertTrue(blob.startswith(custody.MAGIC))
        for secret in (b'FAKE_CHILD_SECRET',b'FAKE_ISSUER_SECRET',b'FAKE_ISSUER_AUTH'):
            self.assertNotIn(secret,blob);self.assertNotIn(secret.decode(),json.dumps(result))
        raw=custody._unprotect(blob[len(custody.MAGIC):])
        self.assertNotIn(b'FAKE_ISSUER',raw);self.assertEqual(self.load()['key_id'],'FAKECHILD')
        code="import sys;sys.path.insert(0,sys.argv[1]);from brain.memory_b2_credential import _load;_load(sys.argv[2],sys.argv[3],sys.argv[4]);print('loaded')"
        run=subprocess.run([sys.executable,'-I','-B','-c',code,str(Path(__file__).resolve().parent),
            str(self.path),self.service.bucket,self.service.name],capture_output=True,text=True,timeout=20,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(run.returncode,0,'Fresh-process DPAPI load failed; raw output withheld.')
        self.assertEqual(run.stdout.strip(),'loaded')

    def test_exact_create_request_child_authorization_and_no_transfer(self):
        self.provision();calls=self.service.calls
        creates=[call for call in calls if call[1].endswith('/b2_create_key')]
        self.assertEqual(len(creates),1)
        self.assertEqual(json.loads(creates[0][2]['data']),dict(accountId='FAKEACCOUNT',
            keyName='lya-memory-lab-worker-pilot',capabilities=sorted(custody.CAPABILITIES),
            bucketIds=[self.service.bucket],namePrefix=custody.PREFIX,validDurationInSeconds=3600))
        self.assertEqual(self.service.puts,0);self.assertEqual(len(calls),5)
        self.assertFalse(any('/file/' in c[1] or '/b2_upload_file' in c[1] for c in calls))
        self.assertEqual(len([c for c in calls if c[1].endswith('/b2_authorize_account')]),2)

    def test_opt_in_scope_existing_and_missing_parent_refuse_before_network(self):
        for args in ({'approved':1},{'synthetic_only':False},{'bucket_name':'production'},
                     {'bucket_id':'../escape'},{'issuer_id':'id:escape'}):
            with self.subTest(args=args),self.assertRaises((PermissionError,ValueError)):self.provision(**args)
        self.path.write_bytes(b'FAKE_KEEP_EXISTING')
        with self.assertRaises(FileExistsError):self.provision()
        self.assertEqual(self.path.read_bytes(),b'FAKE_KEEP_EXISTING')
        self.path=self.home/'missing'/'pilot.dpapi'
        with self.assertRaises(FileNotFoundError):self.provision()
        self.assertEqual(self.service.calls,[])

    def test_protection_failure_cancellation_and_unsupported_host_do_not_create(self):
        with patch.object(custody,'_protect',side_effect=OSError('FAKE_FAILURE')):
            with self.assertRaises(OSError):self.provision()
        with self.assertRaises(InterruptedError):self.provision(cancelled=lambda:True)
        with patch.object(custody.sys,'platform','linux'):
            with self.assertRaises(OSError):self.provision()
        self.assertEqual(self.service.calls,[]);self.assertFalse(self.path.exists())

    def test_missing_issuer_permission_public_or_wrong_bucket_prevents_creation(self):
        self.service.issuer_caps=['writeKeys']
        with self.assertRaises(ValueError):self.provision()
        self.service.issuer_caps=sorted(custody.CAPABILITIES|{'writeKeys'})
        self.service.private=False
        with self.assertRaises(ValueError):self.provision()
        self.service.private=True
        with self.assertRaises(ValueError):self.provision(bucket_name='lya-fake-other')
        self.assertEqual(self.service.creates,0);self.assertFalse(self.path.exists())

    def test_untrusted_issuer_api_never_receives_token(self):
        self.service.api_url='https://example.com'
        with self.assertRaises(ValueError):self.provision()
        self.assertEqual(len(self.service.calls),1);self.assertEqual(self.service.creates,0)

    def test_created_response_must_match_exact_scope_and_expiry(self):
        invalid=({'accountId':'OTHERACCOUNT'},{'keyName':'other'},{'bucketIds':None},
            {'namePrefix':None},{'capabilities':sorted(custody.CAPABILITIES)+['deleteFiles']},
            {'capabilities':None},{'expirationTimestamp':None},{'expirationTimestamp':False},
            {'expirationTimestamp':10**300},{'applicationKeyId':'bad:id'},
            {'applicationKey':'x'*513})
        for values in invalid:
            self.service.created_override=values
            with self.subTest(field=next(iter(values))),self.assertRaisesRegex(RuntimeError,'key may exist'):
                self.provision()
            self.assertFalse(self.path.exists())

    def test_child_authorization_checks_scope_private_bucket_and_matching_expiry(self):
        for attribute,value in (('caps',sorted(custody.CAPABILITIES)+['deleteFiles']),
                ('allowed_prefix','lya-memory-lab/other/'),('buckets',None),
                ('child_expiry',self.service.expiry+1000)):
            original=getattr(self.service,attribute);setattr(self.service,attribute,value)
            with self.subTest(attribute=attribute),self.assertRaises(RuntimeError):self.provision()
            setattr(self.service,attribute,original)
            self.assertFalse(self.path.exists())

    def test_lost_creation_reply_is_not_retried_or_logged(self):
        self.service.lose_create_reply=True
        with self.assertRaises(RuntimeError) as error:self.provision()
        self.assertEqual(str(error.exception),custody.UNCERTAIN)
        self.assertEqual(self.service.creates,1);self.assertFalse(self.path.exists())

    def test_failed_publication_and_post_create_cancellation_report_uncertainty(self):
        with patch.object(custody,'_publish',side_effect=OSError('FAKE_CHILD_SECRET_DO_NOT_PRINT')):
            with self.assertRaisesRegex(RuntimeError,'Do not retry'):self.provision()
        self.assertEqual(self.service.creates,1);self.assertFalse(self.path.exists())
        self.service.creates=0
        with self.assertRaisesRegex(RuntimeError,'Do not retry'):
            self.provision(cancelled=lambda:self.service.creates>0)
        self.assertEqual(self.service.creates,1);self.assertFalse(self.path.exists())

    def test_racing_destination_is_not_overwritten(self):
        original=custody._publish
        def raced(path,writer,cancelled):
            path.write_bytes(b'FAKE_RACING_FILE');return original(path,writer,cancelled)
        with patch.object(custody,'_publish',side_effect=raced):
            with self.assertRaises(RuntimeError):self.provision()
        self.assertEqual(self.path.read_bytes(),b'FAKE_RACING_FILE')

    def test_tampered_oversized_and_plaintext_files_fail_closed(self):
        self.provision();blob=self.path.read_bytes()
        for bad in (b'{"key":"FAKE_PLAINTEXT"}',custody.MAGIC+b'bad',b'x'*16385,
                    blob[:-1]+bytes([blob[-1]^1])):
            self.path.write_bytes(bad)
            with self.subTest(size=len(bad)),self.assertRaises(ValueError):self.load()

    def test_expired_wrong_schema_or_scope_protected_data_is_refused(self):
        self.provision();data=self.load()
        for changes in ({'expires_ms':0},{'expires_ms':10**300},{'version':True},
                        {'prefix':'lya-memory-lab/other/'},{'bucket_id':'otherbucket'},
                        {'issuer_key':'FAKE_FORBIDDEN_EXTRA_FIELD'}):
            altered=dict(data,**changes)
            self.path.write_bytes(custody.MAGIC+custody._protect(custody._json(altered).encode()))
            with self.subTest(field=next(iter(changes))),self.assertRaises(ValueError):self.load()

    def test_credential_handoff_runs_existing_worker_without_issuer_or_unlock_key(self):
        self.provision()
        fixture=B2BackupChecks(methodName='runTest');self.addCleanup(fixture.doCleanups);fixture.setUp()
        with patch.object(backup.http.client,'HTTPSConnection',
                          side_effect=self.service.connection),patch('brain.memory_custody.open_keys',
                          side_effect=AssertionError('No unlock access')):
            before=len(self.service.calls)
            result=custody.backup_with_credential(fixture.folder,fixture.receipt,credential_path=self.path,
                bucket_id=self.service.bucket,bucket_name=self.service.name,pins=fixture.pins,
                observe=lambda:fixture.pins,synthetic_only=True,approved=True)
        self.assertTrue(result['verified']);self.assertEqual(self.service.puts,3)
        for _,_,kw in self.service.calls[before:]:
            self.assertNotIn('FAKE_ISSUER',str(kw));self.assertNotIn(fixture.fixture.unlock.decode(),str(kw))

    def test_handoff_requires_approval_before_decrypt_or_network(self):
        with patch.object(custody,'_load',side_effect=AssertionError('Must not load')):
            with self.assertRaises(PermissionError):
                custody.backup_with_credential(None,None,credential_path=self.path,bucket_id=self.service.bucket,
                    bucket_name=self.service.name,pins=None,observe=lambda:None,synthetic_only=True,approved=False)
        self.assertEqual(self.service.calls,[])

    def test_cli_refuses_redirected_input_and_cancellation_before_getpass(self):
        with patch.object(sys,'argv',['provision',str(self.path)]),patch.object(sys.stdin,'isatty',return_value=False),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):custody.main()
        for secret_side_effect in (None,custody.getpass.GetPassWarning('FAKE_UNSAFE_INPUT')):
            answers=[self.service.bucket,self.service.name,'' if secret_side_effect is None else 'CREATE ONE-HOUR LAB KEY']
            with patch.object(sys,'argv',['provision',str(self.path)]),patch.object(sys.stdin,'isatty',return_value=True),patch.object(sys.stderr,'isatty',return_value=True),patch('builtins.input',side_effect=answers),patch.object(custody.getpass,'getpass',side_effect=secret_side_effect) as secret,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(custody.main(),1)
                if secret_side_effect is None:secret.assert_not_called()
        self.assertEqual(self.service.calls,[])

    def test_read_only_checks_stop_before_creation_or_local_write(self):
        stages=[]
        self.assertEqual(self.provision(check_only=True,progress=stages.append),
                         {'preflight_passed':True,'key_created':False})
        self.assertEqual(stages,['local protected storage','issuer key ID format','issuer application key format',
            'B2 issuer authentication','issuer permissions','private lab bucket'])
        self.assertEqual(self.service.creates,0);self.assertEqual(len(self.service.calls),2)
        self.assertFalse(self.path.exists());self.assertEqual(list(self.home.iterdir()),[])
        with self.assertRaises(ValueError):self.provision(check_only=1)

    def test_cli_safe_diagnostics_distinguish_failure_stage_without_secret_output(self):
        cases=[('format','issuer key ID format'),('auth','B2 issuer authentication (HTTP 401)'),
               ('permissions','issuer permissions'),('bucket','private lab bucket'),('success','Read-only checks passed.')]
        for scenario,expected in cases:
            self.service.issuer_status=401 if scenario=='auth' else None
            self.service.issuer_caps=['writeKeys'] if scenario=='permissions' else sorted(custody.CAPABILITIES|{'writeKeys'})
            self.service.private=scenario!='bucket'
            secrets=['bad:id' if scenario=='format' else 'FAKEISSUER','FAKE_ISSUER_SECRET_DO_NOT_PRINT']
            output=io.StringIO()
            with self.subTest(scenario=scenario),patch.object(sys,'argv',['provision','--check-only',str(self.path)]),patch.object(sys.stdin,'isatty',return_value=True),patch.object(sys.stderr,'isatty',return_value=True),patch('builtins.input',side_effect=[self.service.bucket,self.service.name]),patch.object(custody.getpass,'getpass',side_effect=secrets),contextlib.redirect_stdout(output):
                self.assertEqual(custody.main(),0 if scenario=='success' else 1)
            self.assertIn(expected,output.getvalue());self.assertNotIn('FAKE_ISSUER',output.getvalue())
            self.assertNotIn('FAKE_CHILD',output.getvalue());self.assertEqual(self.service.creates,0)
        self.assertFalse(self.path.exists())
        self.path=self.home/'missing'/'pilot.dpapi'
        with patch.object(sys,'argv',['provision','--check-only',str(self.path)]),patch.object(sys.stdin,'isatty',return_value=True),patch.object(sys.stderr,'isatty',return_value=True),patch('builtins.input',side_effect=AssertionError('Check folder before owner input')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(custody.main(),1)
        self.assertIn('local credential folder is missing',output.getvalue())

    def test_hidden_field_errors_identify_input_without_values_or_network(self):
        cases=[('', 'FAKE_UNUSED_SECRET',1,'issuer key ID format'),
               ('\x16','FAKE_UNUSED_SECRET',1,'issuer key ID format'),
               ('FAKEISSUER','',2,'issuer application key format'),
               ('FAKEISSUER','\x16',2,'issuer application key format'),
               ('FAKEISSUER','FAKE_KEY_WITH_SPACE ',2,'issuer application key format')]
        for key_id,key,count,stage in cases:
            output=io.StringIO()
            with self.subTest(stage=stage),patch.object(sys,'argv',['provision','--check-only',str(self.path)]),patch.object(sys.stdin,'isatty',return_value=True),patch.object(sys.stderr,'isatty',return_value=True),patch('builtins.input',side_effect=[self.service.bucket,self.service.name]),patch.object(custody.getpass,'getpass',side_effect=[key_id,key]) as reader,contextlib.redirect_stdout(output):
                self.assertEqual(custody.main(),1)
            self.assertIn('Setup refused at '+stage,output.getvalue());self.assertEqual(reader.call_count,count)
            for private in ('FAKEISSUER','FAKE_UNUSED_SECRET','FAKE_KEY_WITH_SPACE','\x16'):
                self.assertNotIn(private,output.getvalue())
        self.assertEqual(self.service.calls,[]);self.assertEqual(self.service.creates,0)
        self.assertFalse(self.path.exists())
        # Model the shipped Windows reader receiving Ctrl+V as a raw key, not clipboard text.
        sink=io.StringIO()
        with patch.object(custody.getpass.sys,'stdin',custody.getpass.sys.__stdin__),patch.object(custody.getpass.msvcrt,'getwch',side_effect=['\x16','\r']),patch.object(custody.getpass.msvcrt,'putwch',side_effect=lambda c:sink.write(c)):
            value=custody.getpass.win_getpass('FAKE prompt: ')
        self.assertEqual(value,'\x16');self.assertNotIn(value,sink.getvalue())


if __name__=='__main__':unittest.main()
