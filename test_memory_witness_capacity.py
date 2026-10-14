"""Fake-data receipt/drain/storage limits; localhost only and temporary encrypted fixtures."""
import os
import sqlite3
import unittest
from unittest.mock import patch

from brain import memory_witness_service as rpc
from brain.memory_prototype import Conflict
import test_memory_witness_service as protocol
import test_memory_network_authority as network


class WitnessCapacityChecks(unittest.TestCase):
    def setUp(self):
        self.f = protocol.WitnessServiceChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()

    def test_signed_observation_has_no_receipts_and_still_rejects_nonce_replay(self):
        f = self.f;rid = '1'*32
        raw = f.raw({'op':'observe'},request_id=rid)
        status,body = f.endpoint.exchange(raw)
        self.assertEqual(f.client._reply(body,status,raw)['state'],f.initial)
        self.assertEqual(f.endpoint.exchange(raw)[0],409)
        reserved = f.client.prepare(f.initial,f.digest,request_id='2'*32)
        fresh = f.raw({'op':'observe'},request_id=rid)
        status,body = f.endpoint.exchange(fresh)
        self.assertEqual(f.client._reply(body,status,fresh)['reservation_id'],reserved['reservation_id'])
        self.assertEqual(f.endpoint.capacity()['receipts'],1)
        with self.assertRaises(PermissionError):f.client._reply(body,status,raw)
        # Observations cannot impersonate or change a durable mutation receipt's meaning.
        self.assertEqual(f.endpoint.exchange(f.raw({'op':'observe'},request_id='2'*32))[0],409)

    def test_last_receipt_slot_is_kept_for_finish_and_retry_survives_full_restart(self):
        f = self.f
        with patch.object(rpc,'MAX_RECEIPTS',2):
            reserved = f.client.prepare(f.initial,f.digest,request_id='1'*32)
            for _ in range(4):
                with self.assertRaises(OSError):f.client.head()
                self.assertEqual(f.client.observe()['reservation_id'],reserved['reservation_id'])
            with self.assertRaises(OSError):f.client.prepare(f.initial,f.digest,request_id='3'*32)
            with patch.object(f.client,'_reply',side_effect=OSError('Synthetic finish reply loss')):
                with self.assertRaises(OSError):f.client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
            endpoint = rpc.SyntheticWitnessEndpoint(f.w,**f.options());_,client = f.serve(endpoint)
            self.assertEqual(client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)['state'],f.target)
            self.assertEqual(client.observe()['state'],f.target)
            self.assertEqual(endpoint.capacity()['receipts'],2)
            self.assertFalse(endpoint.capacity()['reservation_pending'])
            with self.assertRaises(Conflict):client.prepare(f.initial,f.digest,request_id='1'*32)
            with self.assertRaises(OSError):client.prepare(f.target,f.digest,request_id='4'*32)

    def test_prepare_requires_two_free_slots_and_preflight_does_not_reserve(self):
        f = self.f
        with patch.object(rpc,'MAX_RECEIPTS',2):
            f.client.head()
            with self.assertRaises(OSError):f.client.observe(require_prepare_capacity=True)
            with self.assertRaises(OSError):f.client.prepare(f.initial,f.digest,request_id='1'*32)
            self.assertFalse(f.endpoint.capacity()['prepare_receipt_capacity'])
            self.assertIsNone(f.client.observe()['reservation_id'])
            self.assertEqual(f.endpoint.capacity()['receipts'],1)

    def test_expired_nonce_cleanup_restores_observation_without_discarding_receipts(self):
        f = self.f
        f.client.head();count = f.endpoint.capacity()['receipts']
        with patch.object(rpc,'MAX_NONCES',3):
            f.client.observe();f.client.observe()
            with self.assertRaises(OSError):f.client.observe()
            f.now += rpc.WINDOW+1
            self.assertEqual(f.client.observe()['state'],f.initial)
            counters = f.endpoint.capacity()
            self.assertEqual(counters['live_nonces'],1);self.assertEqual(counters['receipts'],count)

    def test_observation_flags_and_authentication_are_strict(self):
        f = self.f
        for value in (None,1,'yes'):
            with self.assertRaises(ValueError):f.client.observe(require_prepare_capacity=value)
        for operation in ({'op':'observe','prepare_capacity':1},{'op':'observe','prepare_capacity':False},
                          {'op':'observe','value':'SYNTHETIC_PRIVATE'}):
            status,body = f.endpoint.exchange(f.raw(operation))
            self.assertEqual(status,400);self.assertNotIn(b'SYNTHETIC_PRIVATE',body)
        wrong = rpc.SyntheticWitnessClient(f.server.server_port,**dict(f.options(),key=os.urandom(32)))
        with patch.object(f.endpoint,'_head',side_effect=AssertionError('Unauthenticated state access')):
            with self.assertRaises((PermissionError,ValueError)):wrong.observe()

    def test_capacity_is_content_free_and_observations_do_not_change_generation(self):
        f = self.f;expected = {'receipts','receipt_limit','live_nonces','nonce_limit','reservation_pending',
                              'prepare_receipt_capacity','database_bytes','database_limit_bytes','synthetic_only'}
        for _ in range(12):self.assertEqual(f.client.observe()['generation'],0)
        result = f.endpoint.capacity();self.assertEqual(set(result),expected)
        self.assertEqual(result['receipts'],0);self.assertFalse(result['reservation_pending'])
        self.assertLessEqual(result['database_bytes'],result['database_limit_bytes'])

    def test_database_page_budget_refuses_growth_with_full_rollback(self):
        f = self.f;before = f.client.observe()
        with self.assertRaises(sqlite3.DatabaseError):
            with f.w._db() as db:
                f.endpoint._schema(db)
                db.execute('CREATE TABLE capacity_fixture(value BLOB)')
                for _ in range(8):db.execute('INSERT INTO capacity_fixture VALUES(zeroblob(1048576))')
        self.assertEqual(f.client.observe(),before)
        self.assertLessEqual(f.w.path.stat().st_size,rpc.MAX_DATABASE_BYTES)
        with f.w._db() as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='capacity_fixture'").fetchone())

    def test_oversized_existing_database_is_refused_without_resetting_trust(self):
        f = self.f;before = f.w.path.read_bytes()
        with patch.object(rpc,'MAX_DATABASE_BYTES',1):
            with self.assertRaises(OSError):rpc.SyntheticWitnessEndpoint(f.w,**f.options())
            with self.assertRaises(OSError):f.client.observe()
        self.assertEqual(f.w.path.read_bytes(),before)
        self.assertEqual(f.client.observe()['state'],f.initial)


@unittest.skipIf(network.cipher is None,'Use the isolated witness capacity runner.')
class NetworkCapacityChecks(unittest.TestCase):
    def setUp(self):
        self.f = network.NetworkAuthorityChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()

    def test_capacity_preflight_refuses_new_work_before_local_intent(self):
        f = self.f
        with patch.object(rpc,'MAX_RECEIPTS',1):
            with self.assertRaises(OSError):f.call(f.f.packet())
            self.assertEqual(f.journal()['phase'],'idle')
            self.assertEqual(f.local(),f.initial);self.assertIsNone(f.client.observe()['reservation_id'])

    def test_full_receipts_allow_committed_reconciliation_but_stop_the_next_write(self):
        f = self.f;packet = f.f.packet();original = f.client.finish
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic last-slot reply loss')
        with patch.object(rpc,'MAX_RECEIPTS',2):
            with patch.object(f.client,'finish',side_effect=lost):
                with self.assertRaises(OSError):f.call(packet)
            committed = f.local();self.assertEqual(f.endpoint.capacity()['receipts'],2)
            self.assertEqual(f.journal()['phase'],'committed');f.assert_blocked()
            f.a = f.open();reply = f.reconcile()
            self.assertEqual(reply['anchor'],committed.anchor);self.assertNotIn('result',reply);self.assertNotIn('grant',reply)
            self.assertEqual(f.journal()['phase'],'idle')
            self.assertEqual(f.client.observe()['state'],committed)
            with self.assertRaises(OSError):f.call(f.f.packet('full'))
            self.assertEqual(f.journal()['phase'],'idle');self.assertEqual(f.local(),committed)


if __name__=='__main__':unittest.main()
