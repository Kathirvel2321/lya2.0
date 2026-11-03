"""Generated fake keys, temporary source/publication stores, no network or account."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from brain.memory_authority import SyntheticAuthority
from brain.memory_custody import WitnessState
from brain.memory_prototype import Conflict,SyntheticMemory
from brain.memory_recovery import CheckpointAnchor
from brain.memory_recovery_latest import RecoveryHead,SyntheticRecoveryLatest
from brain.memory_recovery_trust import seal_trust
from brain.memory_publication_authority import SyntheticPublicationAuthority
from test_memory_recovery_pack import RecoveryPackChecks
from test_memory_recovery_host import RecoveryHostChecks

EVIDENCE={}
CRASH=r'''
import json,os,sys,threading,time
from contextlib import contextmanager
from unittest.mock import patch
p=json.load(sys.stdin);sys.path[:0]=p['imports']
from brain.memory_publication_authority import SyntheticPublicationAuthority
from brain.memory_authority import WriterGrant
from brain.memory_recovery_latest import SyntheticRecoveryLatest
from brain.memory_recovery import SyntheticRecovery,CheckpointAnchor
from brain.conversation import Context,PublicTurn
latest=SyntheticRecoveryLatest(p['latest'],synthetic_only=True)
a=SyntheticPublicationAuthority(p['source'],latest=latest,publications=p['publications'],capsule=p['capsule'],
    unlock_key=p['unlock'].encode(),recovery=SyntheticRecovery(p['recovery'].encode(),synthetic_only=True,clock=lambda:p['now']),
    storage_key=bytes.fromhex(p['storage']),synthetic_only=True,clock=lambda:p['now'])
original_source=a._repository._db;original_latest=latest._db;source_calls=[0];latest_calls=[0]
@contextmanager
def source_db():
    source_calls[0]+=1;n=source_calls[0]
    with original_source() as db:
        yield db
        if p['mode']=='source_before' and n==1:os._exit(71)
    if (p['mode']=='source_after' and n==1) or (p['mode']=='journal_after' and n==2):os._exit(72)
@contextmanager
def latest_db():
    latest_calls[0]+=1;n=latest_calls[0]
    with original_latest() as db:yield db
    if (p['mode']=='reserve_after' and n==1) or (p['mode']=='confirm_after' and n==2):os._exit(72)
context=Context('1'*64,'phone','2'*64,'1'*64,p['now']+300,True)
turn=PublicTurn('3'*32,'SYNTHETIC_PUBLICATION',context,time.monotonic()+30,lambda:context,lambda:p['now'],threading.Event())
g=p['grant'];grant=WriterGrant(g['lineage'],g['epoch'],g['writer'],bytes.fromhex(g['token']))
with patch.object(a._repository,'_db',source_db),patch.object(latest,'_db',latest_db):
    a.handle(grant,turn,p['request'],expected_anchor=CheckpointAnchor(**p['anchor']),approved=True)
raise AssertionError('Expected synchronized fake process exit')
'''


class PublicationAuthorityChecks(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='pa-');self.addCleanup(temp.cleanup);self.home=Path(temp.name)
        self.number=0

    def make(self,*,bind=True):
        self.number+=1;home=self.home/str(self.number);home.mkdir()
        f=RecoveryPackChecks(methodName='runTest');self.addCleanup(f.doCleanups);f.setUp()
        pins,_=f.pins();initial=home/'initial-pack';f.stage(initial);record=home/'initial-trust.enc'
        digest=seal_trust(record,pins,f.unlock,synthetic_only=True,approved=True)
        latest=SyntheticRecoveryLatest.create(home/'latest.sqlite',synthetic_only=True,approved=True)
        head=RecoveryHead(pins,digest);latest.begin(None,head,approved=True);latest.finish(head,initial,record,f.unlock,approved=True)
        publications=home/'publications';publications.mkdir()
        a=SyntheticPublicationAuthority(f.f.a._repository.path,latest=latest,publications=publications,capsule=f.capsule,
            unlock_key=f.unlock,recovery=f.f.recovery,storage_key=f.f.key,synthetic_only=True,clock=lambda:f.f.now)
        if bind:a.bind_publication(pins.state.anchor.lineage,record,approved=True)
        f.f.a=a
        return f,a,latest,initial,record

    def call(self,f,request):return f.f.a.handle(f.f.grant,f.f.turn(),request,expected_anchor=f.f.anchor,approved=True)

    def files(self,a,latest,lineage):
        head=latest.head(lineage)
        matches=[path for path in a._publications.rglob('trust.enc') if hashlib.sha256(path.read_bytes()).hexdigest()==head.trust_digest]
        self.assertEqual(len(matches),1);return matches[0].parent/'pack',matches[0]

    def host(self):
        host=RecoveryHostChecks(methodName='runTest');self.addCleanup(host.doCleanups);host.setUp();return host

    def test_successful_mutations_and_exact_retry_are_published_before_reply(self):
        f,a,latest,_,_=self.make();request=f.f.packet('acknowledged')
        first=self.call(f,request);second=self.call(f,request)
        self.assertEqual(first,second);self.assertEqual(latest.head(f.f.anchor.lineage).pins.state.anchor,first['anchor'])
        f.f.anchor=first['anchor'];f.latest()
        self.assertEqual(a.head(f.f.anchor.lineage)['anchor'],latest.head(f.f.anchor.lineage).pins.state.anchor)
        with a._repository._db() as db:
            raw=db.execute('SELECT confirmed_head,operation_id,next_pins FROM publication_links').fetchone()
            self.assertIsNone(raw['operation_id']);self.assertIsNone(raw['next_pins'])
            for secret in (f.unlock.decode(),f.key.decode(),f.f.key.hex(),f.f.grant.token.hex()):self.assertNotIn(secret,raw['confirmed_head'])

    def test_rollback_reservation_blocks_even_old_code_archive_then_reconciles(self):
        f,a,latest,old_pack,old_trust=self.make();anchor=f.f.anchor;request=f.f.packet('rolled-back')
        with patch.object(a,'_publish',side_effect=OSError('FAKE source failure')),self.assertRaises(OSError):self.call(f,request)
        with self.assertRaises(ValueError):latest.head(anchor.lineage)
        host=self.host();packet=dict(version=1,synthetic_only=True,approved=True,latest_store=str(latest.path),lineage=anchor.lineage,
            pack=str(old_pack),trust=str(old_trust),destination=str(self.home/'refused.sqlite'),unlock=f.unlock.decode(),now=f.f.now)
        run,result=host.child(packet);self.assertEqual(run.returncode,1);self.assertFalse(result['passed'])
        self.assertFalse(Path(packet['destination']).exists())
        status=a.reconcile_publication(anchor.lineage,approved=True)
        self.assertEqual(status['anchor'],anchor);self.assertEqual(latest.head(anchor.lineage).pins.state.anchor,anchor)
        self.assertGreater(self.call(f,request)['anchor'].sequence,anchor.sequence)

    def test_committed_source_waits_for_publication_and_retry_does_not_replay(self):
        f,a,latest,_,_=self.make();anchor=f.f.anchor;request=f.f.packet('committed')
        with patch.object(a,'_stage',side_effect=OSError('FAKE publication unavailable')),self.assertRaises(OSError):self.call(f,request)
        with self.assertRaises(Conflict):a.head(anchor.lineage)
        with self.assertRaises(ValueError):latest.head(anchor.lineage)
        status=a.reconcile_publication(anchor.lineage,approved=True)
        self.assertGreater(status['anchor'].sequence,anchor.sequence)
        self.assertEqual(set(status),{'anchor','writer_epoch','publication_confirmed','synthetic_only'})
        reply=self.call(f,request);self.assertEqual(reply['anchor'],status['anchor'])
        with a._repository._db() as db:
            _,_,memory,*_=a._entry(db,anchor.lineage)
            with memory._db() as source:self.assertEqual(source.execute('SELECT COUNT(*) FROM requests WHERE request_id=?',(request['request_id'],)).fetchone()[0],1)

    def test_writer_grant_is_not_returned_until_publication_and_reconcile_issues_none(self):
        f,a,latest,_,_=self.make();lineage=f.f.anchor.lineage;old=f.f.grant
        with patch.object(a,'_stage',side_effect=OSError('FAKE publication unavailable')),self.assertRaises(OSError):
            a.acquire(lineage,'b'*32,expected_epoch=old.epoch,approved=True)
        status=a.reconcile_publication(lineage,approved=True)
        self.assertEqual(status['writer_epoch'],old.epoch+1);self.assertNotIn('token',status)
        grant=a.acquire(lineage,'c'*32,expected_epoch=status['writer_epoch'],approved=True)
        self.assertEqual(latest.head(lineage).pins.state.writer_epoch,grant.epoch)
        self.assertNotEqual(grant.token,old.token)

    def test_turn_expiring_during_publication_cannot_receive_a_success_reply(self):
        f,a,latest,_,_=self.make();request=f.f.packet('expired-turn');original=a._stage
        def expire(*args,**kwargs):
            result=original(*args,**kwargs);f.f.now+=400;return result
        with patch.object(a,'_stage',side_effect=expire),self.assertRaises(PermissionError):self.call(f,request)
        committed=latest.head(f.f.anchor.lineage).pins.state.anchor
        self.assertGreater(committed.sequence,f.f.anchor.sequence)
        self.assertEqual(self.call(f,request)['anchor'],committed)

    def test_cutover_refuses_legacy_authority_and_missing_custody_without_recreation(self):
        f,a,latest,_,record=self.make()
        with self.assertRaises(ValueError):SyntheticAuthority(a._repository.path,recovery=f.f.recovery,storage_key=f.f.key,synthetic_only=True)
        with self.assertRaises(Conflict):a.bind_publication(f.f.anchor.lineage,record,approved=True)
        with self.assertRaises(PermissionError):a.reconcile_publication(f.f.anchor.lineage,approved=1)
        before=a.head(f.f.anchor.lineage);path=latest.path;saved=path.read_bytes();path.unlink()
        with self.assertRaises(sqlite3.DatabaseError):self.call(f,f.f.packet('missing-custody'))
        self.assertFalse(path.exists());path.write_bytes(saved)
        self.assertEqual(a.head(f.f.anchor.lineage),before)
        f,unbound,latest,_,record=self.make(bind=False)
        with unbound._repository._db() as db:
            db.execute('INSERT INTO latest SELECT ?,sequence,checkpoint_id,sha256,backup_sha256,object_id,key_sha256 FROM latest LIMIT 1',('f'*32,))
        with self.assertRaises(Conflict):unbound.bind_publication(f.f.anchor.lineage,record,approved=True)
        with unbound._repository._db() as db:self.assertEqual(db.execute('SELECT version FROM authority_meta').fetchone()[0],2)

    def test_rolled_back_source_catalogue_cannot_replace_current_latest(self):
        f,a,latest,_,_=self.make();catalog=a._repository.catalog;old=catalog.read_bytes()
        reply=self.call(f,f.f.packet('new-state'));head=latest.head(f.f.anchor.lineage)
        self.assertEqual(head.pins.state.anchor,reply['anchor'])
        current=catalog.read_bytes();catalog.write_bytes(old)
        with self.assertRaises(Conflict):a.reconcile_publication(f.f.anchor.lineage,approved=True)
        self.assertEqual(latest.head(f.f.anchor.lineage),head);catalog.write_bytes(current)

    def test_authority_recovery_revokes_old_writer_only_after_published_epoch(self):
        f,a,latest,_,_=self.make();lineage=f.f.anchor.lineage
        result=a.restore(lineage,self.home/'quarantine.sqlite',expected_anchor=f.f.anchor,approved=True)
        self.assertTrue(result['result']['quarantined']);self.assertEqual(result['result']['resumed_jobs'],0)
        self.assertEqual(latest.head(lineage).pins.state.writer_epoch,f.f.grant.epoch+1)
        with self.assertRaises(PermissionError):self.call(f,f.f.packet('revoked'))
        a.reconcile_publication(lineage,approved=True)
        with self.assertRaises(PermissionError):
            a.activate_restored(lineage,self.home/'quarantine.sqlite',f.f.turn(verified=False),'b'*32,
                expected_anchor=f.f.anchor,expected_epoch=result['writer_epoch'],approved=True)

    def test_acknowledged_correction_forget_and_expiry_survive_source_loss_in_old_archive(self):
        f,a,latest,_,_=self.make();f.latest();lineage=f.f.anchor.lineage;pack,trust=self.files(a,latest,lineage)
        host=self.host();destination=host.home/'recovered.sqlite'
        packet=dict(version=1,synthetic_only=True,approved=True,latest_store=str(latest.path),lineage=lineage,
            pack=str(pack),trust=str(trust),destination=str(destination),unlock=f.unlock.decode(),now=f.f.now)
        lost=f.f.home;f.doCleanups();self.assertFalse(lost.exists())
        run,result=host.child(packet);self.assertEqual(run.returncode,0);self.assertTrue(result['archive_only_project_imports'])
        memory=SyntheticMemory(destination,synthetic_only=True,encryption_key=f.f.key,clock=lambda:f.f.now)
        with memory._db() as db:
            rows={row['id']:dict(row) for row in db.execute('SELECT * FROM memories')}
            self.assertEqual(json.loads(rows[f.kept['id']]['value']),{'text':'SYNTHETIC_PACK_CORRECTION'})
            for mid in (f.forgotten['id'],f.expired['id']):self.assertEqual((rows[mid]['deleted'],rows[mid]['value']),(1,None))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bindings WHERE active=1').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)
        EVIDENCE.update(result,source_lost_after_publication=True,acknowledged_correction_forget_expiry_verified=True)

    def test_process_death_at_reservation_source_confirmation_and_journal_boundaries(self):
        modes=('reserve_after','source_before','source_after','confirm_after','journal_after');root=Path(__file__).resolve().parent
        for mode in modes:
            f,a,latest,_,_=self.make();anchor=f.f.anchor;grant=f.f.grant;request=f.f.packet('crash-'+mode)
            imports=[str(root),str(root/'review/2026-10-13-memory-linux')]
            if sys.platform=='win32':imports.append(str(root/'review/2026-10-12-memory-hardening/.drivers'))
            packet=dict(imports=imports,latest=str(latest.path),source=str(a._repository.path),publications=str(a._publications),
                capsule=str(f.capsule),unlock=f.unlock.decode(),recovery=f.key.decode(),storage=f.f.key.hex(),now=f.f.now,
                grant=dict(lineage=grant.lineage,epoch=grant.epoch,writer=grant.writer,token=grant.token.hex()),anchor=asdict(anchor),request=request,mode=mode)
            run=subprocess.run([sys.executable,'-I','-B','-c',CRASH],input=json.dumps(packet),capture_output=True,text=True,timeout=30,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,71 if mode=='source_before' else 72,'Fake integrated crash boundary failed; raw output withheld.')
            status=a.reconcile_publication(anchor.lineage,approved=True)
            if mode in ('reserve_after','source_before'):self.assertEqual(status['anchor'],anchor)
            else:self.assertGreater(status['anchor'].sequence,anchor.sequence)
            reply=self.call(f,request);self.assertEqual(latest.head(anchor.lineage).pins.state.anchor,reply['anchor'])


if __name__=='__main__':unittest.main()
