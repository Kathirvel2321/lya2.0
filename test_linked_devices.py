"""Temporary checkout, test passkeys and loopback transport only."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from cryptography.fernet import Fernet

from cloud.device_links import DeviceLinks
from cloud.mobile import Connection, COOKIE, PrivateHTTP
import test_mobile as fixture


class LinkedDeviceChecks(unittest.TestCase):
    def setUp(self):
        self.phone = fixture.MobileChecks()
        self.phone.setUp()
        self.addCleanup(self.phone.doCleanups)
        self.app = self.phone.app
        self.store = self.phone.store
        self.cipher = Fernet(Fernet.generate_key())
        self.app.links = DeviceLinks(self.store,self.cipher,self.app.clock)
        self.phone_token = self.phone.pair()
        self.http = PrivateHTTP(('127.0.0.1',0),self.app)
        thread = threading.Thread(target=self.http.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        thread.start()
        self.addCleanup(self.http.server_close)
        self.addCleanup(self.http.shutdown)

    def request(self,path,data,*,device=None,phone=False,origin=fixture.ORIGIN):
        client=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=3)
        headers={'Host':self.app.rp,'Origin':origin,'Content-Type':'application/json'}
        if device:headers['Authorization']='Bearer '+device
        if phone:headers['Cookie']=COOKIE+'='+self.phone_token
        try:
            client.request('POST',path,json.dumps(data),headers)
            response=client.getresponse()
            return response.status,json.loads(response.read())
        finally:client.close()

    def approve(self,link):
        status,result=self.request('/auth/begin',{'mode':'link','token':link})
        self.assertEqual(status,200)
        ticket=result['ticket']
        return self.request('/auth/complete',{'ticket':ticket,'response':self.phone.response(ticket)})

    def test_one_approval_sync_reopen_and_revoke(self):
        status,attempt=self.request('/device/start',{'name':'Synthetic work laptop'})
        self.assertEqual(status,200)
        device=attempt['credential']
        self.assertEqual(self.request('/device/history',{},device=device)[0],403)
        status,preview=self.request('/device/preview',{'link':attempt['link']})
        self.assertEqual((status,preview),(200,{'name':'Synthetic work laptop','code':attempt['code']}))
        self.assertEqual(self.approve(attempt['link']),(200,{'linked':True}))
        self.assertEqual(self.request('/device/preview',{'link':attempt['link']})[0],403)
        self.assertEqual(self.request('/device/history',{} ,device=attempt['link'])[0],403)
        self.assertEqual(self.request('/chat',{'id':'a'*32,'text':'Home synthetic turn'},phone=True)[0],200)
        status,initial=self.request('/device/history',{},device=device)
        self.assertEqual(status,200)
        self.assertEqual(initial['history'][0]['content'],'Home synthetic turn')
        data={'id':'b'*32,'text':'Second laptop synthetic turn'}
        self.assertEqual(self.request('/device/chat',data,device=device)[0],200)
        self.assertEqual(self.phone.calls[-1][-3]['content'],'Home synthetic turn')
        self.assertEqual(self.request('/device/chat',data,device=device)[0],400)
        self.assertEqual(self.request('/device/chat',{'id':'c'*32,'text':'shared memory demo: recall x'},device=device)[0],400)
        status,fresh=self.request('/device/history',{},phone=True)
        self.assertEqual((status,fresh['history'][-2]['content']),(200,data['text']))
        self.assertNotIn(b'Home synthetic turn',self.store.path.read_bytes())
        self.assertNotIn(device.encode(),self.store.path.read_bytes())
        replacement=Connection(fixture.ORIGIN,self.store,self.app.infer,clock=self.app.clock,
                               device_links=DeviceLinks(self.store,self.cipher,self.app.clock))
        self.assertEqual(replacement.device_request('/device/history',{},device),fresh)
        self.assertEqual(self.request('/device/manage',{},phone=True)[0],403)
        ticket=self.app.begin('owner',session_token=self.phone_token)['ticket']
        self.app.complete(ticket,self.phone.response(ticket))
        self.assertEqual(self.request('/device/manage',{'remove':attempt['link']},phone=True),(200,{'devices':[]}))
        self.assertEqual(self.request('/device/history',{},device=device)[0],403)

    def test_expired_and_foreign_origin_links_fail(self):
        self.assertEqual(self.request('/device/start',{'name':'Synthetic'},origin='https://other.test')[0],403)
        _,attempt=self.request('/device/start',{'name':'Synthetic'})
        self.phone.now+=181
        self.assertEqual(self.request('/auth/begin',{'mode':'link','token':attempt['link']})[0],403)
        self.assertEqual(self.request('/device/history',{},device=attempt['credential'])[0],403)


class CredentialChecks(unittest.TestCase):
    def test_windows_credential_stays_in_checkout(self):
        import sys
        if sys.platform!='win32':self.skipTest('Windows DPAPI')
        from desktop.linked import CredentialFile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve()
            file=CredentialFile(root)
            self.assertIsNone(file.read())
            device='a'*43
            file.save(fixture.ORIGIN,device)
            self.assertEqual(file.read(),{'origin':fixture.ORIGIN,'credential':device})
            self.assertNotIn(device.encode(),file.path.read_bytes())
            self.assertEqual(list(root.rglob('*')), [file.folder,file.path])
