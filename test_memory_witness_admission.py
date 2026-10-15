"""Fake-data HTTP/TLS request budgets; loopback only, no real stores or keys."""
from contextlib import contextmanager
from http.client import HTTPResponse,HTTPSConnection
import socket
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from brain import memory_witness_service as rpc
from brain.memory_prototype import _json
import test_memory_witness_service as protocol
import test_memory_witness_tls as tls


class WitnessAdmissionChecks(unittest.TestCase):
    def setUp(self):
        self.f=protocol.WitnessServiceChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.server_context,self.client_context=tls.certificates(self.f.home)

    @contextmanager
    def serving(self):
        with tls.serving(self.f.endpoint,self.server_context) as server:
            client=rpc.SyntheticWitnessClient(server.server_port,**self.f.options(),ssl_context=self.client_context)
            yield server,client

    def test_continuous_header_and_body_drips_cannot_extend_the_io_deadline(self):
        for secure in (False,True):
            for stage in ('headers','body'):
                with self.subTest(secure=secure,stage=stage),self.serving() as (_,client):
                    port=client.port if secure else self.f.server.server_port
                    connection=socket.create_connection(('127.0.0.1',port),timeout=3)
                    if secure:connection=self.client_context.wrap_socket(connection,server_hostname='127.0.0.1')
                    with connection:
                        connection.settimeout(.12)
                        prefix=b'POST /witness HTTP/1.0\r\n'
                        prefix+=(b'X-Drip: ' if stage=='headers' else
                            b'Content-Type: application/json\r\nContent-Length: 8192\r\n\r\n')
                        connection.sendall(prefix);closed=False;started=time.monotonic()
                        while time.monotonic()-started<4:
                            try:
                                connection.sendall(b'x')
                                try:data=connection.recv(1024)
                                except socket.timeout:continue
                                if not data:closed=True;break
                            except OSError:closed=True;break
                        self.assertTrue(closed,'Continuous input kept the connection open beyond its I/O budget.')
                    self.assertEqual(client.observe()['state'],self.f.initial)

    def test_aggregate_headers_are_rejected_before_protocol_access(self):
        f=self.f;before=f.w.path.read_bytes()
        with self.serving() as (_,client),patch.object(f.endpoint,'exchange',wraps=f.endpoint.exchange) as exchange:
            connection=HTTPSConnection('127.0.0.1',client.port,timeout=3,context=self.client_context)
            try:
                headers={'Content-Type':'application/json',**{f'X-Pad-{i}':'x'*128 for i in range(80)}}
                connection.request('POST','/witness',body=b'{}',headers=headers)
                try:self.assertIn(connection.getresponse().status,(400,414,431))
                except OSError:pass
            finally:connection.close()
            self.assertEqual(exchange.call_count,0)
        self.assertEqual(f.w.path.read_bytes(),before)

    def test_exact_header_budget_accepts_authenticated_body_without_counting_body_as_headers(self):
        f=self.f;raw=_json(f.client._packet({'op':'observe'},'1'*32)).encode()
        prefix=(b'POST /witness HTTP/1.0\r\nContent-Type: application/json\r\nContent-Length: '+
                str(len(raw)).encode()+b'\r\nX-Pad: ')
        headers=prefix+b'x'*(8192-len(prefix)-4)+b'\r\n\r\n';self.assertEqual(len(headers),8192)
        with self.serving() as (_,client):
            with socket.create_connection(('127.0.0.1',client.port),timeout=3) as connection:
                with self.client_context.wrap_socket(connection,server_hostname='127.0.0.1') as secure:
                    secure.sendall(headers+raw);reply=HTTPResponse(secure);reply.begin()
                    self.assertEqual(client._reply(reply.read(),reply.status,raw)['state'],f.initial)
            self.assertEqual(client.observe()['state'],f.initial)
        self.assertEqual(f.endpoint.capacity()['receipts'],0)

    def test_expired_delivery_withholds_reply_but_preserves_exact_commit_retry(self):
        f=self.f;now=[0.];original=f.endpoint.exchange
        def expired(raw):
            reply=original(raw);now[0]+=3;return reply
        with patch.object(rpc,'time',SimpleNamespace(monotonic=lambda:now[0])),self.serving() as (_,client):
            with patch.object(f.endpoint,'exchange',side_effect=expired):
                with self.assertRaises(OSError):client.prepare(f.initial,f.digest,request_id='1'*32)
            self.assertEqual(f.endpoint.capacity()['receipts'],1)
            retry=client.prepare(f.initial,f.digest,request_id='1'*32)
            self.assertEqual((retry['reservation_id'],retry['generation']),('1'*32,1))
            self.assertEqual(f.endpoint.capacity()['receipts'],1)


if __name__=='__main__':unittest.main()
