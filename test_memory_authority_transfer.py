"""Full catalogue survival with generated secrets and temporary stores only."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import patch

from cryptography.fernet import Fernet
from brain.memory_authority_transfer import seal_authority,restore_authority,resume_authority,_open_authority,MARKER
from brain.memory_prototype import Conflict,SyntheticMemory
from brain.memory_publication_authority import SyntheticPublicationAuthority
from brain.memory_recovery import SyntheticRecovery
from test_memory_publication_authority import PublicationAuthorityChecks

WORKER=r'''
import json,pathlib,sys
p=json.load(sys.stdin);sys.path[:0]=p['imports']
from brain.memory_authority_transfer import restore_authority
from brain.memory_recovery_latest import SyntheticRecoveryLatest
assert not pathlib.Path(p['lost']).exists()
out=restore_authority(p['bundle'],p['destination'],latest=SyntheticRecoveryLatest(p['latest'],synthetic_only=True),
    lineage=p['lineage'],unlock_key=p['unlock'].encode(),trusted_digest=p['digest'],synthetic_only=True,approved=True,clock=lambda:p['now'])
assert out['quarantined'] and out['active_bindings']==out['resumed_jobs']==0 and out['publication_confirmed']
print(json.dumps(dict(passed=True,source_absent=True,catalogue_restored=True,writer_fenced=True,quarantined=True)))
'''


class AuthorityTransferChecks(PublicationAuthorityChecks):
    def sealed(self):
        f,a,latest,_,_=self.make();f.latest();bundle=self.home/('a'+str(self.number)+'.enc')
        receipt=seal_authority(a,bundle,lineage=f.f.anchor.lineage,synthetic_only=True,approved=True)
        return f,a,latest,bundle,receipt

    def restore(self,f,latest,bundle,receipt,**kwargs):
        values=dict(latest=latest,lineage=f.f.anchor.lineage,unlock_key=f.unlock,trusted_digest=receipt['sha256'],
            synthetic_only=True,approved=True,clock=lambda:f.f.now)
        values.update(kwargs);return restore_authority(bundle,self.home/'restored',**values)

    def resume(self,f,latest,receipt,**kwargs):
        return resume_authority(self.home/'restored',latest=latest,lineage=f.f.anchor.lineage,unlock_key=f.unlock,
            trusted_capsule_digest=receipt['head'].pins.keys_digest,synthetic_only=True,approved=True,clock=lambda:f.f.now,**kwargs)

    def reopened(self,f,latest,receipt):
        return _open_authority(self.home/'restored',latest,f.unlock,f.f.anchor.lineage,receipt['head'].pins.keys_digest,lambda:f.f.now)

    def test_transfer_source_loss_preserves_owner_mapping_and_requires_fresh_reactivation(self):
        f,a,latest,bundle,receipt=self.sealed();old=f.f.grant;lost=f.f.home;f.doCleanups();self.assertFalse(lost.exists())
        out=self.restore(f,latest,bundle,receipt);restored=self.reopened(f,latest,receipt)
        self.assertTrue(out['publication_confirmed']);self.assertEqual(out['writer_epoch'],old.epoch+1)
        self.assertFalse((self.home/'restored'/MARKER).exists())
        memory=SyntheticMemory(out['quarantine'],synthetic_only=True,encryption_key=f.f.key,clock=lambda:f.f.now)
        with memory._db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM bindings').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM outbox').fetchone()[0],0)
            rows={row['id']:dict(row) for row in db.execute('SELECT * FROM memories')}
            self.assertEqual(json.loads(rows[f.kept['id']]['value']),{'text':'SYNTHETIC_PACK_CORRECTION'})
            for mid in (f.forgotten['id'],f.expired['id']):self.assertEqual((rows[mid]['deleted'],rows[mid]['value']),(1,None))
        with self.assertRaises(PermissionError):
            restored.handle(old,f.f.turn(),f.f.packet(),expected_anchor=out['anchor'],approved=True)
        restored.reconcile_publication(old.lineage,approved=True)
        reply=restored.activate_restored(old.lineage,out['quarantine'],f.f.turn(),'b'*32,
            expected_anchor=out['anchor'],expected_epoch=out['writer_epoch'],approved=True)
        self.assertTrue(reply['publication_confirmed']);self.assertEqual(reply['grant'].epoch,old.epoch+2)
        self.assertEqual((reply['active_bindings'],reply['resumed_jobs']),(1,0))
        result=restored.handle(reply['grant'],f.f.turn(),dict(op='get',project='alpha',id=f.kept['id']),
            expected_anchor=reply['anchor'],approved=True)
        self.assertEqual(result['result']['record']['value'],{'text':'SYNTHETIC_PACK_CORRECTION'})

    def test_transfer_stale_record_or_writer_epoch_is_refused_before_destination(self):
        for mode in ('record','writer'):
            f,a,latest,bundle,receipt=self.sealed()
            if mode=='record':self.call(f,f.f.packet('newer'))
            else:a.acquire(f.f.anchor.lineage,'c'*32,expected_epoch=f.f.grant.epoch,approved=True)
            current=latest.head(f.f.anchor.lineage)
            with self.assertRaises(Conflict):self.restore(f,latest,bundle,receipt)
            self.assertFalse((self.home/'restored').exists());self.assertEqual(latest.head(f.f.anchor.lineage),current)

    def test_transfer_authentication_literal_approval_and_encryption_boundaries(self):
        f,a,latest,bundle,receipt=self.sealed();blob=bundle.read_bytes()
        for secret in (f.unlock,f.key,f.f.key,b'SQLite format 3',b'SYNTHETIC_PACK_CORRECTION',f.f.grant.token):self.assertNotIn(secret,blob)
        for kwargs in ({'approved':False},{'approved':1},{'synthetic_only':False},{'synthetic_only':1}):
            with self.assertRaises(PermissionError):self.restore(f,latest,bundle,receipt,**kwargs)
        for kwargs in ({'unlock_key':Fernet.generate_key()},{'trusted_digest':'0'*64}):
            with self.assertRaises(ValueError):self.restore(f,latest,bundle,receipt,**kwargs)
        bundle.write_bytes(blob[:-1]+bytes([blob[-1]^1]))
        with self.assertRaises(ValueError):self.restore(f,latest,bundle,receipt)
        self.assertFalse((self.home/'restored').exists())

    def test_transfer_capture_refuses_pending_source_and_pending_owner_recovery(self):
        f,a,latest,bundle,receipt=self.sealed();new=self.home/'refused.enc'
        with patch.object(a,'_stage',side_effect=OSError('FAKE publication unavailable')),self.assertRaises(OSError):
            self.call(f,f.f.packet('pending'))
        with self.assertRaises(Conflict):seal_authority(a,new,lineage=f.f.anchor.lineage,synthetic_only=True,approved=True)
        out=a.reconcile_publication(f.f.anchor.lineage,approved=True)
        a.restore(f.f.anchor.lineage,self.home/'q.sqlite',expected_anchor=out['anchor'],approved=True)
        with self.assertRaises(Conflict):seal_authority(a,new,lineage=f.f.anchor.lineage,synthetic_only=True,approved=True)
        self.assertFalse(new.exists())

    def test_transfer_rollback_preserves_incomplete_candidate_and_explicit_retry_quarantine(self):
        f,a,latest,bundle,receipt=self.sealed();f.doCleanups();original=SyntheticRecovery.restore
        def fail_after_quarantine(service,*args,**kwargs):
            original(service,*args,**kwargs);raise OSError('FAKE failure after quarantine creation')
        with patch.object(SyntheticRecovery,'restore',fail_after_quarantine),self.assertRaises(OSError):self.restore(f,latest,bundle,receipt)
        self.assertTrue((self.home/'restored'/MARKER).exists())
        with self.assertRaises(ValueError):latest.head(f.f.anchor.lineage)
        with self.assertRaises(FileExistsError):self.resume(f,latest,receipt)
        out=self.resume(f,latest,receipt,quarantine='retry-quarantine.sqlite')
        self.assertTrue(out['quarantined']);self.assertEqual(out['writer_epoch'],f.f.grant.epoch+1)
        self.assertTrue((self.home/'restored/quarantine.sqlite').is_file())

    def test_transfer_committed_fence_reconciles_without_replaying_restore(self):
        f,a,latest,bundle,receipt=self.sealed();f.doCleanups();original=SyntheticPublicationAuthority._stage
        def fail_after_commit(service,pins,*args,**kwargs):
            if pins.state.writer_epoch>receipt['head'].pins.state.writer_epoch:raise OSError('FAKE publication unavailable')
            return original(service,pins,*args,**kwargs)
        with patch.object(SyntheticPublicationAuthority,'_stage',fail_after_commit),self.assertRaises(OSError):
            self.restore(f,latest,bundle,receipt)
        target=self.home/'restored/quarantine.sqlite';digest=hashlib.sha256(target.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):latest.head(f.f.anchor.lineage)
        out=self.resume(f,latest,receipt)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(),digest)
        self.assertEqual(out['writer_epoch'],f.f.grant.epoch+1);self.assertNotIn('grant',out)
        with self.assertRaises(ValueError):self.resume(f,latest,receipt)

    def test_transfer_fresh_child_restores_without_original_source_or_catalogue(self):
        f,a,latest,bundle,receipt=self.sealed();lost=f.f.home;f.doCleanups();root=Path(__file__).resolve().parent
        imports=[str(root),str(root/'review/2026-10-13-memory-linux')]
        if sys.platform=='win32':imports.append(str(root/'review/2026-10-12-memory-hardening/.drivers'))
        packet=dict(imports=imports,bundle=str(bundle),latest=str(latest.path),lineage=f.f.anchor.lineage,
            unlock=f.unlock.decode(),digest=receipt['sha256'],now=f.f.now,lost=str(lost),destination=str(self.home/'child'))
        run=subprocess.run([sys.executable,'-I','-B','-c',WORKER],input=json.dumps(packet),capture_output=True,text=True,
            timeout=45,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(run.returncode,0,'Fresh fake transfer child failed; raw output withheld.')
        self.assertEqual(run.stderr,'');self.assertTrue(json.loads(run.stdout)['source_absent'])

    def test_transfer_refuses_overwrite_missing_latest_and_byte_budget(self):
        f,a,latest,bundle,receipt=self.sealed();saved=latest.path.read_bytes();latest.path.unlink()
        with self.assertRaises(sqlite3.DatabaseError):self.restore(f,latest,bundle,receipt)
        self.assertFalse(latest.path.exists());self.assertFalse((self.home/'restored').exists());latest.path.write_bytes(saved)
        (self.home/'restored').mkdir();sentinel=self.home/'restored/keep';sentinel.write_bytes(b'FAKE_KEEP')
        with self.assertRaises(FileExistsError):self.restore(f,latest,bundle,receipt)
        self.assertEqual(sentinel.read_bytes(),b'FAKE_KEEP')
        with patch('brain.memory_authority_transfer.MAX_BLOB',1),self.assertRaises(ValueError):self.restore(f,latest,bundle,receipt)
        with self.assertRaises(FileExistsError):seal_authority(a,bundle,lineage=f.f.anchor.lineage,synthetic_only=True,approved=True)
