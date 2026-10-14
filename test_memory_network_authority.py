"""Disposable encrypted fixtures and real localhost HTTP; no real identities or hosts."""
from contextlib import closing, contextmanager
from dataclasses import asdict
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

from brain.memory_authority import SyntheticAuthority
from brain.memory_custody import SyntheticWitness, WitnessState
from brain.memory_network_authority import SyntheticNetworkAuthority
from brain.memory_prototype import Conflict
from brain.memory_recovery import SyntheticRecovery
from brain.memory_witness_service import SyntheticWitnessClient, SyntheticWitnessEndpoint, loopback_server

try:from sqlcipher3 import dbapi2 as cipher
except ImportError:cipher = None


@unittest.skipIf(cipher is None,'Use the isolated network authority runner.')
class NetworkAuthorityChecks(unittest.TestCase):
    def setUp(self):
        import test_qualification as portable
        self.f = portable.StorageChecks(methodName='runTest');self.addCleanup(self.f.doCleanups);self.f.setUp()
        self.rkey = SyntheticRecovery.new_key()
        self.f.recovery = SyntheticRecovery(self.rkey,synthetic_only=True,clock=lambda:self.f.now)
        self.f.authority();self.bare = self.f.a;self.path = self.bare._repository.path
        self.lineage = self.f.anchor.lineage;self.digest = 'd'*64;self.protocol_key = os.urandom(32)
        self.initial = WitnessState(self.f.anchor,self.f.grant.epoch)
        self.w = SyntheticWitness.create(self.f.home/'witness.sqlite',synthetic_only=True,approved=True)
        self.w.register(self.initial,self.digest,approved=True)
        self.endpoint = SyntheticWitnessEndpoint.enable(self.w,service='a'*32,client='b'*32,lineage=self.lineage,
            key=self.protocol_key,synthetic_only=True,approved=True,clock=lambda:self.f.now)
        self.server = loopback_server(self.endpoint,synthetic_only=True)
        self.thread = threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True)
        self.thread.start();self.addCleanup(self.close_server)
        self.client = self.new_client();self.a = self.open()
        self.a.bind_witness(self.lineage,self.digest,approved=True)

    def close_server(self):
        self.server.shutdown();self.thread.join(3);self.server.server_close()
        self.assertFalse(self.thread.is_alive())

    def new_client(self, **kwargs):
        values = dict(service='a'*32,client='b'*32,lineage=self.lineage,key=self.protocol_key,
                      synthetic_only=True,clock=lambda:self.f.now);values.update(kwargs)
        return SyntheticWitnessClient(self.server.server_port,**values)

    def open(self, **kwargs):
        values = dict(client=self.client,recovery=self.f.recovery,storage_key=self.f.key,
                      synthetic_only=True,clock=lambda:self.f.now);values.update(kwargs)
        return SyntheticNetworkAuthority(self.path,**values)

    def journal(self):
        with closing(sqlite3.connect(self.a._repository.catalog)) as db:
            db.row_factory = sqlite3.Row
            return dict(db.execute('SELECT * FROM network_links').fetchone())

    def local(self):
        with self.a._repository._db() as db:return self.a._witness_state(db,self.lineage)

    def call(self, packet, **kwargs):
        values = dict(expected_anchor=self.f.anchor,approved=True);values.update(kwargs)
        reply = self.a.handle(self.f.grant,self.f.turn(),packet,**values)
        self.f.anchor = reply['anchor'];self.assertTrue(reply['witness_confirmed'])
        return reply['result']

    def reconcile(self):return self.a.reconcile_witness(self.lineage,approved=True)

    def assert_current(self):
        row = self.journal();head = self.client.head()
        self.assertEqual(row['phase'],'idle');self.assertIsNone(head['reservation_id'])
        self.assertEqual((head['state'],head['keys_digest'],head['generation']),(self.local(),self.digest,row['generation']))
        self.assertTrue(self.a.head(self.lineage)['witness_confirmed'])

    def assert_blocked(self):
        with self.assertRaises(Conflict):self.a.head(self.lineage)
        with self.assertRaises(Conflict):self.call(self.f.packet('blocked'))
        with self.assertRaises(Conflict):self.a.acquire(self.lineage,'c'*32,expected_epoch=self.f.grant.epoch,approved=True)
        destination = self.f.home/'blocked.sqlite'
        with self.assertRaises(Conflict):self.a.restore(self.lineage,destination,expected_anchor=self.f.anchor,approved=True)
        with self.assertRaises(Conflict):
            self.a.activate_restored(self.lineage,destination,self.f.turn(),'c'*32,expected_anchor=self.f.anchor,
                                     expected_epoch=self.f.grant.epoch,approved=True)
        self.assertFalse(destination.exists())

    def test_explicit_cutover_preserves_local_mode_and_pins_client(self):
        with self.assertRaises(PermissionError):self.open(synthetic_only=False)
        with self.assertRaises(ValueError):self.open(client=object())
        for approval in (False,1,None):
            with self.assertRaises(PermissionError):self.a.bind_witness(self.lineage,self.digest,approved=approval)
        with self.assertRaises(Conflict):self.a.bind_witness(self.lineage,self.digest,approved=True)
        with self.assertRaises(ValueError):self.bare.head(self.lineage)
        for changed in (dict(key=os.urandom(32)),dict(service='c'*32),dict(client='c'*32),dict(lineage='c'*32)):
            with self.assertRaises(ValueError):self.open(client=self.new_client(**changed))
        with self.assertRaises(ValueError):
            SyntheticNetworkAuthority(self.f.home/'missing',client=self.client,recovery=self.f.recovery,
                                      storage_key=self.f.key,synthetic_only=True)
        self.assertFalse((self.f.home/'missing').exists());self.assert_current()

    def test_save_correct_forget_expiry_and_secret_free_metadata(self):
        saved = self.call(self.f.packet('தமிழ்'))
        corrected = self.call(dict(op='correct',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],
                                   expected_revision=1,value={'text':'SYNTHETIC_NETWORK_CORRECTION'}))
        self.assertEqual(corrected['revision'],2)
        self.call(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],expected_revision=2))
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=saved['id']))['record'])
        timed = self.f.packet('timed');timed['retention']={'mode':'until','expires_at':self.f.now+1}
        record = self.call(timed);self.f.now += 2
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=record['id']))['record'])
        for path in (self.a._repository.catalog,self.w.path):
            for secret in (self.f.key,self.rkey,self.protocol_key,self.f.grant.token,b'SYNTHETIC_NETWORK_CORRECTION'):
                self.assertNotIn(secret,path.read_bytes())
        self.assert_current()

    def test_restore_damaged_live_file_and_verified_reactivation(self):
        saved = self.call(self.f.packet())
        self.call(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],expected_revision=1))
        with self.a._repository._db() as db:
            row = db.execute('SELECT object_id FROM latest WHERE lineage=?',(self.lineage,)).fetchone()
        (self.path/'objects'/row[0]/'live.sqlite').write_bytes(b'SYNTHETIC_DAMAGE')
        destination = self.f.home/'quarantine.sqlite';old = self.f.grant
        restored = self.a.restore(self.lineage,destination,expected_anchor=self.f.anchor,approved=True)
        self.assertTrue(restored['witness_confirmed']);self.assert_current()
        with self.assertRaises(PermissionError):
            self.a.activate_restored(self.lineage,destination,self.f.turn(verified=False),'c'*32,
                expected_anchor=self.f.anchor,expected_epoch=restored['writer_epoch'],approved=True)
        activated = self.a.activate_restored(self.lineage,destination,self.f.turn(),'c'*32,
            expected_anchor=self.f.anchor,expected_epoch=restored['writer_epoch'],approved=True)
        self.f.anchor,self.f.grant = activated['anchor'],activated['grant']
        self.assertEqual((activated['active_bindings'],activated['resumed_jobs']),(1,0))
        with self.assertRaises(PermissionError):
            self.a.handle(old,self.f.turn(),self.f.packet('old'),expected_anchor=self.f.anchor,approved=True)
        self.reconcile()
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=saved['id']))['record']);self.assert_current()

    def test_intent_is_durable_before_prepare_and_unavailable_prepare_resolves_unchanged(self):
        def unavailable(*args,**kwargs):
            self.assertEqual(self.journal()['phase'],'intent')
            self.assertEqual(self.journal()['operation_id'],kwargs['request_id'])
            raise OSError('Synthetic unavailable prepare')
        with patch.object(self.client,'prepare',side_effect=unavailable):
            with self.assertRaises(OSError):self.call(self.f.packet())
        self.assertIsNone(self.client.head()['reservation_id']);self.assertEqual(self.local(),self.initial)
        self.a = self.open();self.assert_blocked();self.reconcile();self.assert_current()

    def test_lost_prepare_reply_recovers_same_reservation_and_blocks_late_resume(self):
        original = self.client.prepare
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic lost prepare reply')
        with patch.object(self.client,'prepare',side_effect=lost):
            with self.assertRaises(OSError):self.call(self.f.packet())
        row = self.journal();self.assertEqual(row['phase'],'intent')
        self.assertEqual(self.client.head()['reservation_id'],row['operation_id'])
        self.a = self.open();self.assert_blocked()
        with self.assertRaises(PermissionError):self.a.reconcile_witness(self.lineage)
        self.reconcile()
        with self.assertRaises(Conflict):self.a._reserve(self.lineage,row['operation_id'],lambda:False)
        self.assertEqual(self.local(),self.initial);self.assert_current()

    def test_failed_publication_rolls_back_source_before_unchanged_finish(self):
        original = self.a._publish
        def failed(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic publication failure')
        with patch.object(self.a,'_publish',side_effect=failed):
            with self.assertRaises(OSError):self.call(self.f.packet())
        self.assertEqual(self.local(),self.initial);self.assertEqual(self.journal()['phase'],'prepared')
        self.assert_blocked();self.reconcile();self.assert_current()

    def test_source_commit_failure_never_finishes_a_changed_state(self):
        original = self.a._repository._db
        @contextmanager
        def failed(*args,**kwargs):
            with original(*args,**kwargs) as db:
                yield db
                row = db.execute('SELECT phase FROM network_links').fetchone()
                if row and row[0]=='committed':raise sqlite3.OperationalError('Synthetic source commit failure')
        with patch.object(self.a._repository,'_db',failed):
            with self.assertRaises(sqlite3.OperationalError):self.call(self.f.packet())
        self.assertEqual(self.local(),self.initial);self.assertEqual(self.journal()['phase'],'prepared')
        self.assertEqual(self.client.head()['state'],self.initial);self.reconcile();self.assert_current()

    def test_lost_finish_reply_reconciles_committed_source_and_retries_only_receipt(self):
        original = self.client.finish;packet = self.f.packet();old = self.f.anchor
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic lost finish reply')
        with patch.object(self.client,'finish',side_effect=lost):
            with self.assertRaises(OSError):self.call(packet)
        committed = self.local();self.assertGreater(committed.anchor.sequence,old.sequence)
        self.assertEqual(self.client.head()['state'],committed);self.assertEqual(self.journal()['phase'],'committed')
        self.a = self.open();self.assert_blocked();reply = self.reconcile()
        self.assertNotIn('result',reply);self.assertNotIn('grant',reply)
        first = self.call(packet,expected_anchor=old)
        self.assertEqual(self.call(packet,expected_anchor=old),first);self.assertEqual(self.local(),committed);self.assert_current()

    def test_confirmation_commit_failure_retries_exact_finish_receipt(self):
        original = self.a._repository._db
        @contextmanager
        def failed(*args,**kwargs):
            with original(*args,**kwargs) as db:
                old = db.execute('SELECT phase FROM network_links').fetchone()[0]
                yield db
                new = db.execute('SELECT phase FROM network_links').fetchone()[0]
                if old=='committed' and new=='idle':raise sqlite3.OperationalError('Synthetic confirmation commit failure')
        with patch.object(self.a._repository,'_db',failed):
            with self.assertRaises(sqlite3.OperationalError):self.call(self.f.packet())
        self.assertEqual(self.journal()['phase'],'committed');self.assertIsNone(self.client.head()['reservation_id'])
        self.a = self.open();self.reconcile();self.assert_current()

    def test_reconciliation_loss_after_unchanged_finish_without_saved_generation(self):
        with patch.object(self.client,'prepare',side_effect=OSError('Synthetic unavailable prepare')):
            with self.assertRaises(OSError):self.call(self.f.packet())
        original = self.client.finish
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('Synthetic reconciliation reply loss')
        with patch.object(self.client,'finish',side_effect=lost):
            with self.assertRaises(OSError):self.reconcile()
        self.assertEqual(self.journal()['phase'],'intent');self.assertIsNone(self.journal()['reserved_generation'])
        self.assertIsNone(self.client.head()['reservation_id']);self.a = self.open();self.reconcile();self.assert_current()

    def test_lost_takeover_grant_is_not_reconstructed(self):
        old = self.f.grant
        with patch.object(self.client,'finish',side_effect=OSError('Synthetic finish unavailable')):
            with self.assertRaises(OSError):self.a.acquire(self.lineage,'c'*32,expected_epoch=old.epoch,approved=True)
        reply = self.reconcile();self.assertNotIn('grant',reply);self.assertEqual(reply['writer_epoch'],old.epoch+1)
        self.f.grant = self.a.acquire(self.lineage,'e'*32,expected_epoch=reply['writer_epoch'],approved=True)
        with self.assertRaises(PermissionError):
            self.a.handle(old,self.f.turn(),self.f.packet(),expected_anchor=self.f.anchor,approved=True)
        self.reconcile();self.assert_current()

    def test_interrupted_restore_and_activation_reconcile_without_replaying_grants(self):
        saved = self.call(self.f.packet())
        self.call(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=saved['id'],expected_revision=1))
        destination = self.f.home/'quarantine.sqlite'
        with patch.object(self.client,'finish',side_effect=OSError('Synthetic restore finish unavailable')):
            with self.assertRaises(OSError):self.a.restore(self.lineage,destination,expected_anchor=self.f.anchor,approved=True)
        self.assert_blocked();restored = self.reconcile()
        self.assertTrue(self.a.head(self.lineage)['recovery_pending'])
        with patch.object(self.client,'finish',side_effect=OSError('Synthetic activation finish unavailable')):
            with self.assertRaises(OSError):
                self.a.activate_restored(self.lineage,destination,self.f.turn(),'c'*32,expected_anchor=self.f.anchor,
                                         expected_epoch=restored['writer_epoch'],approved=True)
        self.assert_blocked();activated = self.reconcile();self.assertNotIn('grant',activated)
        self.f.anchor = activated['anchor'];self.assertFalse(self.a.head(self.lineage)['recovery_pending'])
        self.f.grant = self.a.acquire(self.lineage,'e'*32,expected_epoch=activated['writer_epoch'],approved=True)
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=saved['id']))['record']);self.assert_current()

    def copy_catalog(self, destination):
        with closing(sqlite3.connect(self.a._repository.catalog)) as source,closing(sqlite3.connect(destination)) as target:
            source.backup(target)

    def test_source_rollback_after_changed_state_is_rejected(self):
        backup = self.f.home/'old.sqlite';self.copy_catalog(backup)
        self.call(self.f.packet());head = self.client.head()
        shutil.copyfile(backup,self.a._repository.catalog);self.a = self.open()
        with self.assertRaises(Conflict):self.a.head(self.lineage)
        with self.assertRaises(Conflict):self.reconcile()
        self.assertEqual(self.client.head(),head)

    def test_source_rollback_after_unchanged_read_is_rejected_by_protocol_generation(self):
        backup = self.f.home/'old.sqlite';self.copy_catalog(backup)
        self.a.head(self.lineage);self.assertEqual(self.local(),self.initial)
        shutil.copyfile(backup,self.a._repository.catalog);self.a = self.open()
        with self.assertRaises(Conflict):self.a.head(self.lineage)
        with self.assertRaises(Conflict):self.reconcile()

    def test_two_copied_catalogues_cannot_both_write_or_close_each_others_reservation(self):
        clone = self.f.home/'clone';shutil.copytree(self.path,clone)
        other = SyntheticNetworkAuthority(clone,client=self.new_client(),recovery=self.f.recovery,
            storage_key=self.f.key,synthetic_only=True,clock=lambda:self.f.now)
        barrier = threading.Barrier(2);results = [];original = SyntheticWitnessClient.prepare
        def prepare(client,*args,**kwargs):barrier.wait(3);return original(client,*args,**kwargs)
        def write(authority):
            try:
                reply = authority.handle(self.f.grant,self.f.turn(),self.f.packet(os.urandom(8).hex()),
                    expected_anchor=self.f.anchor,approved=True)
                results.append((authority,reply))
            except Exception as error:results.append((authority,error))
        with patch.object(SyntheticWitnessClient,'prepare',prepare):
            threads = [threading.Thread(target=write,args=(item,)) for item in (self.a,other)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(sum(type(value) is dict for _,value in results),1)
        self.assertEqual(sum(isinstance(value,Conflict) for _,value in results),1)
        for authority,value in results:
            if isinstance(value,Conflict):
                with self.assertRaises(Conflict):authority.reconcile_witness(self.lineage,approved=True)

    def test_generation_cas_rejects_a_stale_prepare_without_stranding_a_reservation(self):
        clone = self.f.home/'clone';shutil.copytree(self.path,clone)
        other = SyntheticNetworkAuthority(clone,client=self.new_client(),recovery=self.f.recovery,
            storage_key=self.f.key,synthetic_only=True,clock=lambda:self.f.now)
        original = self.a._reserve
        def advanced(*args,**kwargs):
            other.head(self.lineage)  # Another copy completes an unchanged operation after our intent commits.
            return original(*args,**kwargs)
        with patch.object(self.a,'_reserve',side_effect=advanced):
            with self.assertRaises(Conflict):self.a.head(self.lineage)
        self.assertIsNone(self.client.head()['reservation_id']);self.assertEqual(self.local(),self.initial)
        with self.assertRaises(Conflict):self.reconcile()
        self.assertTrue(other.head(self.lineage)['witness_confirmed'])
        with self.assertRaises(ValueError):
            self.client.prepare(self.initial,self.digest,request_id=os.urandom(16).hex(),expected_generation=True)

    def test_reconciliation_fences_a_paused_local_writer_before_another_write(self):
        entered,release = threading.Event(),threading.Event();results = [];original = self.a._reserve
        other = self.open(client=self.new_client())
        def paused(*args,**kwargs):
            original(*args,**kwargs);entered.set()
            if not release.wait(5):raise RuntimeError('Synthetic barrier timed out')
        def write():
            try:results.append(self.call(self.f.packet('late')))
            except Exception as error:results.append(error)
        with patch.object(self.a,'_reserve',side_effect=paused):
            thread = threading.Thread(target=write);thread.start()
            try:
                self.assertTrue(entered.wait(3));other.reconcile_witness(self.lineage,approved=True)
                reply = other.handle(self.f.grant,self.f.turn(),self.f.packet('winner'),expected_anchor=self.f.anchor,approved=True)
                self.f.anchor = reply['anchor']
            finally:release.set();thread.join(8)
        self.assertFalse(thread.is_alive());self.assertEqual(len(results),1);self.assertIsInstance(results[0],Conflict)
        self.assert_current()

    def test_cancellation_and_identity_revocation_during_finish_withhold_reply(self):
        original = self.client.finish
        for mode in ('cancel','identity'):
            turn = self.f.turn();cancelled = threading.Event();packet = self.f.packet(mode)
            def revoke(*args,**kwargs):
                result = original(*args,**kwargs)
                (cancelled if mode=='cancel' else turn._cancelled).set();return result
            with patch.object(self.client,'finish',side_effect=revoke):
                with self.assertRaises(InterruptedError):
                    self.a.handle(self.f.grant,turn,packet,expected_anchor=self.f.anchor,approved=True,cancelled=cancelled.is_set)
            self.reconcile();self.call(packet);self.assert_current()

    def test_corrupt_journal_missing_binding_and_changed_custody_fail_closed(self):
        backup = self.f.home/'safe.sqlite';self.copy_catalog(backup);head = self.client.head()
        for mutation in ("UPDATE network_links SET next_state='{}'", "UPDATE network_links SET keys_digest='"+'f'*64+"'",
                         "UPDATE network_links SET phase='intent'",'DROP TABLE network_links'):
            with self.a._repository._db() as db:db.execute(mutation)
            with self.assertRaises((ValueError,sqlite3.DatabaseError,Conflict)):self.a.head(self.lineage)
            with self.assertRaises((ValueError,sqlite3.DatabaseError,Conflict)):self.reconcile()
            self.assertEqual(self.client.head(),head)
            shutil.copyfile(backup,self.a._repository.catalog)
        self.a = self.open();self.assert_current()

    def test_missing_current_bundle_cannot_finish_or_fall_back(self):
        with patch.object(self.client,'finish',side_effect=OSError('Synthetic finish unavailable')):
            with self.assertRaises(OSError):self.call(self.f.packet())
        with self.a._repository._db() as db:row = db.execute('SELECT object_id FROM latest').fetchone()
        (self.path/'objects'/row[0]/'backup.enc').unlink()
        with self.assertRaises((ValueError,OSError)):self.reconcile()
        self.assertIsNotNone(self.client.head()['reservation_id'])

    def test_semantically_wrong_prepare_and_finish_replies_do_not_acknowledge(self):
        original = self.client.prepare
        def wrong(*args,**kwargs):return dict(original(*args,**kwargs),generation=999)
        with patch.object(self.client,'prepare',side_effect=wrong):
            with self.assertRaises(Conflict):self.call(self.f.packet('wrong-prepare'))
        self.assertEqual(self.local(),self.initial);self.reconcile()
        def wrong_finish(*args,**kwargs):return dict(self.client.head(),reservation_id=None,generation=999)
        with patch.object(self.client,'finish',side_effect=wrong_finish):
            with self.assertRaises(Conflict):self.call(self.f.packet('wrong-finish'))
        self.assert_blocked();self.reconcile();self.assert_current()

    def test_process_death_at_intent_reservation_source_and_confirmation_boundaries(self):
        program = r'''
from contextlib import contextmanager
import json,os,sys,threading,time
p=json.load(sys.stdin);sys.path[:0]=p['imports']
from brain.memory_network_authority import SyntheticNetworkAuthority
from brain.memory_authority import WriterGrant
from brain.memory_recovery import SyntheticRecovery,CheckpointAnchor
from brain.memory_witness_service import SyntheticWitnessClient
from brain.conversation import Context,PublicTurn
c=SyntheticWitnessClient(p['port'],service='a'*32,client='b'*32,lineage=p['lineage'],key=bytes.fromhex(p['protocol_key']),
    synthetic_only=True,clock=lambda:p['now'])
a=SyntheticNetworkAuthority(p['path'],client=c,storage_key=bytes.fromhex(p['key']),
    recovery=SyntheticRecovery(p['recovery'].encode(),synthetic_only=True,clock=lambda:p['now']),synthetic_only=True,clock=lambda:p['now'])
mode=p['mode']
if mode in ('intent','reserved'):
    original=a._reserve
    def die(*args,**kwargs):
        if mode=='reserved':original(*args,**kwargs)
        os._exit(17 if mode=='intent' else 18)
    a._reserve=die
elif mode=='before_source_commit':
    original=a._repository._db
    @contextmanager
    def die(*args,**kwargs):
        with original(*args,**kwargs) as db:
            yield db
            if db.execute('SELECT phase FROM network_links').fetchone()[0]=='committed':os._exit(19)
    a._repository._db=die
elif mode=='after_source_commit':a._finish=lambda *args:os._exit(20)
else:
    original=c.finish
    def die(*args,**kwargs):original(*args,**kwargs);os._exit(21)
    c.finish=die
g=p['grant'];g['token']=bytes.fromhex(g['token']);grant=WriterGrant(**g)
context=Context('1'*64,'phone','2'*64,'1'*64,p['now']+300,True)
turn=PublicTurn('3'*32,'SYNTHETIC_CRASH',context,time.monotonic()+30,lambda:context,lambda:p['now'],threading.Event())
a.handle(grant,turn,p['packet'],expected_anchor=CheckpointAnchor(**p['anchor']),approved=True)
'''
        for mode,code in (('intent',17),('reserved',18),('before_source_commit',19),('after_source_commit',20),('after_remote_commit',21)):
            before = self.local();packet = self.f.packet(mode);grant = asdict(self.f.grant);grant['token']=grant['token'].hex()
            data = dict(imports=[str(Path(__file__).resolve().parent),str(Path(cipher.__file__).resolve().parents[1])],
                path=str(self.path),lineage=self.lineage,key=self.f.key.hex(),recovery=self.rkey.decode(),
                protocol_key=self.protocol_key.hex(),port=self.server.server_port,now=self.f.now,
                grant=grant,packet=packet,anchor=asdict(self.f.anchor),mode=mode)
            run = subprocess.run([sys.executable,'-I','-B','-c',program],input=json.dumps(data),capture_output=True,text=True,
                                 timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,code,'Synthetic crash child failed; raw output withheld.')
            self.a = self.open();self.assert_blocked()
            if code<=19:self.assertEqual(self.local(),before)
            else:self.assertGreater(self.local().anchor.sequence,before.anchor.sequence)
            self.reconcile();first = self.call(packet);current = self.local()
            self.assertEqual(self.call(packet),first);self.assertEqual(self.local(),current);self.assert_current()


if __name__=='__main__':unittest.main()
