"""Isolated mock-provider pilot checks; never reads a live credential or clipboard."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pilot
from test_memory_b2_backup import FakeB2,Response

HERE=Path(__file__).resolve().parent
ORIGINAL_TRANSFER=pilot.TRANSFER


class ScopedFake(FakeB2):
    prefix=pilot.custody.PREFIX
    def __init__(self):super().__init__();self.denied=True
    def request(self,method,url,**kw):
        if url.endswith('/b2_list_file_names') or url.endswith('/file/'+self.name+'/backup.enc'):
            self.calls.append((method,url,kw))
            return Response({'message':'FAKE_PRIVATE_DETAILS'},401) if self.denied else Response(b'FAKE_SCOPE_FAILURE')
        return super().request(method,url,**kw)


class PilotChecks(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='.fake-pilot-check-',dir=HERE)
        self.home=Path(self.temp.name).resolve();assert self.home.is_relative_to(HERE.resolve())
        self.addCleanup(self.temp.cleanup)
        prepared=json.loads((ORIGINAL_TRANSFER/'prepared.json').read_text())
        old_local=Path(prepared['local_only_inputs']);local=json.loads(old_local.read_text())
        home=self.home/'.fake-local'/'fixture';home.mkdir(parents=True);pack=home/'upload-only';pack.mkdir()
        for name in pilot.NAMES:shutil.copyfile(Path(prepared['upload_folder'])/name,pack/name)
        local['pack']=str(pack);local_path=home/'local-only.json';local_path.write_text(json.dumps(local))
        prepared.update(upload_folder=str(pack),local_only_inputs=str(local_path))
        (self.home/'prepared.json').write_text(json.dumps(prepared))
        shutil.copyfile(ORIGINAL_TRANSFER/'verify.py',self.home/'verify.py')
        for key,value in (('HERE',self.home),('TRANSFER',self.home)):
            mock=patch.object(pilot,key,value);mock.start();self.addCleanup(mock.stop)
        self.service=ScopedFake()
        import brain.memory_b2_backup as backup
        transport=patch.object(backup.http.client,'HTTPSConnection',side_effect=self.service.connection)
        transport.start();self.addCleanup(transport.stop)
        self.loader=patch.object(pilot.custody,'_load',return_value={'key_id':'FAKE_CHILD_ID','key':'FAKE_CHILD_SECRET'})
        self.load=self.loader.start();self.addCleanup(self.loader.stop)
        self.credential=self.home/'unused-fake-credential.dpapi';self.pack=pack

    def run_pilot(self,**values):
        return pilot.run(self.credential,self.service.bucket,self.service.name,'mock-run',**values)

    def test_mock_upload_scope_denials_download_and_fresh_process_restore(self):
        result=self.run_pilot(approved=True)
        self.assertTrue(result['passed']);self.assertEqual(self.service.puts,3)
        self.assertEqual(result['scope_read_denials_http'],{'outside_prefix':401,'file_listing':401})
        self.assertTrue(result['fresh_process']['recovered']);self.assertTrue(result['fresh_process']['quarantined'])
        self.assertEqual(result['fresh_process']['active_bindings'],0);self.assertEqual(result['fresh_process']['resumed_jobs'],0)
        self.assertLessEqual(result['extra_client_calls'],16)
        text=json.dumps(result)
        for secret in ('FAKE_CHILD_SECRET','FAKE_AUTH_TOKEN','FAKE_UPLOAD_TOKEN','FAKE_PRIVATE_DETAILS'):
            self.assertNotIn(secret,text)
        self.assertFalse(self.credential.exists())

    def test_preview_approval_and_existing_output_guards(self):
        output=io.StringIO()
        with patch.object(pilot.sys,'argv',['pilot']),contextlib.redirect_stdout(output):self.assertEqual(pilot.main(),0)
        self.assertFalse(json.loads(output.getvalue())['credential_read'])
        with self.assertRaises(PermissionError):self.run_pilot()
        report=self.home/'mock-run.json';report.write_text('FAKE_KEEP')
        with self.assertRaises(FileExistsError):self.run_pilot(approved=True)
        self.assertEqual(report.read_text(),'FAKE_KEEP');self.load.assert_not_called();self.assertEqual(self.service.calls,[])

    def test_changed_fake_pack_refuses_before_credential_or_network(self):
        (self.pack/'backup.enc').write_bytes(b'FAKE_CHANGED_CIPHERTEXT')
        with self.assertRaises(ValueError):self.run_pilot(approved=True)
        self.load.assert_not_called();self.assertEqual(self.service.calls,[])

    def test_missing_provider_scope_denial_stops_before_upload(self):
        self.service.denied=False
        with self.assertRaises(ValueError):self.run_pilot(approved=True)
        self.assertEqual(self.service.puts,0)


if __name__=='__main__':
    report=HERE/'mock-validation.json';log=HERE/'mock-validation.txt'
    if report.exists() or log.exists():raise SystemExit('Preserve previous evidence.')
    with log.open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PilotChecks))
    data={'passed':result.wasSuccessful() and not result.skipped and result.testsRun==4,
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'b2_https_mocked':True,'live_credential_loaded':False,'live_upload_performed':False}
    report.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
    if not data['passed']:print(log.read_text());raise SystemExit(1)
