"""Generated fake keys, temporary SQLCipher stores and mocked B2; no live account."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import unquote,urlsplit

from brain import memory_b2_backup as backup
from test_memory_recovery_pack import RecoveryPackChecks,WORKER


class Response:
    def __init__(self,value,status=200):
        self.status=self.status_code=status;self.blob=value if isinstance(value,bytes) else json.dumps(value).encode();self.offset=0
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,size):
        value=self.blob[self.offset:self.offset+size];self.offset+=len(value);return value
    def getheader(self,name):return None


class Connection:
    def __init__(self,service,host,timeout,context):
        assert context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname
        assert 0<timeout<=4
        self.service=service;self.host=host
    def request(self,method,path,body=None,headers=None):
        self.response=self.service.request(method,'https://'+self.host+path,headers=headers,data=body)
    def getresponse(self):return self.response
    def close(self):self.service.closed=True


class FakeB2:
    bucket='123456abcdef';name='lya-fake-backup-test';prefix='lya-memory-lab/test/'
    def __init__(self):
        self.caps=list(backup.CAPABILITIES);self.buckets=[{'id':self.bucket,'name':self.name}]
        self.allowed_prefix=self.prefix;self.private=True;self.objects={};self.puts=0;self.calls=[]
        self.fail_after_put=False;self.fail_status=None;self.corrupt=False;self.closed=False
        self.upload_url='https://pod-000-1005-03.backblaze.com/b2api/v4/b2_upload_file?cvt=fake&bucket='+self.bucket
        self.api_url='https://api003.backblazeb2.com';self.download_url='https://f003.backblazeb2.com'
        self.auth_override=None
        self.expiry=int((time.time()+3600)*1000)
    def connection(self,host,timeout,context):return Connection(self,host,timeout,context)
    def request(self,method,url,**kw):
        self.calls.append((method,url,kw))
        if url.endswith('/b2_authorize_account'):
            return self.auth_override or Response({'accountId':'FAKE_ACCOUNT','authorizationToken':'FAKE_AUTH_TOKEN',
                'applicationKeyExpirationTimestamp':self.expiry,
                'apiInfo':{'storageApi':{'apiUrl':self.api_url,'downloadUrl':self.download_url,
                'allowed':{'capabilities':self.caps,'buckets':self.buckets,'namePrefix':self.allowed_prefix}}}})
        if url.endswith('/b2_list_buckets'):
            return Response({'buckets':[{'bucketId':self.bucket,'bucketName':self.name,
                'bucketType':'allPrivate' if self.private else 'allPublic'}]})
        if url.endswith('/b2_get_upload_url'):
            return Response({'bucketId':self.bucket,'uploadUrl':self.upload_url,'authorizationToken':'FAKE_UPLOAD_TOKEN'})
        if '/b2_upload_file' in url:
            if self.fail_status:return Response({'code':'storage_cap_exceeded','message':'FAKE_SECRET_DO_NOT_PRINT'},self.fail_status)
            name=unquote(kw['headers']['X-Bz-File-Name']);blob=kw['data'];self.objects[name]=blob;self.puts+=1
            if self.fail_after_put:self.fail_after_put=False;raise OSError('FAKE_SECRET_DO_NOT_PRINT')
            return Response({'bucketId':self.bucket,'fileName':name,'contentLength':len(blob),
                'contentSha1':hashlib.sha1(blob).hexdigest(),'serverSideEncryption':{'algorithm':'AES256','mode':'SSE-B2'}})
        if '/file/' in url:
            name=unquote(urlsplit(url).path.split('/file/'+self.name+'/',1)[1])
            if name not in self.objects:return Response({'code':'not_found'},404)
            blob=self.objects[name]
            return Response(blob+b'bad' if self.corrupt else blob)
        raise AssertionError('Unexpected fake endpoint')


class B2BackupChecks(unittest.TestCase):
    def setUp(self):
        self.fixture=RecoveryPackChecks(methodName='runTest');self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp();self.fixture.latest();self.pins,_=self.fixture.pins()
        self.folder=self.fixture.f.home/'pack';self.fixture.stage(self.folder)
        self.service=FakeB2();self.mock=patch.object(backup.http.client,'HTTPSConnection',side_effect=self.service.connection)
        self.mock.start();self.addCleanup(self.mock.stop)
        self.receipt=self.fixture.f.home/'receipt.json'

    def run_backup(self,**kw):
        values=dict(pins=self.pins,observe=lambda:self.pins,key_id='FAKE_KEY_ID',key='FAKE_SERVICE_KEY',
            bucket_id=self.service.bucket,bucket_name=self.service.name,prefix=self.service.prefix,
            synthetic_only=True,approved=True)
        values.update(kw)
        return backup.backup_once(self.folder,self.receipt,**values)

    def test_opaque_ciphertext_upload_and_readback_need_no_unlock_key(self):
        with patch('brain.memory_custody.open_keys',side_effect=AssertionError('Uploader must not unlock')):
            result=self.run_backup()
        self.assertTrue(result['verified']);self.assertEqual(self.service.puts,3)
        self.assertLessEqual(len(self.service.calls),16);self.assertTrue(self.service.closed)
        self.assertEqual(json.loads(self.receipt.read_text()),result)
        text=self.receipt.read_text()
        for secret in ('FAKE_SERVICE_KEY','FAKE_AUTH_TOKEN','FAKE_UPLOAD_TOKEN',self.fixture.unlock.decode()):
            self.assertNotIn(secret,text)
        for _,_,kw in self.service.calls:
            self.assertNotIn(self.fixture.unlock,kw.get('data') or b'')

    def test_repeat_fresh_worker_reads_existing_objects_without_more_uploads(self):
        first=self.run_backup();self.receipt=self.fixture.f.home/'second-receipt.json'
        self.assertEqual(self.run_backup(),first);self.assertEqual(self.service.puts,3)

    def test_only_documented_or_legacy_missing_file_404_is_absent(self):
        client=backup._B2(lambda:False)
        url='https://f003.backblazeb2.com/file/lya-fake-backup-test/fake.enc'
        for code in ('not_found','file_not_present'):
            with self.subTest(code=code),patch.object(self.service,'request',return_value=Response({'code':code},404)):
                self.assertIsNone(client.request('GET',url,missing=True))
        for value,status,missing in (({'code':'not_found'},401,True),({'code':'other'},404,True),
                                     ({'code':'not_found'},404,False),(b'not json',404,True)):
            with self.subTest(value=value,status=status,missing=missing),patch.object(
                    self.service,'request',return_value=Response(value,status)),self.assertRaises(ValueError):
                client.request('GET',url,missing=missing)

    def test_committed_upload_reply_loss_reconciles_on_next_worker(self):
        self.service.fail_after_put=True
        with self.assertRaises(OSError) as error:self.run_backup()
        self.assertNotIn('FAKE_SECRET',str(error.exception));self.assertFalse(self.receipt.exists())
        self.assertEqual(self.service.puts,1);self.assertTrue(self.run_backup()['verified'])
        self.assertEqual(self.service.puts,3)

    def test_corrupted_remote_artifact_never_gets_overwritten_or_acknowledged(self):
        self.run_backup();self.receipt=self.fixture.f.home/'refused.json';self.service.corrupt=True
        with self.assertRaises(ValueError):self.run_backup()
        self.assertEqual(self.service.puts,3);self.assertFalse(self.receipt.exists())

    def test_failed_final_readback_leaves_no_receipt(self):
        original=self.service.request
        def corrupt_after_put(*args,**kw):
            if self.service.puts==3:self.service.corrupt=True
            return original(*args,**kw)
        self.service.request=corrupt_after_put
        with self.assertRaises(ValueError):self.run_backup()
        self.assertFalse(self.receipt.exists())

    def test_master_broad_delete_and_incomplete_capabilities_refuse_before_file_io(self):
        for caps in (list(backup.CAPABILITIES)+['deleteFiles'],['writeKeys'],['writeFiles']):
            with self.subTest(caps=caps):
                self.service.calls=[];self.service.caps=caps
                with self.assertRaises(ValueError):self.run_backup()
                self.assertEqual(len(self.service.calls),1);self.assertEqual(self.service.puts,0)

    def test_wrong_bucket_unrestricted_or_wrong_prefix_are_refused(self):
        for field,value in (('buckets',None),('buckets',[{'id':'wrong','name':'wrong'}]),
                ('allowed_prefix',None),('allowed_prefix','lya-memory-lab/other/')):
            original=getattr(self.service,field);setattr(self.service,field,value)
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.run_backup()
            setattr(self.service,field,original)
        self.assertEqual(self.service.puts,0)

    def test_public_bucket_is_refused(self):
        self.service.private=False
        with self.assertRaises(ValueError):self.run_backup()
        self.assertEqual(self.service.puts,0)

    def test_permanent_expired_or_overlong_service_keys_are_refused(self):
        for expiry in (None,False,int((time.time()-1)*1000),int((time.time()+90000)*1000)):
            self.service.expiry=expiry
            with self.subTest(expiry=expiry),self.assertRaises(ValueError):self.run_backup()
        self.assertEqual(self.service.puts,0)

    def test_untrusted_discovered_destinations_do_not_receive_service_tokens(self):
        for field,value in (('api_url','http://api003.backblazeb2.com'),
                ('download_url','https://f003.backblazeb2.com.evil.example'),
                ('upload_url','https://example.com/b2api/v4/b2_upload_file')):
            original=getattr(self.service,field);setattr(self.service,field,value);self.service.calls=[]
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_backup()
            self.assertTrue(all('example.com' not in call[1] for call in self.service.calls))
            setattr(self.service,field,original)
        self.assertEqual(self.service.puts,0)

    def test_redirect_auth_failure_and_malformed_authorization_fail_closed(self):
        for response in (Response({},302),Response({'message':'FAKE_SECRET_DO_NOT_PRINT'},401),
                         Response(b'{"accountId":"x","accountId":"y"}'),Response({'apiInfo':None})):
            response.offset=0
            self.service.auth_override=response
            with self.subTest(status=response.status_code),self.assertRaises(ValueError) as error:self.run_backup()
            self.assertNotIn('FAKE_SECRET',str(error.exception));self.assertFalse(self.receipt.exists())

    def test_storage_cap_rejection_and_cancellation_leave_no_receipt(self):
        self.service.fail_status=403
        with self.assertRaises(ValueError) as error:self.run_backup()
        self.assertNotIn('FAKE_SECRET',str(error.exception));self.assertFalse(self.receipt.exists())
        self.service.fail_status=None
        with self.assertRaises(InterruptedError):self.run_backup(cancelled=lambda:self.service.puts>0)
        self.assertFalse(self.receipt.exists())

    def test_trust_change_before_or_during_transfer_prevents_acknowledgement(self):
        advanced=replace(self.pins,state=replace(self.pins.state,writer_epoch=self.pins.state.writer_epoch+1))
        with self.assertRaises(backup.Conflict):self.run_backup(observe=lambda:advanced)
        self.assertEqual(self.service.calls,[])
        observations=[]
        def observe():
            observations.append(True);return self.pins if len(observations)==1 else advanced
        with self.assertRaises(backup.Conflict):self.run_backup(observe=observe)
        self.assertEqual(self.service.puts,3);self.assertFalse(self.receipt.exists())

    def test_local_bad_layout_hash_and_size_refuse_before_authorization(self):
        for kind in ('extra','changed','large'):
            path=self.folder/('extra.txt' if kind=='extra' else 'backup.enc');old=path.read_bytes() if path.exists() else None
            if kind=='large':
                with path.open('r+b') as out:out.truncate(backup.MAX_PACK_BYTES+1)
            else:path.write_bytes(b'FAKE_BAD_INPUT')
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.run_backup()
            if old is None:path.unlink()
            else:path.write_bytes(old)
        self.assertEqual(self.service.calls,[])

    def test_exact_opt_in_scope_and_new_receipt_required(self):
        for values in ({'approved':1},{'approved':False},{'synthetic_only':1},{'prefix':'../'},
                       {'bucket_name':'x/escape'},{'pins':None}):
            with self.subTest(values=values),self.assertRaises((PermissionError,ValueError)):self.run_backup(**values)
        self.receipt.write_text('FAKE_DO_NOT_REPLACE')
        with self.assertRaises(FileExistsError):self.run_backup()
        self.assertEqual(self.receipt.read_text(),'FAKE_DO_NOT_REPLACE');self.assertEqual(self.service.calls,[])

    def test_response_request_and_cooperative_time_budgets(self):
        client=backup._B2(lambda:False)
        client.calls=16
        with self.assertRaises(ValueError):client.request('GET','https://api.backblazeb2.com')
        client.calls=0;client.deadline=0
        with self.assertRaises(TimeoutError):client.request('GET','https://api.backblazeb2.com')
        self.service.auth_override=Response(b'x'*65537)
        with self.assertRaises(ValueError):self.run_backup()
        self.assertFalse(self.receipt.exists())

    def test_fresh_process_recovers_from_mock_remote_with_custody_kept_separate(self):
        self.run_backup()
        with tempfile.TemporaryDirectory(prefix='fake-worker-readback-',dir=self.fixture.f.home.parent) as folder:
            home=Path(folder);pack=home/'readback';pack.mkdir()
            for name in backup.NAMES:
                matching=[blob for key,blob in self.service.objects.items() if key.endswith('/'+name)]
                self.assertEqual(len(matching),1);(pack/name).write_bytes(matching[0])
            f=self.fixture
            packet=dict(imports=[str(Path(__file__).resolve().parent)],lost_source=str(f.f.home),
                pack=str(pack),destination=str(home/'restored.sqlite'),pins=backup.asdict(self.pins),
                unlock=f.unlock.decode(),storage_key=f.f.key.hex(),now=f.f.now,
                kept=f.kept['id'],forgotten=f.forgotten['id'],expired=f.expired['id'])
            if sys.platform=='win32':packet['imports'].append(str(Path(__file__).resolve().parent/'review/2026-10-12-memory-hardening/.drivers'))
            f.doCleanups()
            result=subprocess.run([sys.executable,'-I','-B','-c',WORKER],input=json.dumps(packet),
                capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(result.returncode,0,'Fake fresh-process restore failed; raw output withheld.')
            self.assertTrue(json.loads(result.stdout)['quarantined'])


if __name__=='__main__':unittest.main()
