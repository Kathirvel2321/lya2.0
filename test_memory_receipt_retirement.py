"""Disposable generation-scoped receipt retirement; localhost only, fake keys and owners."""
from contextlib import closing,contextmanager
from dataclasses import asdict,replace
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from brain import memory_witness_service as rpc
from brain.memory_prototype import Conflict
import test_memory_witness_service as protocol
import test_memory_network_authority as network


class RetirementProtocolChecks(unittest.TestCase):
    def setUp(self):
        self.f = protocol.WitnessServiceChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.f.endpoint.enable_retirement(approved=True)

    def cycle(self,previous=None,generation=0):
        f=self.f;previous=previous or f.initial
        reserved=f.client.prepare(previous,f.digest,request_id=os.urandom(16).hex(),expected_generation=generation)
        target=replace(previous,writer_epoch=previous.writer_epoch+1)
        f.client.finish(reserved,previous,target,f.digest,request_id=os.urandom(16).hex())
        return target,reserved

    def test_explicit_fresh_setup_rejects_reenable_and_legacy_history(self):
        f=self.f
        for approval in (False,1,None):
            with self.assertRaises(PermissionError):f.endpoint.enable_retirement(approved=approval)
        with self.assertRaises(Conflict):f.endpoint.enable_retirement(approved=True)
        other=protocol.WitnessServiceChecks(methodName='runTest');self.addCleanup(other.doCleanups);other.setUp()
        other.client.head();before=other.w.path.read_bytes()
        with self.assertRaises(Conflict):other.endpoint.enable_retirement(approved=True)
        self.assertEqual(other.w.path.read_bytes(),before);self.assertNotIn('retired_generation',other.endpoint.capacity())
        with self.assertRaises(ValueError):other.client.retire(other.initial,other.digest,generation=0)

    def test_generation_floor_rejects_retired_requests_with_new_nonces_and_ids(self):
        f=self.f
        prepare=dict(op='prepare',previous=asdict(f.initial),keys_digest=f.digest,expected_generation=0)
        raw=f.raw(prepare,request_id='1'*32);status,body=f.endpoint.exchange(raw)
        reserved=f.client._reply(body,status,raw)
        finish=dict(op='finish',reservation_id=reserved['reservation_id'],generation=1,previous=asdict(f.initial),
                    state=asdict(f.target),keys_digest=f.digest)
        f.client.request(finish,request_id='2'*32)
        confirmed=f.client.retire(f.target,f.digest,generation=1)
        self.assertEqual(confirmed['retired_generation'],1);self.assertEqual(f.endpoint.capacity()['receipts'],0)
        for operation in (prepare,finish):
            for rid in ('1'*32,os.urandom(16).hex()):
                self.assertEqual(f.endpoint.exchange(f.raw(operation,request_id=rid))[0],409)
        # IDs are scoped by generation after opt-in; only a newly signed higher-generation operation may reuse one.
        new=f.client.prepare(f.target,f.digest,request_id='1'*32,expected_generation=1)
        self.assertEqual(new['generation'],2)

    def test_unknown_generation_legacy_head_and_malformed_retirement_are_rejected(self):
        f=self.f
        with self.assertRaises(ValueError):f.client.head()
        with self.assertRaises(ValueError):f.client.prepare(f.initial,f.digest,request_id='1'*32)
        for operation in (dict(op='prepare',previous=asdict(f.initial),keys_digest=f.digest,expected_generation=True),
                          dict(op='retire',state=asdict(f.initial),keys_digest=f.digest,generation=True),
                          dict(op='retire',state=asdict(f.initial),keys_digest=f.digest,generation=0,value='SYNTHETIC_PRIVATE')):
            status,body=f.endpoint.exchange(f.raw(operation));self.assertEqual(status,400)
            self.assertNotIn(b'SYNTHETIC_PRIVATE',body)
        self.assertEqual(f.endpoint.capacity()['receipts'],0)

    def test_pending_reservation_and_wrong_state_custody_or_generation_never_retire(self):
        f=self.f
        reserved=f.client.prepare(f.initial,f.digest,request_id='1'*32,expected_generation=0)
        with self.assertRaises(Conflict):f.client.retire(f.initial,f.digest,generation=1)
        self.assertEqual(f.endpoint.capacity()['receipts'],1)
        f.client.finish(reserved,f.initial,f.target,f.digest,request_id='2'*32)
        for state,digest,generation in ((f.initial,f.digest,1),(f.target,'f'*64,1),(f.target,f.digest,0),(f.target,f.digest,2)):
            with self.assertRaises(Conflict):f.client.retire(state,digest,generation=generation)
        self.assertEqual(f.endpoint.capacity()['receipts'],2);self.assertEqual(f.endpoint.capacity()['retired_generation'],0)

    def test_floor_and_deletion_commit_atomically_and_lost_reply_retries_without_a_receipt(self):
        f=self.f;target,_=self.cycle();original=f.w._db
        @contextmanager
        def failed():
            with original() as db:
                yield db
                raise sqlite3.OperationalError('Synthetic retirement commit failure')
        with patch.object(f.w,'_db',failed):
            with self.assertRaises(OSError):f.client.retire(target,f.digest,generation=1)
        self.assertEqual(f.endpoint.capacity()['retired_generation'],0);self.assertEqual(f.endpoint.capacity()['receipts'],2)
        with patch.object(f.client,'_reply',side_effect=OSError('Synthetic retirement reply lost')):
            with self.assertRaises(OSError):f.client.retire(target,f.digest,generation=1)
        endpoint=rpc.SyntheticWitnessEndpoint(f.w,**f.options());_,client=f.serve(endpoint)
        self.assertEqual(client.retire(target,f.digest,generation=1)['retired_generation'],1)
        self.assertEqual(endpoint.capacity()['receipts'],0)

    def test_retirement_preserves_nonces_authentication_and_reply_correlation(self):
        f=self.f;observation=f.raw({'op':'observe'});self.assertEqual(f.endpoint.exchange(observation)[0],200)
        target,_=self.cycle();f.client.retire(target,f.digest,generation=1)
        self.assertEqual(f.endpoint.exchange(observation)[0],409)
        request=f.raw(dict(op='retire',state=asdict(target),keys_digest=f.digest,generation=1))
        status,body=f.endpoint.exchange(request)
        other=f.raw(dict(op='retire',state=asdict(target),keys_digest=f.digest,generation=1))
        with self.assertRaises(PermissionError):f.client._reply(body,status,other)
        tampered=json.loads(body);tampered.pop('mac');tampered['result']['retired_generation']=0
        with self.assertRaises(ValueError):
            f.client._reply(json.dumps(rpc._sign(tampered,f.key,rpc.REPLY_DOMAIN)).encode(),status,request)
        bad=rpc.SyntheticWitnessClient(f.server.server_port,**dict(f.options(),key=os.urandom(32)))
        with patch.object(f.endpoint,'_head',side_effect=AssertionError('Unauthorized state access')):
            with self.assertRaises((PermissionError,ValueError)):bad.retire(target,f.digest,generation=1)
        with patch.object(rpc,'MAX_NONCES',0):
            with self.assertRaises(OSError):f.client.retire(target,f.digest,generation=1)

    def test_missing_corrupt_or_downgraded_floor_is_never_recreated(self):
        f=self.f;backup=f.home/'safe.sqlite'
        with closing(sqlite3.connect(f.w.path)) as db,closing(sqlite3.connect(backup)) as destination:db.backup(destination)
        for statement in ('DELETE FROM rpc_retirement','UPDATE rpc_retirement SET retired_generation=1',
                          'DROP TABLE rpc_retirement','UPDATE rpc_meta SET version=1'):
            with f.w._db() as db:db.execute(statement)
            with self.assertRaises((ValueError,sqlite3.DatabaseError)):rpc.SyntheticWitnessEndpoint(f.w,**f.options())
            with self.assertRaises((OSError,ValueError)):f.client.observe()
            shutil.copyfile(backup,f.w.path)
        self.assertEqual(f.endpoint.capacity()['retired_generation'],0)

    def test_retirement_racing_next_prepare_never_discards_its_reservation(self):
        f=self.f;state,_=self.cycle();endpoint=rpc.SyntheticWitnessEndpoint(f.w,**f.options());_,client=f.serve(endpoint)
        barrier=threading.Barrier(2);results=[]
        def retire():
            try:barrier.wait(3);results.append(client.retire(state,f.digest,generation=1))
            except Exception as error:results.append(error)
        def prepare():
            try:barrier.wait(3);results.append(f.client.prepare(state,f.digest,request_id='3'*32,expected_generation=1))
            except Exception as error:results.append(error)
        threads=[threading.Thread(target=retire),threading.Thread(target=prepare)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(6)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertTrue(all(type(value) is dict or isinstance(value,Conflict) for value in results),results)
        head=f.client.observe();self.assertEqual((head['generation'],head['reservation_id']),(2,'3'*32))
        with f.w._db() as db:self.assertEqual(db.execute('SELECT count(*) FROM rpc_receipts WHERE generation=2').fetchone()[0],1)

    def test_more_than_original_receipt_budget_remains_bounded_under_repeated_retirement(self):
        f=self.f;state=f.initial
        with patch.object(rpc,'MAX_RECEIPTS',2):
            for generation in range(520):
                state,_=self.cycle(state,generation)
                f.client.retire(state,f.digest,generation=generation+1)
            counters=f.endpoint.capacity()
            self.assertEqual(counters['retired_generation'],520);self.assertEqual(counters['receipts'],0)
            self.assertLessEqual(counters['database_bytes'],counters['database_limit_bytes'])

    def test_process_death_before_and_after_retirement_commit(self):
        f=self.f;state,_=self.cycle()
        program=r'''
from contextlib import contextmanager
import json,os,sys
p=json.load(sys.stdin);sys.path.insert(0,p['root'])
from brain.memory_custody import SyntheticWitness
from brain.memory_witness_service import SyntheticWitnessEndpoint
w=SyntheticWitness(p['path'],synthetic_only=True)
e=SyntheticWitnessEndpoint(w,service='a'*32,client='b'*32,lineage=p['lineage'],key=bytes.fromhex(p['key']),synthetic_only=True,clock=lambda:p['now'])
original=w._db
@contextmanager
def die():
    with original() as db:
        yield db
        if p['before']:os._exit(17)
    os._exit(18)
w._db=die;e.exchange(p['raw'].encode())
'''
        for before in (True,False):
            raw=f.raw(dict(op='retire',state=asdict(state),keys_digest=f.digest,generation=1))
            data=dict(root=str(Path(__file__).resolve().parent),path=str(f.w.path),lineage=f.lineage,
                      key=f.key.hex(),now=f.now,raw=raw.decode(),before=before)
            run=subprocess.run([sys.executable,'-I','-B','-c',program],input=json.dumps(data),capture_output=True,text=True,
                               timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,17 if before else 18,'Synthetic retirement child failed; raw output withheld.')
            counters=f.endpoint.capacity();self.assertEqual(counters['retired_generation'],0 if before else 1)
            self.assertEqual(counters['receipts'],2 if before else 0)
        self.assertEqual(f.client.retire(state,f.digest,generation=1)['retired_generation'],1)


@unittest.skipIf(network.cipher is None,'Use the isolated receipt-retirement runner.')
class RetirementAuthorityChecks(unittest.TestCase):
    def setUp(self):
        self.f=network.NetworkAuthorityChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups);self.f.setUp();self.f.endpoint.enable_retirement(approved=True)

    def test_confirmed_authority_retirement_reopens_full_capacity_without_changing_memory(self):
        f=self.f
        with patch.object(rpc,'MAX_RECEIPTS',2):
            saved=f.call(f.f.packet());state=f.local();grant=f.f.grant
            with self.assertRaises(PermissionError):f.a.retire_receipts(f.lineage)
            reply=f.a.retire_receipts(f.lineage,approved=True)
            self.assertEqual(reply['retired_generation'],1);self.assertNotIn('grant',reply);self.assertNotIn('result',reply)
            self.assertEqual(f.local(),state);self.assertEqual(f.f.grant,grant)
            self.assertEqual(f.endpoint.capacity()['receipts'],0)
            self.assertEqual(f.call(dict(op='get',project='alpha',id=saved['id']))['record']['id'],saved['id'])

    def test_pending_source_or_lost_confirmation_cannot_discard_its_finish_receipt(self):
        f=self.f;original=f.client.finish
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic finish confirmation lost')
        with patch.object(f.client,'finish',side_effect=lost):
            with self.assertRaises(OSError):f.call(f.f.packet())
        with self.assertRaises(Conflict):f.a.retire_receipts(f.lineage,approved=True)
        self.assertEqual(f.endpoint.capacity()['receipts'],2);self.assertEqual(f.endpoint.capacity()['retired_generation'],0)
        f.a=f.open();f.reconcile();f.a.retire_receipts(f.lineage,approved=True)
        self.assertEqual(f.endpoint.capacity()['receipts'],0)

    def test_lost_retirement_reply_or_local_commit_failure_is_safe_to_retry(self):
        f=self.f;f.call(f.f.packet());original=f.client.retire
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic retirement confirmation lost')
        with patch.object(f.client,'retire',side_effect=lost):
            with self.assertRaises(OSError):f.a.retire_receipts(f.lineage,approved=True)
        f.a=f.open();self.assertEqual(f.a.retire_receipts(f.lineage,approved=True)['retired_generation'],1)
        original_db=f.a._repository._db
        @contextmanager
        def failed(*args,**kwargs):
            with original_db(*args,**kwargs) as db:
                yield db
                raise sqlite3.OperationalError('Synthetic source confirmation failure')
        with patch.object(f.a._repository,'_db',failed):
            with self.assertRaises(sqlite3.OperationalError):f.a.retire_receipts(f.lineage,approved=True)
        self.assertEqual(f.a.retire_receipts(f.lineage,approved=True)['retired_generation'],1)

    def test_rolled_back_pending_catalogue_cannot_recover_from_a_retired_receipt(self):
        f=self.f;original=f.client.finish
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic finish reply lost')
        with patch.object(f.client,'finish',side_effect=lost):
            with self.assertRaises(OSError):f.call(f.f.packet())
        old=f.f.home/'pending-catalog.sqlite';f.copy_catalog(old)
        f.reconcile();f.a.retire_receipts(f.lineage,approved=True)
        shutil.copyfile(old,f.a._repository.catalog);f.a=f.open()
        with self.assertRaises(Conflict):f.reconcile()
        self.assertEqual(f.endpoint.capacity()['retired_generation'],1)


if __name__=='__main__':unittest.main()
