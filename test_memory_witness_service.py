"""Disposable fake-key witness protocol; HTTP connects only to loopback test servers."""
from contextlib import contextmanager
from dataclasses import asdict,replace
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from brain.memory_authority import SyntheticAuthority
from brain.memory_custody import SyntheticWitness,WitnessState
from brain.memory_prototype import Conflict,_json
from brain.memory_recovery import CheckpointAnchor,SyntheticRecovery
from brain import memory_witness_service as rpc


class WitnessServiceChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.home = Path(temp.name)
        self.now = 2000000000;self.key = os.urandom(32)
        self.service,self.client_id,self.lineage,self.digest = 'a'*32,'b'*32,'c'*32,'d'*64
        self.initial = WitnessState(CheckpointAnchor(self.lineage,1,'e'*32,'f'*64),1)
        self.target = replace(self.initial,anchor=replace(self.initial.anchor,sequence=2,checkpoint_id='1'*32,sha256='2'*64))
        self.w = SyntheticWitness.create(self.home/'witness.sqlite',synthetic_only=True,approved=True)
        self.w.register(self.initial,self.digest,approved=True)
        self.endpoint = rpc.SyntheticWitnessEndpoint.enable(self.w,**self.options(),approved=True)
        self.server,self.client = self.serve(self.endpoint)

    def options(self):
        return dict(service=self.service,client=self.client_id,lineage=self.lineage,key=self.key,
                    synthetic_only=True,clock=lambda:self.now)

    def serve(self,endpoint):
        server = rpc.loopback_server(endpoint,synthetic_only=True)
        thread = threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        def stop():server.shutdown();server.server_close();thread.join(3)
        self.addCleanup(stop)
        return server,rpc.SyntheticWitnessClient(server.server_port,**self.options())

    def raw(self,operation,**changes):
        packet = self.client._packet(operation,os.urandom(16).hex());packet.update(changes)
        packet.pop('mac',None)
        return _json(rpc._sign(packet,self.key,rpc.REQUEST_DOMAIN)).encode()

    def test_signed_head_prepare_finish_and_no_raw_key_transmission_or_storage(self):
        self.assertEqual(self.client.head()['state'],self.initial)
        reserved = self.client.prepare(self.initial,self.digest,request_id='1'*32)
        self.assertEqual(reserved['reservation_id'],'1'*32);self.assertEqual(reserved['generation'],1)
        reply = self.client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)
        self.assertEqual(reply['state'],self.target);self.assertIsNone(reply['reservation_id'])
        self.assertEqual(self.w.head(self.lineage),(self.target,self.digest))
        request = self.raw({'op':'head'});status,body = self.endpoint.exchange(request)
        for data in (request,body,self.w.path.read_bytes()):
            self.assertNotIn(self.key,data);self.assertNotIn(self.key.hex().encode(),data)
        self.assertEqual(status,200)

    def test_wrong_key_audience_client_and_signature_domain_never_read_state(self):
        valid = self.client._packet({'op':'head'},'1'*32)
        candidates = [dict(valid,mac='0'*64)]
        for name,value in (('service','f'*32),('client','f'*32)):
            packet=dict(valid);packet.pop('mac');packet[name]=value
            candidates.append(rpc._sign(packet,self.key,rpc.REQUEST_DOMAIN))
        unsigned=dict(valid);unsigned.pop('mac');candidates.append(rpc._sign(unsigned,self.key,rpc.REPLY_DOMAIN))
        with patch.object(self.endpoint,'_head',side_effect=AssertionError('Unauthorized state access')):
            for packet in candidates:self.assertEqual(self.endpoint.exchange(_json(packet).encode())[0],401)
        client = rpc.SyntheticWitnessClient(self.server.server_port,**dict(self.options(),key=os.urandom(32)))
        with self.assertRaises((PermissionError,ValueError)):client.head()

    def test_nonce_replay_is_rejected_but_fresh_nonce_receipt_retry_is_allowed(self):
        raw = self.raw({'op':'head'},request_id='1'*32)
        self.assertEqual(self.endpoint.exchange(raw)[0],200)
        self.assertEqual(self.endpoint.exchange(raw)[0],409)
        fresh = self.raw({'op':'head'},request_id='1'*32)
        self.assertEqual(self.endpoint.exchange(fresh)[0],200)
        self.endpoint = rpc.SyntheticWitnessEndpoint(self.w,**self.options())
        self.assertEqual(self.endpoint.exchange(raw)[0],409)

    def test_old_future_and_boolean_timestamps_fail_without_mutation(self):
        for issued in (self.now-31,self.now+31,True):
            status,_ = self.endpoint.exchange(self.raw({'op':'head'},issued_at=issued));self.assertEqual(status,401)
        self.assertEqual(self.client.head()['state'],self.initial)

    def test_request_expiry_during_operation_rolls_back_reservation(self):
        original = self.endpoint._operation
        def expire(*args):
            result=original(*args);self.now+=31;return result
        with patch.object(self.endpoint,'_operation',side_effect=expire):
            with self.assertRaises(PermissionError):self.client.prepare(self.initial,self.digest,request_id='1'*32)
        self.assertIsNone(self.client.head()['reservation_id'])

    def test_strict_bounded_fields_duplicate_json_and_cross_lineage_are_rejected(self):
        for raw in (b'{}',b'{"version":1,"version":1}',b'[]',b'x'*8193,b'\xff',b'NaN'):
            self.assertEqual(self.endpoint.exchange(raw)[0],401)
        for op in ({'op':'head','value':'SYNTHETIC_PRIVATE'}, {'op':'delete'}, {'op':'head','lineage':'f'*32}):
            status,body = self.endpoint.exchange(self.raw(op));self.assertEqual(status,400)
            self.assertNotIn(b'SYNTHETIC_PRIVATE',body)
        other = replace(self.initial,anchor=replace(self.initial.anchor,lineage='f'*32))
        with self.assertRaises(ValueError):self.client.prepare(other,self.digest,request_id='1'*32)
        for invalid in (False,'',1):
            with self.assertRaises(ValueError):self.client.prepare(self.initial,self.digest,request_id=invalid)
        self.assertEqual(self.client.head()['state'],self.initial)

    def test_prepare_retry_pins_meaning_and_competing_prepare_cannot_steal_reservation(self):
        reserved = self.client.prepare(self.initial,self.digest,request_id='1'*32)
        self.assertEqual(self.client.prepare(self.initial,self.digest,request_id='1'*32),reserved)
        with self.assertRaises(Conflict):self.client.prepare(self.initial,self.digest,request_id='2'*32)
        changed = replace(self.initial,writer_epoch=2)
        with self.assertRaises(Conflict):self.client.prepare(changed,self.digest,request_id='1'*32)
        self.assertEqual(self.client.head()['reservation_id'],'1'*32)

    def test_old_generation_and_changed_key_or_previous_state_cannot_finish(self):
        reserved = self.client.prepare(self.initial,self.digest,request_id='1'*32)
        values = ((dict(reserved,generation=2),self.initial,self.digest),
                  (reserved,replace(self.initial,writer_epoch=2),self.digest),(reserved,self.initial,'f'*64))
        for reservation,previous,digest in values:
            with self.assertRaises(Conflict):self.client.finish(reservation,previous,self.target,digest,request_id=os.urandom(16).hex())
        self.assertEqual(self.client.head()['state'],self.initial)
        self.client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)
        newer = self.client.prepare(self.target,self.digest,request_id='3'*32)
        self.assertGreater(newer['generation'],reserved['generation'])
        with self.assertRaises(Conflict):self.client.finish(reserved,self.initial,self.target,self.digest,request_id='4'*32)

    def test_reservation_survives_restart_and_clock_advance_without_automatic_unlock(self):
        reserved = self.client.prepare(self.initial,self.digest,request_id='1'*32);self.now += 10000
        endpoint = rpc.SyntheticWitnessEndpoint(self.w,**self.options());_,client = self.serve(endpoint)
        self.assertEqual(client.head()['reservation_id'],reserved['reservation_id'])
        with self.assertRaises(Conflict):client.prepare(self.initial,self.digest,request_id='2'*32)
        # Only an explicit unchanged-state finish closes this fake reservation; source reconciliation must authorize it.
        client.finish(reserved,self.initial,self.initial,self.digest,request_id='3'*32)
        self.assertIsNone(client.head()['reservation_id'])

    def test_lost_prepare_reply_is_recovered_with_same_operation_and_new_nonce(self):
        original = self.w._db
        @contextmanager
        def lost():
            with original() as db:yield db
            raise OSError('Synthetic reply lost after commit')
        with patch.object(self.w,'_db',lost):
            with self.assertRaises(OSError):self.client.prepare(self.initial,self.digest,request_id='1'*32)
        reserved = self.client.prepare(self.initial,self.digest,request_id='1'*32)
        self.assertEqual(reserved['generation'],1)
        self.client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)

    def test_lost_finish_reply_retries_durably_but_stale_receipt_is_never_current(self):
        reserved = self.client.prepare(self.initial,self.digest,request_id='1'*32)
        with patch.object(self.client,'_reply',side_effect=OSError('Synthetic dropped reply')):
            with self.assertRaises(OSError):self.client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)
        endpoint = rpc.SyntheticWitnessEndpoint(self.w,**self.options());_,client = self.serve(endpoint)
        reply = client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)
        self.assertEqual(reply['state'],self.target)
        new = client.prepare(self.target,self.digest,request_id='3'*32)
        with self.assertRaises(Conflict):client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)
        self.assertEqual(client.head()['reservation_id'],new['reservation_id'])

    def test_forged_tampered_and_substituted_replies_are_rejected(self):
        first = self.raw({'op':'head'});second = self.raw({'op':'head'})
        status,body = self.endpoint.exchange(first)
        with self.assertRaises(PermissionError):self.client._reply(body,status,second)
        data=json.loads(body);data['result']['generation']=99
        with self.assertRaises(PermissionError):self.client._reply(_json(data).encode(),status,first)
        with self.assertRaises(ValueError):self.client._reply(b'x'*8193,status,first)
        data=json.loads(body);data.pop('mac');data['status']=True
        with self.assertRaises(PermissionError):self.client._reply(_json(rpc._sign(data,self.key,rpc.REPLY_DOMAIN)).encode(),status,first)

    def test_receipt_and_nonce_budgets_fail_closed(self):
        with patch.object(rpc,'MAX_RECEIPTS',0):
            with self.assertRaises(OSError):self.client.prepare(self.initial,self.digest,request_id='1'*32)
        with patch.object(rpc,'MAX_NONCES',0):
            with self.assertRaises(OSError):self.client.head()
        self.assertIsNone(self.client.head()['reservation_id'])

    def test_missing_schema_wrong_key_and_reenable_never_reset_trust(self):
        with self.assertRaises(Conflict):rpc.SyntheticWitnessEndpoint.enable(self.w,**self.options(),approved=True)
        with self.assertRaises(ValueError):rpc.SyntheticWitnessEndpoint(self.w,**dict(self.options(),key=os.urandom(32)))
        with self.w._db() as db:db.execute('DROP TABLE rpc_receipts')
        with self.assertRaises(sqlite3.DatabaseError):rpc.SyntheticWitnessEndpoint(self.w,**self.options())
        with self.assertRaises(OSError):self.client.head()
        with self.w._db() as db:self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='rpc_receipts'").fetchone())

    def test_failure_before_commit_rolls_back_head_reservation_and_receipt(self):
        reserved = self.client.prepare(self.initial,self.digest,request_id='1'*32);original=self.w._db
        @contextmanager
        def fail():
            with original() as db:
                yield db
                raise sqlite3.OperationalError('Synthetic commit failure with private diagnostics')
        with patch.object(self.w,'_db',fail):
            with self.assertRaises(OSError):self.client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)
        self.assertEqual(self.client.head()['state'],self.initial)
        self.assertEqual(self.client.head()['reservation_id'],reserved['reservation_id'])
        self.client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)

    def test_two_service_instances_have_one_reserved_winner(self):
        other_w = SyntheticWitness(self.w.path,synthetic_only=True)
        endpoint=rpc.SyntheticWitnessEndpoint(other_w,**self.options());_,client=self.serve(endpoint)
        barrier=threading.Barrier(2);results=[]
        def prepare(c,rid):
            try:barrier.wait(3);results.append(c.prepare(self.initial,self.digest,request_id=rid))
            except Exception as error:results.append(error)
        threads=[threading.Thread(target=prepare,args=(c,rid)) for c,rid in ((self.client,'1'*32),(client,'2'*32))]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(type(item) is dict for item in results),1)
        self.assertEqual(sum(isinstance(item,Conflict) for item in results),1)

    def test_http_boundaries_and_fake_only_binding(self):
        self.assertEqual(self.server.server_address[0],'127.0.0.1')
        with self.assertRaises(PermissionError):rpc.loopback_server(self.endpoint)
        with self.assertRaises(PermissionError):rpc.SyntheticWitnessClient(self.server.server_port,**dict(self.options(),synthetic_only=False))
        with self.assertRaises(ValueError):rpc.SyntheticWitnessClient('remote.example',**self.options())
        for method,path,headers,body in (('GET','/witness',{},None),('POST','/other',{'Content-Type':'application/json'},b'{}'),
            ('POST','/witness',{},b'{}'),('POST','/witness',{'Content-Type':'application/json','Content-Length':'9000'},b'')):
            connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
            try:
                connection.request(method,path,body=body,headers=headers);reply=connection.getresponse()
                self.assertIn(reply.status,(400,405));reply.read()
            except ConnectionError:
                # Closing without reading an invalid body can reset the TCP connection on Windows.
                pass
            finally:connection.close()
        with socket.create_connection(('127.0.0.1',self.server.server_port),timeout=2) as connection:
            connection.sendall(b'POST /witness HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 2\r\nContent-Length: 2\r\n\r\n{}')
            try:self.assertIn(b' 400 ',connection.recv(1024))
            except ConnectionError:pass
        self.assertEqual(self.client.head()['state'],self.initial)
        with self.assertRaises(ValueError):
            SyntheticAuthority(self.home/'not-created',recovery=SyntheticRecovery(SyntheticRecovery.new_key(),synthetic_only=True),
                               storage_key=os.urandom(32),synthetic_only=True,witness=self.client)
        self.assertFalse((self.home/'not-created').exists())

    def test_process_death_before_finish_commit_and_after_prepare_or_finish_commit(self):
        program=r'''
from contextlib import contextmanager
import json,os,sys
p=json.load(sys.stdin);sys.path.insert(0,p['root'])
from brain.memory_custody import SyntheticWitness
from brain.memory_witness_service import SyntheticWitnessEndpoint
w=SyntheticWitness(p['path'],synthetic_only=True)
e=SyntheticWitnessEndpoint(w,service=p['service'],client=p['client'],lineage=p['lineage'],key=bytes.fromhex(p['key']),synthetic_only=True,clock=lambda:p['now'])
original=w._db
@contextmanager
def die():
    with original() as db:
        yield db
        if p['before']:os._exit(17)
    os._exit(18)
w._db=die;e.exchange(p['raw'].encode())
'''
        def run(raw,before):
            packet=dict(root=str(Path(__file__).resolve().parent),path=str(self.w.path),service=self.service,client=self.client_id,
                        lineage=self.lineage,key=self.key.hex(),now=self.now,raw=raw.decode(),before=before)
            result=subprocess.run([sys.executable,'-I','-B','-c',program],input=json.dumps(packet),capture_output=True,text=True,
                                  timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(result.returncode,17 if before else 18,'Synthetic protocol child failed; raw output withheld.')
        run(self.raw(dict(op='prepare',previous=asdict(self.initial),keys_digest=self.digest),request_id='1'*32),False)
        reserved=self.client.prepare(self.initial,self.digest,request_id='1'*32)
        finish=dict(op='finish',reservation_id=reserved['reservation_id'],generation=reserved['generation'],
                    previous=asdict(self.initial),state=asdict(self.target),keys_digest=self.digest)
        run(self.raw(finish,request_id='2'*32),True)
        self.assertEqual(self.client.head()['state'],self.initial)
        run(self.raw(finish,request_id='2'*32),False)
        self.assertEqual(self.client.finish(reserved,self.initial,self.target,self.digest,request_id='2'*32)['state'],self.target)


if __name__=='__main__':unittest.main()
