"""Portable storage tests with direct synthetic authority; no native identity claim."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from sqlcipher3 import dbapi2 as cipher
from brain.conversation import Context,PublicTurn
from brain.memory_prototype import Conflict,SyntheticMemory
from brain.memory_recovery import SyntheticRecovery
from brain.memory_authority import SyntheticAuthority


class StorageChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.home = Path(temp.name);self.key = os.urandom(32);self.now = 2000000000.
        self.memory = SyntheticMemory(self.home/'memory.sqlite',synthetic_only=True,encryption_key=self.key,clock=lambda:self.now)
        self.owner = self.memory.create_owner('1'*64)
        self.recovery = SyntheticRecovery(SyntheticRecovery.new_key(),synthetic_only=True,clock=lambda:self.now)

    def turn(self, *, principal='1'*64, verified=True):
        context = Context(principal,'phone','2'*64,principal,self.now+300,verified)
        return PublicTurn('3'*32,'SYNTHETIC_LINUX',context,time.monotonic()+30,lambda:context,lambda:self.now,threading.Event())

    def packet(self, key='fake', **kwargs):
        return dict(op='save',project='alpha',request_id=os.urandom(16).hex(),kind='fact',key=key,
                    value={'text':'SYNTHETIC_LINUX_VALUE'},retention={'mode':'permanent'},**kwargs)

    def call(self, packet, **kwargs):return self.memory.handle(self.turn(),packet,approved=True,**kwargs)

    def ciphertext(self, path):
        data = Path(path).read_bytes()
        for marker in (b'SQLite format 3',b'SYNTHETIC_LINUX_VALUE',self.key):self.assertNotIn(marker,data)

    def authority(self):
        self.a = SyntheticAuthority(self.home/'authority',recovery=self.recovery,storage_key=self.key,
                                    synthetic_only=True,clock=lambda:self.now)
        self.anchor = self.a.register(self.memory,approved=True)
        self.grant = self.a.acquire(self.anchor.lineage,'a'*32,expected_epoch=0,approved=True)

    def request(self, packet, **kwargs):
        result = self.a.handle(self.grant,self.turn(),packet,expected_anchor=self.anchor,approved=True,**kwargs)
        self.anchor = result['anchor'];return result['result']

    def test_engine_encryption_wrong_keys_and_plaintext_driver_rejection(self):
        self.call(self.packet());self.ciphertext(self.memory.path)
        with self.memory._db() as db:
            self.assertEqual(str(db.execute('PRAGMA cipher_status').fetchone()[0]),'1')
            self.assertEqual(str(db.execute('PRAGMA cipher_use_hmac').fetchone()[0]),'1')
            self.assertEqual(str(db.execute('PRAGMA cipher_plaintext_header_size').fetchone()[0]),'0')
            self.assertEqual(db.execute('PRAGMA cipher_integrity_check').fetchall(),[])
        before = self.memory.path.read_bytes()
        for key in (None,os.urandom(32)):
            with self.assertRaises((sqlite3.DatabaseError,cipher.DatabaseError,ValueError)):
                SyntheticMemory(self.memory.path,synthetic_only=True,encryption_key=key)
            self.assertEqual(self.memory.path.read_bytes(),before)
        with patch.dict(sys.modules,{'sqlcipher3':type('FakeDriver',(),{'dbapi2':sqlite3})}):
            with self.assertRaises(ValueError):
                SyntheticMemory(self.home/'wrong-driver.sqlite',synthetic_only=True,encryption_key=self.key)

    def test_correction_retry_unicode_forget_expiry_and_owner_scope(self):
        packet = self.packet('தமிழ்');first = self.call(packet);self.assertEqual(self.call(packet),first)
        correction = dict(op='correct',project='alpha',request_id=os.urandom(16).hex(),id=first['id'],
                          expected_revision=1,value={'text':'SYNTHETIC_CORRECTED'})
        self.assertEqual(self.call(correction)['revision'],2)
        self.assertEqual(self.call(correction)['revision'],2)
        with self.assertRaises(PermissionError):
            self.memory.handle(self.turn(principal='4'*64),dict(op='get',project='alpha',id=first['id']),approved=True)
        self.call(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=first['id'],expected_revision=2))
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=first['id']))['record'])
        timed = self.packet('timed');timed['retention']={'mode':'until','expires_at':self.now+1}
        saved = self.call(timed);self.now += 2
        self.assertIsNone(self.call(dict(op='get',project='alpha',id=saved['id']))['record'])

    def test_wal_rollback_journal_and_encrypted_restore_staging(self):
        with closing(self.memory._connect()) as writer:
            writer.execute('BEGIN IMMEDIATE')
            writer.execute('UPDATE bindings SET active=0');journal = Path(str(self.memory.path)+'-journal')
            self.assertTrue(journal.exists());self.ciphertext(journal)
            writer.rollback()
        with closing(self.memory._connect()) as reader:
            self.assertEqual(reader.execute('PRAGMA journal_mode=WAL').fetchone()[0],'wal')
            reader.execute('BEGIN');reader.execute('SELECT count(*) FROM memories').fetchone()
            self.call(self.packet());self.ciphertext(str(self.memory.path)+'-wal')
            anchor = self.recovery.bundle(self.memory,self.home/'backup.enc',self.home/'checkpoint.enc',approved=True)
        import brain.memory_recovery as recovery_module
        original = recovery_module._publish;stages = []
        def inspect(path,writer,cancelled):
            def write(stage):writer(stage);self.ciphertext(stage);stages.append(True)
            return original(path,write,cancelled)
        with patch.object(recovery_module,'_publish',side_effect=inspect):
            result = self.recovery.restore(self.home/'backup.enc',self.home/'checkpoint.enc',self.home/'restored.sqlite',
                trusted_anchor=anchor,approved=True,storage_key=self.key)
        self.assertEqual(stages,[True]);self.assertEqual((result['active_bindings'],result['resumed_jobs']),(0,0))

    def test_corrupt_and_truncated_database_are_not_accepted(self):
        self.call(self.packet());original = self.memory.path.read_bytes()
        for data in (original[:len(original)//2],bytes([original[0]^1])+original[1:]):
            path = self.home/'damaged.sqlite';path.write_bytes(data)
            with self.assertRaises((cipher.DatabaseError,ValueError)):
                SyntheticMemory(path,synthetic_only=True,encryption_key=self.key)
        self.assertEqual(self.memory.path.read_bytes(),original)

    def test_cancellation_and_full_database_rollback(self):
        turn = self.turn();enqueue = self.memory._enqueue
        def cancel(*args):enqueue(*args);turn._cancelled.set()
        with patch.object(self.memory,'_enqueue',side_effect=cancel):
            with self.assertRaises(InterruptedError):self.memory.handle(turn,self.packet(),approved=True)
        with self.memory._db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memories').fetchone()[0],0)
            pages = db.execute('PRAGMA page_count').fetchone()[0]
        failed = False
        with patch('brain.memory_prototype.MAX_PAGES',pages):
            for i in range(40):
                with self.memory._db() as db:before = db.execute('SELECT count(*) FROM memories').fetchone()[0]
                packet = self.packet(str(i));packet['value']={'text':'x'*3000}
                try:self.call(packet)
                except cipher.OperationalError as error:
                    self.assertIn('full',str(error).lower());failed = True
                    with self.memory._db() as db:self.assertEqual(db.execute('SELECT count(*) FROM memories').fetchone()[0],before)
                    break
        self.assertTrue(failed)

    def test_authority_fencing_conflicts_failed_publication_and_reactivation(self):
        initial = self.call(self.packet());self.authority();old = self.grant
        self.grant = self.a.acquire(self.anchor.lineage,'b'*32,expected_epoch=1,approved=True)
        with self.assertRaises(PermissionError):self.a.handle(old,self.turn(),self.packet('old'),expected_anchor=self.anchor,approved=True)
        anchor = self.anchor;packet = self.packet('new');self.request(packet)
        with self.assertRaises(Conflict):self.a.handle(self.grant,self.turn(),self.packet('stale'),expected_anchor=anchor,approved=True)
        head = self.a.head(self.anchor.lineage)
        with patch.object(self.recovery,'bundle',side_effect=OSError('Synthetic unavailable storage')):
            with self.assertRaises(OSError):self.request(self.packet('failure'))
        self.assertEqual(self.a.head(self.anchor.lineage),head)
        self.request(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=initial['id'],expected_revision=1))
        old = self.grant;destination = self.home/'quarantine.sqlite'
        restored = self.a.restore(self.anchor.lineage,destination,expected_anchor=self.anchor,approved=True)
        with self.assertRaises(Conflict):self.a.acquire(self.anchor.lineage,'c'*32,expected_epoch=restored['writer_epoch'],approved=True)
        result = self.a.activate_restored(self.anchor.lineage,destination,self.turn(),'c'*32,
            expected_anchor=self.anchor,expected_epoch=restored['writer_epoch'],approved=True)
        self.grant,self.anchor = result['grant'],result['anchor']
        with self.assertRaises(PermissionError):self.a.handle(old,self.turn(),self.packet('old2'),expected_anchor=self.anchor,approved=True)
        self.assertIsNone(self.request(dict(op='get',project='alpha',id=initial['id']))['record'])
        self.assertEqual((result['active_bindings'],result['resumed_jobs']),(1,0))

    def test_child_death_before_commit_and_lost_reply_after_commit(self):
        program = r'''
import json,os,sys,threading,time
from contextlib import contextmanager
p=json.load(sys.stdin);sys.path[:0]=p['imports']
from brain.memory_prototype import SyntheticMemory
from brain.conversation import Context,PublicTurn
m=SyntheticMemory(p['path'],synthetic_only=True,encryption_key=bytes.fromhex(p['key']))
c=Context('1'*64,'phone','2'*64,'1'*64,4102444800.,True)
t=PublicTurn('3'*32,'SYNTHETIC_CRASH',c,time.monotonic()+30,lambda:c,time.time,threading.Event())
original=m._db
@contextmanager
def die(*args,**kwargs):
    with original(*args,**kwargs) as db:
        yield db
        os._exit(17)
if p['mode']=='before':m._db=die
m.handle(t,p['packet'],approved=True);os._exit(18)
'''
        imports = [str(Path(cipher.__file__).resolve().parents[1]),
                   str(Path(sys.modules[SyntheticMemory.__module__].__file__).resolve().parents[1])]
        for mode,code in (('before',17),('after',18)):
            packet = self.packet(mode)
            run = subprocess.run([sys.executable,'-I','-B','-c',program],input=json.dumps(dict(imports=imports,
                path=str(self.memory.path),key=self.key.hex(),packet=packet,mode=mode)),capture_output=True,text=True,timeout=20,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,code,'Synthetic crash child failed; raw output withheld.')
            with self.memory._db() as db:self.assertEqual(db.execute('SELECT count(*) FROM memories').fetchone()[0],0 if mode=='before' else 1)
            if mode=='after':self.assertEqual(self.call(packet),self.call(packet))

    def test_thousand_record_corpus_and_quarantined_restore(self):
        receipts = [self.call(self.packet(str(i))) for i in range(1000)]
        for row in receipts[:60]:self.call(dict(op='forget',project='alpha',request_id=os.urandom(16).hex(),id=row['id'],expected_revision=1))
        anchor = self.recovery.bundle(self.memory,self.home/'corpus.enc',self.home/'corpus-checkpoint.enc',approved=True)
        result = self.recovery.restore(self.home/'corpus.enc',self.home/'corpus-checkpoint.enc',self.home/'corpus-restored.sqlite',
            trusted_anchor=anchor,approved=True,storage_key=self.key)
        self.assertEqual((result['preserved'],result['suppressed_deleted'],result['active_bindings'],result['resumed_jobs']),(940,60,0,0))
        restored = SyntheticMemory(self.home/'corpus-restored.sqlite',synthetic_only=True,encryption_key=self.key)
        with restored._db() as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__':unittest.main()
