"""Disposable local certificates, fake memory and loopback HTTPS only."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import ipaddress
import os
import socket
import ssl
import threading
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID,NameOID

from brain import memory_witness_service as rpc
import test_memory_witness_service as protocol
import test_memory_network_authority as network


def certificates(home,*,address='127.0.0.1',expired=False):
    """Fresh test CA/leaf; no system trust installation or retained private key."""
    now=datetime.now(timezone.utc);ca_key=ec.generate_private_key(ec.SECP256R1())
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'LYA SYNTHETIC TEST CA')])
    ca=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=2))
        .not_valid_after(now+timedelta(days=2)).add_extension(x509.BasicConstraints(ca=True,path_length=0),True)
        .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,None,None),True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),False)
        .sign(ca_key,hashes.SHA256()))
    key=ec.generate_private_key(ec.SECP256R1())
    leaf=(x509.CertificateBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME,'LYA SYNTHETIC TEST SERVER')]))
        .issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now-timedelta(days=1)).not_valid_after(now-timedelta(hours=1) if expired else now+timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),True)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(address))]),False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),False)
        .sign(ca_key,hashes.SHA256()))
    ca_path,cert_path,key_path=[home/name for name in ('test-ca.pem','test-server.pem','test-server-key.pem')]
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_path.write_bytes(leaf.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    server=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);server.minimum_version=ssl.TLSVersion.TLSv1_2
    server.load_cert_chain(cert_path,key_path)
    client=ssl.create_default_context(cafile=str(ca_path))
    client.minimum_version=ssl.TLSVersion.TLSv1_2
    return server,client


@contextmanager
def serving(endpoint,context):
    server=rpc.loopback_server(endpoint,synthetic_only=True,ssl_context=context)
    thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True)
    thread.start()
    try:yield server
    finally:
        server.shutdown();server.server_close();thread.join(3)
        if thread.is_alive():raise AssertionError('Synthetic TLS server did not stop.')


class WitnessTLSChecks(unittest.TestCase):
    def setUp(self):
        self.f=protocol.WitnessServiceChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.server_context,self.client_context=certificates(self.f.home)

    def client(self,server,**kwargs):
        values=dict(self.f.options(),ssl_context=self.client_context);values.update(kwargs)
        return rpc.SyntheticWitnessClient(server.server_port,**values)

    def test_fixture_pins_minimum_when_platform_default_is_unspecified(self):
        factory=ssl.create_default_context
        def unspecified(*args,**kwargs):
            context=factory(*args,**kwargs)
            context.minimum_version=ssl.TLSVersion.MINIMUM_SUPPORTED
            return context
        with patch.object(ssl,'create_default_context',side_effect=unspecified):
            server_context,client_context=certificates(self.f.home)
        self.assertEqual(client_context.minimum_version,ssl.TLSVersion.TLSv1_2)
        with serving(self.f.endpoint,server_context) as server:
            self.assertEqual(self.client(server,ssl_context=client_context).observe()['state'],self.f.initial)

    def test_tls_prepare_finish_retry_retirement_survive_service_restart(self):
        f=self.f;f.endpoint.enable_retirement(approved=True)
        with serving(f.endpoint,self.server_context) as server:
            client=self.client(server);self.assertEqual(server.server_address[0],'127.0.0.1')
            reserved=client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
        endpoint=rpc.SyntheticWitnessEndpoint(f.w,**f.options())
        with serving(endpoint,self.server_context) as server:
            client=self.client(server);self.assertEqual(client.observe()['reservation_id'],'1'*32)
            with patch.object(client,'_reply',side_effect=OSError('Synthetic TLS reply loss')):
                with self.assertRaises(OSError):client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
        endpoint=rpc.SyntheticWitnessEndpoint(f.w,**f.options())
        with serving(endpoint,self.server_context) as server:
            client=self.client(server)
            self.assertEqual(client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)['state'],f.target)
            self.assertEqual(client.retire(f.target,f.digest,generation=1)['retired_generation'],1)
        with serving(rpc.SyntheticWitnessEndpoint(f.w,**f.options()),self.server_context) as server:
            self.assertEqual(self.client(server).observe()['state'],f.target)
            self.assertEqual(f.endpoint.capacity()['retired_generation'],1)
            self.assertEqual(f.endpoint.capacity()['receipts'],0)

    def test_untrusted_expired_and_wrong_address_certificates_never_reach_protocol_or_fallback(self):
        f=self.f
        for kind in ('untrusted','wrong_address','expired'):
            with self.subTest(kind=kind):
                server_context,client_context=certificates(f.home,address='127.0.0.2' if kind=='wrong_address' else '127.0.0.1',
                                                           expired=kind=='expired')
                if kind=='untrusted':client_context=ssl.create_default_context()
                client_context.minimum_version=ssl.TLSVersion.TLSv1_2
                with serving(f.endpoint,server_context) as server,patch.object(f.endpoint,'exchange',side_effect=AssertionError('Unauthenticated TLS')):
                    with patch.object(rpc,'HTTPConnection',side_effect=AssertionError('TLS downgrade')):
                        with self.assertRaises(ssl.SSLCertVerificationError):self.client(server,ssl_context=client_context).observe()
        self.assertEqual(f.endpoint.capacity()['receipts'],0)

    def test_tls_still_requires_protocol_authentication_and_service_recovers(self):
        f=self.f
        with serving(f.endpoint,self.server_context) as server:
            with patch.object(f.endpoint,'_head',side_effect=AssertionError('Wrong protocol key')):
                with self.assertRaises((PermissionError,ValueError)):self.client(server,key=os.urandom(32)).observe()
            self.assertEqual(self.client(server).observe()['state'],f.initial)

    def test_invalid_roles_disabled_verification_and_mutated_context_are_refused(self):
        f=self.f
        for invalid in (object(),self.client_context):
            with self.assertRaises(ValueError):rpc.loopback_server(f.endpoint,synthetic_only=True,ssl_context=invalid)
        for invalid in (object(),self.server_context):
            with self.assertRaises(ValueError):rpc.SyntheticWitnessClient(f.server.server_port,**f.options(),ssl_context=invalid)
        with serving(f.endpoint,self.server_context) as server:
            client=self.client(server);self.client_context.check_hostname=False
            with self.assertRaises(ValueError):client.observe()
            self.client_context.verify_mode=ssl.CERT_NONE
            with self.assertRaises(ValueError):self.client(server)
        weak=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);weak.minimum_version=ssl.TLSVersion.MINIMUM_SUPPORTED
        with self.assertRaises(ValueError):rpc.loopback_server(f.endpoint,synthetic_only=True,ssl_context=weak)

    def test_plaintext_and_silent_handshake_are_rejected_and_socket_closes(self):
        f=self.f
        with serving(f.endpoint,self.server_context) as server:
            port=server.server_port
            with socket.create_connection(('127.0.0.1',port),timeout=4) as connection:
                connection.sendall(b'GET /witness HTTP/1.0\r\n\r\n')
                try:self.assertEqual(connection.recv(1024),b'')
                except ConnectionError:pass
            with socket.create_connection(('127.0.0.1',port),timeout=4) as connection:
                self.assertEqual(connection.recv(1024),b'')
            self.assertEqual(self.client(server).observe()['state'],f.initial)
        with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=1)


@unittest.skipIf(network.cipher is None,'Use the isolated TLS runner.')
class AuthorityTLSChecks(unittest.TestCase):
    def setUp(self):
        self.f=network.NetworkAuthorityChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp();self.f.endpoint.enable_retirement(approved=True)
        self.server_context,self.client_context=certificates(self.f.f.home)

    def connect(self,server):
        self.f.client=self.f.new_client(ssl_context=self.client_context)
        self.f.client.port=server.server_port;self.f.a=self.f.open()

    def test_committed_reply_loss_reconciles_after_tls_restart_and_retirement(self):
        f=self.f;packet=f.f.packet()
        with serving(f.endpoint,self.server_context) as server:
            self.connect(server);original=f.client.finish
            def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic TLS finish reply loss')
            with patch.object(f.client,'finish',side_effect=lost):
                with self.assertRaises(OSError):f.call(packet)
            committed=f.local();self.assertEqual(f.journal()['phase'],'committed')
        endpoint=rpc.SyntheticWitnessEndpoint(f.w,service='a'*32,client='b'*32,lineage=f.lineage,key=f.protocol_key,
                                               synthetic_only=True,clock=lambda:f.f.now)
        with serving(endpoint,self.server_context) as server:
            self.connect(server);reply=f.reconcile()
            self.assertEqual(reply['anchor'],committed.anchor);self.assertNotIn('result',reply);self.assertNotIn('grant',reply)
            self.assertEqual(f.journal()['phase'],'idle')
            f.a.retire_receipts(f.lineage,approved=True)
            self.assertEqual(f.call(packet)['operation'],'save')

    def test_tls_trust_failure_blocks_before_local_intent_and_does_not_change_state(self):
        f=self.f
        with serving(f.endpoint,self.server_context) as server:
            self.connect(server);f.client.ssl_context=ssl.create_default_context()
            f.client.ssl_context.minimum_version=ssl.TLSVersion.TLSv1_2
            with self.assertRaises(ssl.SSLCertVerificationError):f.call(f.f.packet())
            self.assertEqual(f.journal()['phase'],'idle');self.assertEqual(f.local(),f.initial)
            self.assertEqual(f.endpoint.capacity()['receipts'],0)


if __name__=='__main__':unittest.main()
