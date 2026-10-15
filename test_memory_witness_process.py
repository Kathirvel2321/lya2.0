"""Fake-key TLS witness processes; disposable stores and loopback connections only."""
from contextlib import contextmanager
from http.client import HTTPSConnection
import json
import os
from pathlib import Path
import queue
import socket
import ssl
import subprocess
import sys
import threading
import unittest

from brain import memory_witness_service as rpc
from brain.memory_custody import SyntheticWitness
from brain.memory_prototype import Conflict
import test_memory_witness_service as protocol
import test_memory_witness_tls as tls
import test_memory_network_authority as network


BOOTSTRAP = "import json,sys; p=json.loads(sys.stdin.readline()); sys.path.insert(0,p.pop('root')); from test_memory_witness_process import worker; worker(p)"


def worker(packet):
    """Test-only process entry point; never creates or replaces trust on startup."""
    if 'process_budget' in packet:
        from brain.memory_witness_budget import apply_synthetic_budget
        apply_synthetic_budget(synthetic_only=packet['process_budget'],approved=True)
    witness=SyntheticWitness(packet['path'],synthetic_only=True)
    endpoint=rpc.SyntheticWitnessEndpoint(witness,service=packet['service'],client=packet['client'],
        lineage=packet['lineage'],key=bytes.fromhex(packet['key']),synthetic_only=True,clock=lambda:packet['now'])
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
    home=Path(packet['home']);context.load_cert_chain(home/'test-server.pem',home/'test-server-key.pem')
    if packet['point']:
        exchange=endpoint.exchange;original_db=witness._db
        def stop():
            if packet['point'].startswith('pause_'):
                print('paused',flush=True)
                threading.Event().wait(15)
            os._exit(70 if packet['point'].endswith('before_commit') else 71)
        @contextmanager
        def interrupted():
            with original_db() as db:
                yield db
                if packet['point'].endswith('before_commit'):stop()
            stop()
        def fault(raw):
            if json.loads(raw)['operation']['op']==packet['operation']:witness._db=interrupted
            return exchange(raw)
        endpoint.exchange=fault
    with rpc.loopback_server(endpoint,synthetic_only=True,ssl_context=context) as server:
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01})
        thread.start();print(server.server_port,flush=True)
        try:sys.stdin.readline()
        finally:
            server.shutdown();thread.join(4)
            if thread.is_alive():os._exit(72)


def packet(home,path,*,service,client,lineage,key,now,point=None,operation=None):
    return dict(root=str(Path(__file__).resolve().parent),home=str(home),path=str(path),service=service,
                client=client,lineage=lineage,key=key.hex(),now=now,point=point,operation=operation)


@contextmanager
def process_server(values):
    process=subprocess.Popen([sys.executable,'-I','-B','-c',BOOTSTRAP],stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    signals=queue.Queue(maxsize=4)
    def read_signals():
        for line in process.stdout:signals.put(line.strip())
    reader=threading.Thread(target=read_signals,daemon=True)
    reader.start()
    try:
        process.stdin.write(json.dumps(values)+'\n');process.stdin.flush()
        port=int(signals.get(timeout=15))
        context=ssl.create_default_context(cafile=str(Path(values['home'])/'test-ca.pem'))
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        client=rpc.SyntheticWitnessClient(port,service=values['service'],client=values['client'],
            lineage=values['lineage'],key=bytes.fromhex(values['key']),synthetic_only=True,
            clock=lambda:values['now'],ssl_context=context)
        yield process,client,signals
    finally:
        if process.poll() is None:
            try:
                process.stdin.write('stop\n');process.stdin.flush();process.wait(timeout=6)
            except (OSError,subprocess.TimeoutExpired):process.kill();process.wait(timeout=5)
        try:process.stdin.close()
        except OSError:pass
        reader.join(3);process.stdout.close()
        if reader.is_alive():raise AssertionError('Synthetic process output reader did not stop.')


class WitnessProcessChecks(unittest.TestCase):
    def fixture(self):
        f=protocol.WitnessServiceChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp()
        f.endpoint.enable_retirement(approved=True);tls.certificates(f.home)
        return f

    def values(self,f,**kwargs):
        return packet(f.home,f.w.path,service=f.service,client=f.client_id,lineage=f.lineage,
                      key=f.key,now=f.now,**kwargs)

    def test_external_termination_preserves_pending_reservation_and_releases_listener(self):
        f=self.fixture()
        with process_server(self.values(f)) as (process,client,_):
            reserved=client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
            port=client.port;process.kill();process.wait(timeout=5)
            with self.assertRaises(OSError):client.observe()
            with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=1)
        with process_server(self.values(f)) as (_,client,_):
            self.assertEqual(client.observe()['reservation_id'],reserved['reservation_id'])
            client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
            self.assertEqual(client.retire(f.target,f.digest,generation=1)['retired_generation'],1)
        self.assertEqual(f.w.head(f.lineage),(f.target,f.digest))

    def test_process_exit_before_and_after_prepare_finish_and_retirement_commits(self):
        for operation in ('prepare','finish','retire'):
            for point in ('before_commit','after_commit'):
                with self.subTest(operation=operation,point=point):
                    f=self.fixture();reserved=None
                    if operation!='prepare':
                        with process_server(self.values(f)) as (_,client,_):
                            reserved=client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
                            if operation=='retire':client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
                    def request(client):
                        if operation=='prepare':return client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
                        if operation=='finish':return client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
                        return client.retire(f.target,f.digest,generation=1)
                    with process_server(self.values(f,point=point,operation=operation)) as (process,client,_):
                        with self.assertRaises(OSError):request(client)
                        self.assertEqual(process.wait(timeout=5),70 if point=='before_commit' else 71)
                    with process_server(self.values(f)) as (_,client,_):
                        head=client.observe();after=point=='after_commit';counters=f.endpoint.capacity()
                        expected=f.target if operation=='retire' or (operation=='finish' and after) else f.initial
                        self.assertEqual(head['state'],expected)
                        pending=(operation=='prepare' and after) or (operation=='finish' and not after)
                        self.assertEqual(head['reservation_id'],'1'*32 if pending else None)
                        self.assertEqual(head['generation'],0 if operation=='prepare' and not after else 1)
                        receipts={'prepare':int(after),'finish':1+int(after),'retire':0 if after else 2}[operation]
                        self.assertEqual(counters['receipts'],receipts)
                        self.assertEqual(counters['retired_generation'],int(operation=='retire' and after))
                        result=request(client)
                        if operation=='prepare':self.assertEqual(result['reservation_id'],'1'*32)
                        elif operation=='finish':self.assertEqual(result['state'],f.target)
                        else:self.assertEqual(result['retired_generation'],1)

    def test_external_kill_at_synchronized_transaction_boundaries(self):
        for point in ('pause_before_commit','pause_after_commit'):
            with self.subTest(point=point):
                f=self.fixture();results=[]
                with process_server(self.values(f,point=point,operation='prepare')) as (process,client,signals):
                    def request():
                        try:results.append(client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0))
                        except OSError as error:results.append(error)
                    thread=threading.Thread(target=request);thread.start()
                    try:
                        self.assertEqual(signals.get(timeout=5),'paused');process.kill();process.wait(timeout=5)
                    finally:
                        if process.poll() is None:process.kill();process.wait(timeout=5)
                        thread.join(4)
                    self.assertFalse(thread.is_alive());self.assertEqual(len(results),1);self.assertIsInstance(results[0],OSError)
                with process_server(self.values(f)) as (_,client,_):
                    after=point=='pause_after_commit';head=client.observe()
                    self.assertEqual(head['generation'],int(after))
                    self.assertEqual(head['reservation_id'],'1'*32 if after else None)
                    self.assertEqual(f.endpoint.capacity()['receipts'],int(after))
                    self.assertEqual(client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)['generation'],1)

    def test_graceful_process_stop_during_silent_handshake_or_incomplete_body(self):
        f=self.fixture();before=f.w.path.read_bytes()
        for stage in ('handshake','body'):
            with self.subTest(stage=stage),process_server(self.values(f)) as (process,client,_):
                raw=socket.create_connection(('127.0.0.1',client.port),timeout=4)
                connection=client.ssl_context.wrap_socket(raw,server_hostname='127.0.0.1') if stage=='body' else raw
                with connection:
                    if stage=='body':
                        connection.sendall(b'POST /witness HTTP/1.0\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{')
                    process.stdin.write('stop\n');process.stdin.flush()
                    self.assertEqual(process.wait(timeout=5),0)
                    try:self.assertEqual(connection.recv(1024),b'')
                    except ConnectionError:pass
        self.assertEqual(f.w.path.read_bytes(),before)

    def test_body_rejection_and_repeated_observations_keep_durable_state_bounded(self):
        f=self.fixture()
        with process_server(self.values(f)) as (_,client,_):
            connection=HTTPSConnection('127.0.0.1',client.port,timeout=3,context=client.ssl_context)
            try:
                connection.request('POST','/witness',body=b'',headers={
                    'Content-Type':'application/json','Content-Length':str(rpc.MAX_BODY+1)})
                response=connection.getresponse();self.assertEqual(response.status,400);response.read()
            finally:connection.close()
            self.assertEqual(f.endpoint.capacity()['live_nonces'],0)
            for _ in range(40):self.assertEqual(client.observe()['state'],f.initial)
        counters=f.endpoint.capacity()
        self.assertEqual(counters['receipts'],0);self.assertEqual(counters['live_nonces'],40)
        self.assertLessEqual(counters['database_bytes'],counters['database_limit_bytes'])
        self.assertEqual(f.w.head(f.lineage),(f.initial,f.digest))

    def test_missing_corrupt_or_wrong_key_trust_refuses_startup_without_recreation(self):
        f=self.fixture();original=f.w.path.read_bytes()
        corrupt=f.home/'corrupt.sqlite';corrupt.write_bytes(b'SYNTHETIC_CORRUPTION')
        for kind in ('missing','corrupt','key'):
            with self.subTest(kind=kind):
                values=self.values(f)
                if kind=='missing':values['path']=str(f.home/'missing.sqlite')
                elif kind=='corrupt':values['path']=str(corrupt)
                else:values['key']=os.urandom(32).hex()
                result=subprocess.run([sys.executable,'-I','-B','-c',BOOTSTRAP],input=json.dumps(values)+'\n',
                    capture_output=True,text=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertNotEqual(result.returncode,0,'Synthetic startup unexpectedly succeeded.')
                self.assertEqual(result.stdout,'');self.assertFalse((f.home/'missing.sqlite').exists())
                self.assertEqual(corrupt.read_bytes(),b'SYNTHETIC_CORRUPTION');self.assertEqual(f.w.path.read_bytes(),original)


@unittest.skipIf(network.cipher is None,'Use the isolated witness process runner.')
class AuthorityProcessChecks(unittest.TestCase):
    def test_tls_witness_death_during_finish_reconciles_committed_source_without_lost_grants(self):
        for point in ('before_commit','after_commit'):
            with self.subTest(point=point):
                f=network.NetworkAuthorityChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp()
                f.endpoint.enable_retirement(approved=True);tls.certificates(f.f.home)
                values=packet(f.f.home,f.w.path,service='a'*32,client='b'*32,lineage=f.lineage,
                              key=f.protocol_key,now=f.f.now,point=point,operation='finish')
                request=f.f.packet()
                with process_server(values) as (process,client,_):
                    f.client=client;f.a=f.open()
                    with self.assertRaises(OSError):f.call(request)
                    self.assertEqual(process.wait(timeout=5),70 if point=='before_commit' else 71)
                committed=f.local();self.assertEqual(f.journal()['phase'],'committed')
                self.assertGreater(committed.anchor.sequence,f.initial.anchor.sequence)
                values['point']=None
                with process_server(values) as (_,client,_):
                    f.client=client;f.a=f.open()
                    with self.assertRaises(Conflict):f.a.head(f.lineage)
                    reply=f.reconcile();self.assertEqual(reply['anchor'],committed.anchor)
                    self.assertNotIn('result',reply);self.assertNotIn('grant',reply)
                    self.assertEqual(f.journal()['phase'],'idle');self.assertIsNone(client.observe()['reservation_id'])
                    saved=f.call(request);self.assertEqual(f.call(request),saved)
                    self.assertEqual(f.local(),committed)
                    generation=client.observe()['generation']
                    self.assertEqual(f.a.retire_receipts(f.lineage,approved=True)['retired_generation'],generation)
                    self.assertEqual(f.endpoint.capacity()['receipts'],0)


if __name__=='__main__':unittest.main()
