"""Recovery checks: disposable stores, generated fake keys, no external transfer."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from brain import memory_recovery as recovery
from brain.memory_prototype import SyntheticMemory
import test_memory_prototype as memory_fixtures


class RecoveryChecks(unittest.TestCase):
    def setUp(self):
        fixture = memory_fixtures.MemoryChecks(methodName='runTest')
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        self.f = fixture
        self.folder = fixture.path.parent
        (self.folder/'backups').mkdir();(self.folder/'checkpoint-copy').mkdir()
        self.key = recovery.SyntheticRecovery.new_key()
        self.r = recovery.SyntheticRecovery(self.key,synthetic_only=True,clock=lambda:self.f.now)
        self.serial = 0
        self.forgotten = fixture.call(fixture.save_packet(key='fake forgotten',value='SYNTHETIC_FORGOTTEN'))
        self.expiring = fixture.call(fixture.save_packet(key='fake expires',value='SYNTHETIC_EXPIRES',retention={'mode':'until','expires_at':fixture.now+30}))
        self.kept = fixture.call(fixture.save_packet(key='fake kept',value='SYNTHETIC_KEEP'))

    def path(self, name):
        self.serial += 1
        return self.folder/f'{self.serial}-{name}'

    def backup(self):
        self.serial += 1
        path = self.folder/'backups'/f'{self.serial}-snapshot.enc'
        self.r.backup(self.f.m,path,approved=True)
        return path

    def checkpoint(self):
        self.serial += 1
        path = self.folder/'checkpoint-copy'/f'{self.serial}-state.enc'
        return path,self.r.checkpoint(self.f.m,path,approved=True)

    def restore(self, backup, checkpoint=None, anchor=None, **kwargs):
        if checkpoint is None:checkpoint,anchor = self.checkpoint()
        destination = self.path('restored.sqlite')
        result = self.r.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=True,**kwargs)
        return SyntheticMemory(destination,synthetic_only=True,clock=lambda:self.f.now),result

    def forget(self, mid=None):
        self.f.call(dict(op='forget',project='alpha',request_id=self.f.rid(),id=mid or self.forgotten['id'],expected_revision=1))

    def rows(self, memory):
        with memory._db() as db:
            return {row['id']:dict(row) for row in db.execute('SELECT * FROM memories')}

    def reseal(self, data, magic, *, checkpoint=False):
        path = self.path('altered.enc')
        blob = self.r._seal(data,magic,path,lambda:False)
        anchor = recovery.CheckpointAnchor(data['lineage'],data['sequence'],data['checkpoint_id'],hashlib.sha256(blob).hexdigest()) if checkpoint else None
        return path,anchor

    def test_encrypted_snapshot_roundtrip_and_restored_access_quarantine(self):
        backup = self.backup()
        checkpoint,anchor = self.checkpoint()
        for marker in (b'SYNTHETIC_KEEP',b'SYNTHETIC_FORGOTTEN',b'SYNTHETIC_EXPIRES',self.f.owner.encode()):
            self.assertNotIn(marker,backup.read_bytes())
            self.assertNotIn(marker,checkpoint.read_bytes())
        data,_ = self.r._open(checkpoint,recovery.CHECKPOINT_MAGIC)
        self.assertNotIn('SYNTHETIC_',json.dumps(data))
        restored,result = self.restore(backup,checkpoint,anchor)
        self.assertEqual(result,dict(preserved=3,suppressed_deleted=0,suppressed_expired=0,suppressed_unavailable=0,quarantined=True,active_bindings=0,resumed_jobs=0))
        self.assertIn('SYNTHETIC_KEEP',self.rows(restored)[self.kept['id']]['value'])
        with restored._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM bindings').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM outbox').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM requests').fetchone()[0],3)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_search').fetchone()[0],3)
        with self.assertRaises(PermissionError):restored.handle(self.f.f.laptop(),dict(op='get',project='alpha',id=self.kept['id']),approved=True)

    def test_old_backup_cannot_restore_later_forgotten_fact_or_search(self):
        backup = self.backup()
        self.forget()
        restored,result = self.restore(backup)
        row = self.rows(restored)[self.forgotten['id']]
        self.assertEqual((row['deleted'],row['revision'],row['key'],row['value']),(1,2,'',None))
        self.assertEqual(result['suppressed_deleted'],1)
        with restored._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM memory_search WHERE memory_search MATCH 'SYNTHETIC_FORGOTTEN'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT reason FROM deletions WHERE memory_id=?',(row['id'],)).fetchone()[0],'forget')
            self.assertNotIn('SYNTHETIC_FORGOTTEN',str([tuple(r) for r in db.execute('SELECT * FROM requests')]))

    def test_recovered_store_can_be_backed_up_again_without_reactivating_access(self):
        backup = self.backup();self.forget()
        restored,first = self.restore(backup)
        next_backup = self.path('next-backup.enc')
        next_checkpoint = self.path('next-checkpoint.enc')
        self.r.backup(restored,next_backup,approved=True)
        anchor = self.r.checkpoint(restored,next_checkpoint,approved=True)
        again,result = self.restore(next_backup,next_checkpoint,anchor)
        self.assertEqual(result,first)
        self.assertEqual(self.rows(again),self.rows(restored))
        with again._db() as db:
            self.assertEqual([row[0] for row in db.execute('SELECT id FROM owners')],[self.f.owner])
            self.assertEqual(db.execute('SELECT count(*) FROM bindings').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM outbox').fetchone()[0],0)

    def test_old_prototype_schema_is_refused_without_automatic_migration(self):
        with self.f.m._db() as db:db.execute('PRAGMA user_version=1')
        original = self.f.path.read_bytes()
        with self.assertRaises(ValueError):SyntheticMemory(self.f.path,synthetic_only=True)
        with self.assertRaises(ValueError):self.backup()
        self.assertEqual(self.f.path.read_bytes(),original)

    def test_expiry_enforced_at_restore_even_without_expiry_cleanup_checkpoint(self):
        backup = self.backup();checkpoint,anchor = self.checkpoint()
        self.f.now += 31
        restored,result = self.restore(backup,checkpoint,anchor)
        self.assertEqual(result['suppressed_expired'],1)
        row = self.rows(restored)[self.expiring['id']]
        self.assertEqual((row['deleted'],row['revision'],row['value']),(1,2,None))

    def test_later_correction_and_missing_post_backup_record_do_not_restore_old_facts(self):
        backup = self.backup()
        self.f.call(dict(op='correct',project='alpha',request_id=self.f.rid(),id=self.kept['id'],expected_revision=1,value={'text':'SYNTHETIC_LATER_VALUE'}))
        later = self.f.call(self.f.save_packet(key='later record',value='SYNTHETIC_POST_BACKUP'))
        restored,result = self.restore(backup)
        self.assertEqual(result['suppressed_unavailable'],2)
        rows = self.rows(restored)
        self.assertEqual(rows[self.kept['id']]['revision'],3)
        self.assertEqual(rows[later['id']]['revision'],2)
        self.assertIsNone(rows[self.kept['id']]['value'])
        self.assertIsNone(rows[later['id']]['value'])
        self.assertNotIn('SYNTHETIC_LATER_VALUE',str(rows))

    def test_latest_anchor_rejects_replayed_old_checkpoint(self):
        backup = self.backup();old,old_anchor = self.checkpoint()
        self.forget();latest,anchor = self.checkpoint()
        destination = self.path('rejected.sqlite')
        with self.assertRaises(ValueError):self.r.restore(backup,old,destination,trusted_anchor=anchor,approved=True)
        self.assertFalse(destination.exists())
        restored,result = self.restore(backup,latest,anchor)
        self.assertEqual(result['suppressed_deleted'],1)
        self.assertNotEqual(old_anchor,anchor)

    def test_missing_wrong_malformed_keys_and_damaged_ciphertexts_refuse_restore(self):
        backup = self.backup();checkpoint,anchor = self.checkpoint()
        for key in (None,b'password',b'bad!'):
            with self.assertRaises(ValueError):recovery.SyntheticRecovery(key,synthetic_only=True)
        wrong = recovery.SyntheticRecovery(recovery.SyntheticRecovery.new_key(),synthetic_only=True)
        destination = self.path('wrong-key.sqlite')
        with self.assertRaises(ValueError):wrong.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=True)
        for source in (backup,checkpoint):
            original = source.read_bytes()
            for corrupted in (original[:-9],original[:30]+bytes([original[30]^1])+original[31:]):
                damaged = self.path('damaged.enc');damaged.write_bytes(corrupted)
                inputs = (damaged,checkpoint) if source == backup else (backup,damaged)
                with self.assertRaises(ValueError):self.r.restore(*inputs,destination,trusted_anchor=anchor,approved=True)
        with self.assertRaises(ValueError):self.r.restore(checkpoint,backup,destination,trusted_anchor=anchor,approved=True)
        self.assertFalse(destination.exists())

    def test_missing_checkpoint_anchor_or_input_fails_without_publishing(self):
        backup = self.backup();checkpoint,anchor = self.checkpoint()
        destination = self.path('missing-state.sqlite')
        with self.assertRaises(ValueError):self.r.restore(backup,checkpoint,destination,trusted_anchor=None,approved=True)
        with self.assertRaises(FileNotFoundError):self.r.restore(backup,self.path('absent.enc'),destination,trusted_anchor=anchor,approved=True)
        with self.assertRaises(ValueError):self.r.restore(backup,checkpoint,destination,trusted_anchor=replace(anchor,sequence=anchor.sequence+1),approved=True)
        self.assertFalse(destination.exists())

    def test_incomplete_deletion_register_and_missing_head_fail_closed(self):
        backup = self.backup();self.forget()
        checkpoint,_ = self.checkpoint()
        original,_ = self.r._open(checkpoint,recovery.CHECKPOINT_MAGIC)
        for change in ('deletion','head'):
            data = copy.deepcopy(original)
            if change == 'deletion':data['deletions'] = []
            else:data['heads'] = [row for row in data['heads'] if row['id'] != self.kept['id']]
            altered,anchor = self.reseal(data,recovery.CHECKPOINT_MAGIC,checkpoint=True)
            destination = self.path('incomplete.sqlite')
            with self.assertRaises(ValueError):self.r.restore(backup,altered,destination,trusted_anchor=anchor,approved=True)
            self.assertFalse(destination.exists())

    def test_older_checkpoint_cannot_cover_newer_snapshot(self):
        old,anchor = self.checkpoint()
        self.f.call(self.f.save_packet(key='later'))
        backup = self.backup()
        destination = self.path('stale-state.sqlite')
        with self.assertRaises(ValueError):self.r.restore(backup,old,destination,trusted_anchor=anchor,approved=True)
        self.assertFalse(destination.exists())

    def test_wrong_lineage_and_scope_changes_cannot_cross_restore(self):
        backup = self.backup();checkpoint,_ = self.checkpoint()
        original,_ = self.r._open(checkpoint,recovery.CHECKPOINT_MAGIC)
        for change in ('lineage','scope','no_revision'):
            data = copy.deepcopy(original)
            if change == 'lineage':data['lineage'] = 'b'*32
            elif change == 'scope':data['heads'][0]['project'] = 'different-project'
            else:data['heads'][0]['expires_at'] = self.f.now+100
            altered,anchor = self.reseal(data,recovery.CHECKPOINT_MAGIC,checkpoint=True)
            with self.assertRaises(ValueError):self.restore(backup,altered,anchor)

    def test_authenticated_but_malformed_snapshot_and_receipt_rejected(self):
        backup = self.backup();checkpoint,anchor = self.checkpoint()
        original,_ = self.r._open(backup,recovery.BACKUP_MAGIC)
        for change in ('extra','kind','receipt','duplicate'):
            data = copy.deepcopy(original)
            if change == 'extra':data['records'][0]['trusted_admin'] = True
            elif change == 'kind':data['records'][0]['kind'] = 'credentials'
            elif change == 'receipt':data['requests'][0]['result'] = '{"value":"SYNTHETIC_VALUE"}'
            else:data['records'].append(data['records'][0])
            altered,_ = self.reseal(data,recovery.BACKUP_MAGIC)
            with self.assertRaises(ValueError):self.restore(altered,checkpoint,anchor)

    def test_existing_outputs_never_overwritten_and_failed_publication_is_invisible(self):
        backup = self.backup();checkpoint,anchor = self.checkpoint()
        destination = self.path('existing.sqlite');destination.write_bytes(b'EXISTING_FAKE_FILE')
        for action in (lambda:self.r.backup(self.f.m,backup,approved=True),
                       lambda:self.r.checkpoint(self.f.m,checkpoint,approved=True),
                       lambda:self.r.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=True)):
            with self.assertRaises(FileExistsError):action()
        self.assertEqual(destination.read_bytes(),b'EXISTING_FAKE_FILE')
        target = self.path('publication-fails.sqlite')
        with patch.object(recovery.os,'link',side_effect=OSError('synthetic publication failure')):
            with self.assertRaises(OSError):self.r.restore(backup,checkpoint,target,trusted_anchor=anchor,approved=True)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.folder.glob('.lya-fake-recovery-*')))

    def test_cancellation_and_approval_denial_never_publish(self):
        backup = self.backup();checkpoint,anchor = self.checkpoint()
        destination = self.path('cancelled.sqlite')
        for approved in (False,1,'yes'):
            with self.assertRaises(PermissionError):self.r.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=approved)
            with self.assertRaises(PermissionError):self.r.backup(self.f.m,destination,approved=approved)
            with self.assertRaises(PermissionError):self.r.checkpoint(self.f.m,destination,approved=approved)
        with self.assertRaises(InterruptedError):self.r.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=True,cancelled=lambda:True)
        with patch('brain.memory_recovery._publish', wraps=recovery._publish):
            calls = [False,False,True]
            with self.assertRaises(InterruptedError):self.r.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=True,cancelled=lambda:calls.pop(0))
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.folder.glob('.lya-fake-recovery-*')))

    def test_consistent_snapshot_includes_committed_wal_content(self):
        wal = sqlite3.connect(self.f.path)
        self.addCleanup(wal.close)
        self.assertEqual(wal.execute('PRAGMA journal_mode=WAL').fetchone()[0],'wal')
        wal.execute('BEGIN')
        wal.execute('SELECT count(*) FROM memories').fetchone()
        receipt = self.f.call(self.f.save_packet(key='wal fixture',value='SYNTHETIC_WAL_COMMIT'))
        self.assertTrue(Path(str(self.f.path)+'-wal').exists())
        backup = self.backup()
        restored,result = self.restore(backup)
        self.assertEqual(result['preserved'],4)
        self.assertIn('SYNTHETIC_WAL_COMMIT',self.rows(restored)[receipt['id']]['value'])

    def test_size_and_duplicate_json_fields_are_rejected(self):
        backup = self.backup();checkpoint,anchor = self.checkpoint()
        destination = self.path('size.sqlite')
        with patch.object(recovery,'MAX_BLOB',10):
            with self.assertRaises(ValueError):self.r.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=True)
        malformed = self.path('duplicate.enc')
        malformed.write_bytes(recovery.BACKUP_MAGIC+self.r.cipher.encrypt(b'{"format":1,"format":2}'))
        with self.assertRaises(ValueError):self.r.restore(malformed,checkpoint,destination,trusted_anchor=anchor,approved=True)
        self.assertFalse(destination.exists())


if __name__ == '__main__':unittest.main()
