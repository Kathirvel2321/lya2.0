"""Regression cases for the isolated memory/recovery prototypes; fake data only."""
from contextlib import closing
import copy
import sqlite3
import unittest

from brain.memory_prototype import Conflict, SyntheticMemory
from brain.memory_recovery import SyntheticRecovery, BACKUP_MAGIC
from brain.memory_repository import SyntheticRepository
import test_memory_repository as fixtures


class HardeningChecks(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RepositoryChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()

    def test_missing_open_store_is_not_recreated(self):
        path = self.f.m.path
        path.unlink()
        with self.assertRaises((ValueError,sqlite3.OperationalError)):
            self.f.repo.status(self.f.m,self.f.r)
        self.assertFalse(path.exists())

    def test_wrong_sync_key_cannot_silently_rotate_existing_acknowledgement(self):
        self.f.sync();original = self.f.latest()
        wrong = SyntheticRecovery(SyntheticRecovery.new_key(),synthetic_only=True)
        for changed in (False,True):
            if changed:self.f.f.f.call(self.f.f.f.save_packet(key='new after acknowledgement'))
            with self.assertRaises(PermissionError):self.f.repo.sync(self.f.m,wrong,approved=True)
            self.assertEqual(self.f.latest(),original)
        self.assertEqual(self.f.sync()['state'],'verified')

    def test_equal_sequence_different_source_branch_is_not_verified_or_reused(self):
        path = self.f.f.path('divergent.sqlite')
        with closing(sqlite3.connect(self.f.m.path)) as source,closing(sqlite3.connect(path)) as target:
            source.backup(target)
        branch = SyntheticMemory(path,synthetic_only=True,clock=self.f.m.clock)
        packet = dict(op='correct',project='alpha',request_id=self.f.f.f.rid(),
                      id=self.f.f.kept['id'],expected_revision=1,value={'text':'SYNTHETIC_BRANCH_A'})
        self.f.f.f.call(packet)
        self.f.sync();original = self.f.latest()
        branch.handle(self.f.f.f.f.laptop(),dict(packet,value={'text':'SYNTHETIC_BRANCH_B'}),approved=True)
        self.assertEqual(self.f.repo.status(branch,self.f.r)['state'],'diverged')
        with self.assertRaises(Conflict):self.f.repo.sync(branch,self.f.r,approved=True)
        self.assertEqual(self.f.latest(),original)

    def test_nonfinite_clock_cannot_commit_records(self):
        before = self.f.f.f.counts()
        for invalid in (float('nan'),float('inf'),-1,True,10**1000):
            self.f.m.clock = lambda value=invalid:value
            with self.assertRaises(ValueError):self.f.f.f.call(self.f.f.f.save_packet(key='bad clock'))
            self.assertEqual(self.f.f.f.counts(),before)
        self.f.m.clock = lambda:self.f.f.f.now
        for invalid in (float('nan'),float('inf'),-1,True,10**1000):
            packet = self.f.f.f.save_packet(retention={'mode':'until','expires_at':invalid})
            with self.assertRaises(ValueError):self.f.f.f.call(packet)
            self.assertEqual(self.f.f.f.counts(),before)

    def test_authenticated_wrong_json_field_types_are_validation_errors(self):
        backup = self.f.f.backup()
        original,_ = self.f.r._open(backup,BACKUP_MAGIC)
        for field in ('value','result'):
            data = copy.deepcopy(original)
            if field == 'value':data['records'][0]['value'] = None
            else:data['requests'][0]['result'] = []
            with self.assertRaises(ValueError):self.f.r._validate_backup(data)

    def test_old_catalogue_schema_is_refused_without_migration(self):
        self.f.sync()
        with self.f.repo._db() as db:db.execute('PRAGMA user_version=1')
        original = self.f.repo.catalog.read_bytes()
        with self.assertRaises(ValueError):SyntheticRepository(self.f.root,synthetic_only=True)
        self.assertEqual(self.f.repo.catalog.read_bytes(),original)


if __name__ == '__main__':unittest.main()
