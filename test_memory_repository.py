"""Disposable fake recovery destinations/keys only; no external service or real memory."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from brain.memory_prototype import Conflict, SyntheticMemory
from brain.memory_recovery import SyntheticRecovery
from brain.memory_repository import SyntheticRepository
import test_memory_recovery as fixtures


class RepositoryChecks(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RecoveryChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.m,self.r = self.f.f.m,self.f.r
        self.root = self.f.folder/'fake-destination'
        self.repo = SyntheticRepository(self.root,synthetic_only=True)

    def sync(self, **kwargs):
        return self.repo.sync(self.m,self.r,approved=True,**kwargs)

    def status(self):
        return self.repo.status(self.m,self.r)

    def latest(self):
        with self.repo._db() as db:
            return dict(db.execute('SELECT * FROM latest').fetchone())

    def restore(self):
        target = self.f.path('restored.sqlite')
        lineage,sequence = self.repo._state(self.m)
        result = self.repo.restore(lineage,self.r,target,required_sequence=sequence,approved=True)
        return SyntheticMemory(target,synthetic_only=True,clock=lambda:self.f.f.now),result

    def test_pending_verified_restart_and_lost_ack_retry_without_duplicate_bundle(self):
        self.assertEqual(self.status()['state'],'pending')
        self.assertIsNone(self.status()['acknowledged_sequence'])
        self.assertEqual(self.sync()['state'],'verified')
        old = self.latest()
        self.repo = SyntheticRepository(self.root,synthetic_only=True)
        self.assertTrue(self.status()['current_snapshot_verified'])
        self.assertEqual(self.sync()['state'],'verified')
        self.assertEqual(self.latest(),old)
        self.assertEqual(len(list((self.root/'objects').iterdir())),1)
        restored,result = self.restore()
        self.assertEqual(result['preserved'],3)
        self.assertEqual(result['active_bindings'],0)
        self.assertEqual(result['resumed_jobs'],0)
        def records(memory):
            return {mid:{key:value for key,value in row.items() if key != 'rowid'}
                    for mid,row in self.f.rows(memory).items()}
        self.assertEqual(records(restored),records(self.m))
        catalogue = self.repo.catalog.read_bytes()
        self.assertNotIn(self.f.key,catalogue)
        self.assertNotIn(b'SYNTHETIC_KEEP',catalogue)
        self.assertNotIn('SYNTHETIC_',json.dumps(self.status()))

    def test_correction_and_forget_invalidate_old_ack_and_restore_latest_only(self):
        self.sync()
        self.f.f.call(dict(op='correct',project='alpha',request_id=self.f.f.rid(),
                          id=self.f.kept['id'],expected_revision=1,value={'text':'SYNTHETIC_CORRECTION'}))
        self.assertEqual(self.status()['state'],'pending')
        self.sync()
        self.f.forget()
        self.assertFalse(self.status()['current_snapshot_verified'])
        self.sync()
        restored,result = self.restore()
        rows = self.f.rows(restored)
        self.assertIn('SYNTHETIC_CORRECTION',rows[self.f.kept['id']]['value'])
        self.assertIsNone(rows[self.f.forgotten['id']]['value'])
        self.assertEqual(result['suppressed_deleted'],1)
        with restored._db() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM memory_search WHERE memory_search MATCH 'SYNTHETIC_FORGOTTEN'").fetchone()[0],0)

    def test_source_mutation_during_transfer_cannot_claim_current_snapshot_verified(self):
        original = self.r._backup
        def save_during_transfer(*args):
            result = original(*args)
            self.f.f.call(self.f.f.save_packet(key='concurrent fixture'))
            return result
        with patch.object(self.r,'_backup',side_effect=save_during_transfer):
            self.assertEqual(self.sync()['state'],'pending')
        with self.assertRaises(Conflict):self.restore()
        self.assertEqual(self.sync()['state'],'verified')
        self.assertEqual(self.restore()[1]['preserved'],4)

    def test_readback_damage_never_acknowledges_and_retry_repairs(self):
        original = self.r.bundle
        def damage(memory,backup,checkpoint,**kwargs):
            anchor = original(memory,backup,checkpoint,**kwargs)
            checkpoint.write_bytes(checkpoint.read_bytes()[:-8])
            return anchor
        with patch.object(self.r,'bundle',side_effect=damage):
            with self.assertRaises(ValueError):self.sync()
        self.assertIsNone(self.status()['acknowledged_sequence'])
        self.assertEqual(len(self.f.rows(self.m)),3)
        self.assertEqual(self.sync()['state'],'verified')

    def test_transfer_and_catalogue_failures_keep_old_ack_and_committed_memory(self):
        self.sync();old = self.latest()
        self.f.f.call(self.f.f.save_packet(key='saved before outage'))
        with patch.object(self.r,'_checkpoint',side_effect=OSError('fake destination full')):
            with self.assertRaises(OSError):self.sync()
        self.assertEqual(self.latest(),old)
        self.assertEqual(self.status()['state'],'pending')
        with self.repo._db() as db:
            db.execute("CREATE TRIGGER fake_full BEFORE INSERT ON latest BEGIN SELECT RAISE(ABORT,'fake catalogue full'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.sync()
        self.assertEqual(self.latest(),old)
        self.assertEqual(len(self.f.rows(self.m)),4)
        with self.repo._db() as db:db.execute('DROP TRIGGER fake_full')
        self.assertEqual(self.sync()['state'],'verified')

    def test_cancellation_after_files_verified_does_not_commit_ack(self):
        event = threading.Event()
        original = self.repo._verify
        def cancel_after_readback(*args):
            result = original(*args)
            event.set()
            return result
        with patch.object(self.repo,'_verify',side_effect=cancel_after_readback):
            with self.assertRaises(InterruptedError):self.sync(cancelled=event.is_set)
        self.assertIsNone(self.status()['acknowledged_sequence'])
        self.assertEqual(self.sync()['state'],'verified')
        old = self.latest()
        with self.assertRaises(InterruptedError):self.sync(cancelled=lambda:True)
        self.assertEqual(self.latest(),old)

    def test_stale_source_cannot_roll_back_latest_ack(self):
        old_path = self.f.path('old-source.sqlite')
        with closing(sqlite3.connect(self.m.path)) as source, closing(sqlite3.connect(old_path)) as old:
            source.backup(old)
        stale = SyntheticMemory(old_path,synthetic_only=True)
        self.f.forget();self.sync();latest = self.latest()
        self.assertEqual(self.repo.status(stale,self.r)['state'],'source_behind')
        with self.assertRaises(Conflict):self.repo.sync(stale,self.r,approved=True)
        self.assertEqual(self.latest(),latest)
        self.assertEqual(self.restore()[1]['suppressed_deleted'],1)

    def test_unacknowledged_forget_blocks_restore_of_known_stale_snapshot(self):
        self.sync();self.f.forget()
        self.assertEqual(self.status()['state'],'pending')
        with self.assertRaises(Conflict):self.restore()
        self.assertEqual(self.sync()['state'],'verified')
        self.assertEqual(self.restore()[1]['suppressed_deleted'],1)

    def test_missing_changed_or_wrong_key_bundle_never_restores_or_reports_verified(self):
        self.sync();row = self.latest()
        folder = self.root/'objects'/row['object_id']
        wrong = SyntheticRecovery(SyntheticRecovery.new_key(),synthetic_only=True)
        self.assertEqual(self.repo.status(self.m,wrong)['state'],'unavailable')
        target = self.f.path('wrong-key.sqlite')
        with self.assertRaises(ValueError):self.repo.restore(row['lineage'],wrong,target,required_sequence=row['sequence'],approved=True)
        self.assertFalse(target.exists())
        for name in ('backup.enc','checkpoint.enc'):
            path = folder/name
            original = path.read_bytes()
            path.unlink()
            self.assertEqual(self.status()['state'],'unavailable')
            target = self.f.path('missing.sqlite')
            with self.assertRaises(OSError):self.repo.restore(row['lineage'],self.r,target,required_sequence=row['sequence'],approved=True)
            self.assertFalse(target.exists())
            path.write_bytes(original[:-5])
            self.assertEqual(self.status()['state'],'unavailable')
            with self.assertRaises(ValueError):self.repo.restore(row['lineage'],self.r,target,required_sequence=row['sequence'],approved=True)
            self.assertFalse(target.exists())
            path.write_bytes(original)
        self.assertEqual(self.status()['state'],'verified')

    def test_valid_ciphertext_replacement_is_rejected_by_acknowledged_hash(self):
        self.sync();row = self.latest()
        backup = self.root/'objects'/row['object_id']/'backup.enc'
        data,_ = self.r._open(backup,b'LYA-FAKE-BACKUP-1\n')
        data['records'][0]['value'] = '{"text":"SYNTHETIC_REPLACEMENT"}'
        backup.write_bytes(b'LYA-FAKE-BACKUP-1\n'+self.r.cipher.encrypt(json.dumps(data).encode()))
        self.assertEqual(self.status()['state'],'unavailable')
        with self.assertRaises(ValueError):self.restore()
        self.assertEqual(self.sync()['state'],'verified')

    def test_backup_replacement_after_readback_is_checked_again_at_restore(self):
        self.sync();row = self.latest()
        backup = self.root/'objects'/row['object_id']/'backup.enc'
        original = self.r.restore
        def swap_after_verification(*args,**kwargs):
            data,_ = self.r._open(backup,b'LYA-FAKE-BACKUP-1\n')
            backup.write_bytes(b'LYA-FAKE-BACKUP-1\n'+self.r.cipher.encrypt(json.dumps(data).encode()))
            return original(*args,**kwargs)
        with patch.object(self.r,'restore',side_effect=swap_after_verification):
            with self.assertRaises(ValueError):self.restore()

    def test_literal_approval_lineage_isolation_and_unrelated_catalogue_preserved(self):
        with self.assertRaises(PermissionError):SyntheticRepository(self.root)
        for approved in (False,1,'yes',None):
            with self.assertRaises(PermissionError):self.repo.sync(self.m,self.r,approved=approved)
            with self.assertRaises(PermissionError):self.repo.restore('a'*32,self.r,self.f.path('denied'),required_sequence=0,approved=approved)
        self.assertIsNone(self.status()['acknowledged_sequence'])
        self.sync()
        other = SyntheticMemory(self.f.path('other.sqlite'),synthetic_only=True)
        self.assertEqual(self.repo.status(other,self.r)['state'],'pending')
        with self.assertRaises(ValueError):self.repo.restore('../escape',self.r,self.f.path('out'),required_sequence=0,approved=True)
        with self.assertRaises(ValueError):self.repo.restore(self.repo._state(other)[0],self.r,self.f.path('out'),required_sequence=0,approved=True)
        wrong = self.f.folder/'unrelated-destination';wrong.mkdir()
        with closing(sqlite3.connect(wrong/'catalog.sqlite')) as db:
            db.execute('CREATE TABLE unrelated(value TEXT)');db.commit()
        before = (wrong/'catalog.sqlite').read_bytes()
        with self.assertRaises(ValueError):SyntheticRepository(wrong,synthetic_only=True)
        self.assertEqual((wrong/'catalog.sqlite').read_bytes(),before)

    def test_missing_catalogue_is_not_silently_recreated_by_existing_instance(self):
        self.sync();self.repo.catalog.unlink()
        with self.assertRaises(sqlite3.OperationalError):self.status()
        with self.assertRaises(ValueError):SyntheticRepository(self.root,synthetic_only=True)
        self.assertFalse(self.repo.catalog.exists())

    def test_concurrent_publishers_keep_one_matching_ack(self):
        barrier = threading.Barrier(2)
        outcomes = []
        def run():
            try:
                barrier.wait(3)
                outcomes.append(self.sync()['state'])
            except BaseException as error:outcomes.append(error)
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
        self.assertEqual(outcomes,['verified','verified'])
        self.assertEqual(len(list((self.root/'objects').iterdir())),1)

    def test_process_death_before_ack_and_after_commit_then_retry(self):
        program = '''
from contextlib import contextmanager
import os,sys
from brain.memory_prototype import SyntheticMemory
from brain.memory_recovery import SyntheticRecovery
from brain.memory_repository import SyntheticRepository
source,destination,key,mode = sys.argv[1:]
memory = SyntheticMemory(source,synthetic_only=True)
recovery = SyntheticRecovery(key.encode(),synthetic_only=True)
repository = SyntheticRepository(destination,synthetic_only=True)
original = repository._db
@contextmanager
def die_before_ack(*args,**kwargs):
    with original(*args,**kwargs) as db:
        yield db
        os._exit(17)
if mode == 'before':repository._db = die_before_ack
repository.sync(memory,recovery,approved=True)
os._exit(18)
'''
        for mode,code in (('before',17),('after',18)):
            run = subprocess.run([sys.executable,'-c',program,str(self.m.path),str(self.root),self.f.key.decode(),mode],
                                 cwd=Path(__file__).resolve().parent,capture_output=True,text=True,timeout=15,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,code,run.stderr)
            self.assertEqual(self.status()['state'],'pending' if mode == 'before' else 'verified')
        old = self.latest()
        self.assertEqual(self.sync()['state'],'verified')
        self.assertEqual(self.latest(),old)


if __name__ == '__main__':unittest.main()
