"""Pre-existing fake-owner reactivation through the publication transaction only."""
from dataclasses import asdict,replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import patch

from brain.memory_prototype import Conflict,SyntheticMemory
from test_memory_publication_authority import PublicationAuthorityChecks,CRASH


class PublicationReactivationChecks(PublicationAuthorityChecks):
    def prepare(self):
        f,a,latest,_,_=self.make();target=self.home/('q'+str(self.number)+'.sqlite')
        restored=a.restore(f.f.anchor.lineage,target,expected_anchor=f.f.anchor,approved=True)
        return f,a,latest,target,restored

    def activate(self,f,target,recovery,**kwargs):
        values=dict(lineage=f.f.anchor.lineage,restored=target,turn=f.f.turn(),writer='b'*32,
            expected_anchor=f.f.anchor,expected_epoch=recovery['writer_epoch'],approved=True)
        values.update(kwargs);return f.f.a.activate_restored(**values)

    def test_reactivation_success_publishes_one_owner_and_fences_old_writer(self):
        f,a,latest,_,_=self.make();f.latest();target=self.home/'q.sqlite'
        restored=a.restore(f.f.anchor.lineage,target,expected_anchor=f.f.anchor,approved=True)
        quarantine=target.read_bytes();old=f.f.grant;reply=self.activate(f,target,restored)
        self.assertTrue(reply['publication_confirmed']);self.assertFalse(reply['quarantined'])
        self.assertEqual((reply['active_bindings'],reply['resumed_jobs']),(1,0))
        self.assertEqual(latest.head(old.lineage).pins.state.writer_epoch,reply['grant'].epoch)
        self.assertEqual(latest.head(old.lineage).pins.state.anchor,reply['anchor'])
        self.assertEqual(reply['grant'].epoch,old.epoch+2);self.assertNotEqual(reply['grant'].token,old.token)
        with self.assertRaises(PermissionError):self.call(f,f.f.packet('old-grant'))
        a.reconcile_publication(old.lineage,approved=True)
        self.assertEqual(target.read_bytes(),quarantine)
        with a._repository._db() as db:
            _,_,memory,*_=a._entry(db,old.lineage)
            self.assertIsNone(db.execute('SELECT 1 FROM recoveries').fetchone())
            with memory._db() as source:
                self.assertEqual([tuple(row) for row in source.execute('SELECT binding,owner,active FROM bindings')],
                    [('1'*64,f.f.owner,1)])
                self.assertEqual(source.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)
                rows={row['id']:dict(row) for row in source.execute('SELECT * FROM memories')}
                self.assertEqual(json.loads(rows[f.kept['id']]['value']),{'text':'SYNTHETIC_PACK_CORRECTION'})
                for mid in (f.forgotten['id'],f.expired['id']):self.assertEqual((rows[mid]['deleted'],rows[mid]['value']),(1,None))
        f.f.grant=reply['grant'];f.f.anchor=reply['anchor']
        self.assertTrue(self.call(f,f.f.packet('fresh-writer'))['publication_confirmed'])
        pack,trust=self.files(a,latest,old.lineage);host=self.host();destination=host.home/'after-activation.sqlite'
        packet=dict(version=1,synthetic_only=True,approved=True,latest_store=str(latest.path),lineage=old.lineage,
            pack=str(pack),trust=str(trust),destination=str(destination),unlock=f.unlock.decode(),now=f.f.now)
        run,result=host.child(packet);self.assertEqual(run.returncode,0);self.assertTrue(result['quarantined'])
        memory=SyntheticMemory(destination,synthetic_only=True,encryption_key=f.f.key,clock=lambda:f.f.now)
        with memory._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bindings').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)

    def test_reactivation_guards_keep_recovery_pending_and_do_not_enroll(self):
        f,a,latest,target,restored=self.prepare();lineage=f.f.anchor.lineage;head=latest.head(lineage)
        expired=f.f.turn();expired=replace(expired,deadline=0)
        cancelled=f.f.turn();cancelled._cancelled.set()
        damaged=self.home/'damaged.sqlite';damaged.write_bytes(target.read_bytes()+b'FAKE_TAMPER')
        cases=[(PermissionError,dict(approved=False)),(PermissionError,dict(approved=1)),
            (PermissionError,dict(turn=f.f.turn(verified=False))),(PermissionError,dict(turn=expired)),
            (InterruptedError,dict(turn=cancelled)),(PermissionError,dict(turn=f.f.turn(principal='4'*64))),
            (Conflict,dict(expected_epoch=restored['writer_epoch']+1)),
            (Conflict,dict(expected_anchor=replace(f.f.anchor,sequence=f.f.anchor.sequence+1))),
            (ValueError,dict(restored=damaged))]
        for error,kwargs in cases:
            with self.subTest(error=error.__name__,fields=sorted(kwargs)):
                with self.assertRaises(error):self.activate(f,target,restored,**kwargs)
                a.reconcile_publication(lineage,approved=True)
                self.assertEqual(latest.head(lineage),head)
                self.assertTrue(a.head(lineage)['recovery_pending']);self.assertFalse(a.head(lineage)['writer_active'])
        self.assertTrue(self.activate(f,target,restored)['publication_confirmed'])

    def test_reactivation_rolled_back_source_reconciles_before_safe_retry(self):
        f,a,latest,target,restored=self.prepare();head=latest.head(f.f.anchor.lineage)
        with patch.object(a,'_publish',side_effect=OSError('FAKE source failure')),self.assertRaises(OSError):
            self.activate(f,target,restored)
        with self.assertRaises(ValueError):latest.head(f.f.anchor.lineage)
        a.reconcile_publication(f.f.anchor.lineage,approved=True)
        self.assertEqual(latest.head(f.f.anchor.lineage),head)
        self.assertTrue(a.head(f.f.anchor.lineage)['recovery_pending'])
        self.assertTrue(self.activate(f,target,restored)['publication_confirmed'])

    def test_reactivation_committed_publication_failure_never_reissues_lost_grant(self):
        f,a,latest,target,restored=self.prepare();lineage=f.f.anchor.lineage
        with patch.object(a,'_stage',side_effect=OSError('FAKE publication failure')),self.assertRaises(OSError):
            self.activate(f,target,restored)
        with self.assertRaises(ValueError):latest.head(lineage)
        with self.assertRaises(Conflict):self.activate(f,target,restored)
        status=a.reconcile_publication(lineage,approved=True)
        self.assertEqual(set(status),{'anchor','writer_epoch','publication_confirmed','synthetic_only'})
        self.assertEqual(status['writer_epoch'],restored['writer_epoch']+1)
        with self.assertRaises(Conflict):self.activate(f,target,restored)
        a.reconcile_publication(lineage,approved=True)
        self.assertEqual(a.head(lineage)['writer_epoch'],status['writer_epoch'])
        grant=a.acquire(lineage,'c'*32,expected_epoch=status['writer_epoch'],approved=True)
        self.assertEqual(grant.epoch,status['writer_epoch']+1)
        self.assertEqual(latest.head(lineage).pins.state.writer_epoch,grant.epoch)

    def test_reactivation_rechecks_owner_expiry_identity_and_cancellation_after_publication(self):
        for mode in ('expiry','identity','cancellation'):
            with self.subTest(mode=mode):
                f,a,latest,target,restored=self.prepare();turn=f.f.turn();context=[turn.context]
                turn=replace(turn,_resolve=lambda:context[0]);original=a._stage
                def invalidate(*args,**kwargs):
                    result=original(*args,**kwargs)
                    if mode=='expiry':f.f.now+=400
                    elif mode=='identity':context[0]=replace(turn.context,generation='5'*64)
                    else:turn._cancelled.set()
                    return result
                with patch.object(a,'_stage',side_effect=invalidate),self.assertRaises(
                        InterruptedError if mode=='cancellation' else PermissionError):
                    self.activate(f,target,restored,turn=turn)
                head=latest.head(f.f.anchor.lineage)
                self.assertEqual(head.pins.state.writer_epoch,restored['writer_epoch']+1)
                self.assertFalse(a.head(f.f.anchor.lineage)['recovery_pending'])
                with self.assertRaises(Conflict):self.activate(f,target,restored)
                a.reconcile_publication(f.f.anchor.lineage,approved=True)
                self.assertEqual(latest.head(f.f.anchor.lineage),head)

    def test_reactivation_missing_latest_refuses_without_recreation_or_source_commit(self):
        f,a,latest,target,restored=self.prepare();catalog=a._repository.catalog.read_bytes()
        saved=latest.path.read_bytes();latest.path.unlink()
        with self.assertRaises(sqlite3.DatabaseError):self.activate(f,target,restored)
        self.assertFalse(latest.path.exists());self.assertEqual(a._repository.catalog.read_bytes(),catalog)
        latest.path.write_bytes(saved);self.assertTrue(self.activate(f,target,restored)['publication_confirmed'])

    def test_reactivation_process_death_at_five_commit_boundaries(self):
        activation_crash=CRASH.replace(
            "a.handle(grant,turn,p['request'],expected_anchor=CheckpointAnchor(**p['anchor']),approved=True)",
            "a.activate_restored(grant.lineage,p['quarantine'],turn,'b'*32,expected_anchor=CheckpointAnchor(**p['anchor']),expected_epoch=p['epoch'],approved=True)")
        self.assertNotEqual(activation_crash,CRASH)
        for mode in ('reserve_after','source_before','source_after','confirm_after','journal_after'):
            with self.subTest(mode=mode):
                f,a,latest,target,restored=self.prepare();grant=f.f.grant;root=Path(__file__).resolve().parent
                imports=[str(root),str(root/'review/2026-10-13-memory-linux')]
                if sys.platform=='win32':imports.append(str(root/'review/2026-10-12-memory-hardening/.drivers'))
                packet=dict(imports=imports,latest=str(latest.path),source=str(a._repository.path),publications=str(a._publications),
                    capsule=str(f.capsule),unlock=f.unlock.decode(),recovery=f.key.decode(),storage=f.f.key.hex(),now=f.f.now,
                    grant=dict(lineage=grant.lineage,epoch=grant.epoch,writer=grant.writer,token=grant.token.hex()),
                    anchor=asdict(f.f.anchor),quarantine=str(target),epoch=restored['writer_epoch'],mode=mode)
                run=subprocess.run([sys.executable,'-I','-B','-c',activation_crash],input=json.dumps(packet),capture_output=True,
                    text=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                self.assertEqual(run.returncode,71 if mode=='source_before' else 72,'Fake reactivation crash failed; raw output withheld.')
                self.assertEqual((run.stdout,run.stderr),('',''))
                status=a.reconcile_publication(grant.lineage,approved=True)
                if mode in ('reserve_after','source_before'):
                    self.assertEqual(status['writer_epoch'],restored['writer_epoch'])
                    self.assertTrue(a.head(grant.lineage)['recovery_pending'])
                    self.assertTrue(self.activate(f,target,restored)['publication_confirmed'])
                else:
                    self.assertEqual(status['writer_epoch'],restored['writer_epoch']+1)
                    self.assertFalse(a.head(grant.lineage)['recovery_pending'])
                    with self.assertRaises(Conflict):self.activate(f,target,restored)
                    a.reconcile_publication(grant.lineage,approved=True)
                with self.assertRaises(PermissionError):self.call(f,f.f.packet('old-writer'))
                a.reconcile_publication(grant.lineage,approved=True)
