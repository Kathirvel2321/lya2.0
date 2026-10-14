"""SQLCipher qualification with generated keys and disposable fake records only."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import types
import unittest
from unittest.mock import patch

from brain import memory_prototype as memory
from brain import memory_recovery as recovery
from brain.memory_repository import SyntheticRepository
import test_memory_prototype as fixtures

try:from sqlcipher3 import dbapi2 as cipher
except ImportError:cipher = None


@unittest.skipIf(cipher is None,'Run the isolated SQLCipher qualification runner.')
class EncryptedChecks(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.MemoryChecks(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.key = os.urandom(32)
        self.f.path = self.f.path.with_name('encrypted.sqlite')
        self.f.m = memory.SyntheticMemory(self.f.path,synthetic_only=True,encryption_key=self.key,
                                          clock=lambda:self.f.now)
        self.f.owner = self.f.m.create_owner(self.f.f.binding)
        self.r = recovery.SyntheticRecovery(recovery.SyntheticRecovery.new_key(),synthetic_only=True,
                                            clock=lambda:self.f.now)
        self.repo = SyntheticRepository(self.f.path.parent/'fake-repository',synthetic_only=True)

    def assert_ciphertext(self, path, *markers):
        data = path.read_bytes()
        self.assertNotIn(b'SQLite format 3',data)
        self.assertNotIn(self.key,data)
        for marker in markers:self.assertNotIn(marker.encode(),data)

    def test_shared_semantics_restart_correction_retry_forget_and_expiry(self):
        packet = self.f.save_packet(key='தமிழ்',value='SYNTHETIC_ENCRYPTED_TAMIL')
        first = self.f.call(packet)
        self.f.m = memory.SyntheticMemory(self.f.path,synthetic_only=True,encryption_key=self.key,
                                          clock=lambda:self.f.now)
        self.assertEqual(self.f.get(first['id'],phone=True)['value'],packet['value'])
        self.assertEqual(self.f.search('SYNTHETIC_ENCRYPTED_TAMIL')[0]['id'],first['id'])
        correction = dict(op='correct',project='alpha',request_id=self.f.rid(),id=first['id'],
                          expected_revision=1,value={'text':'SYNTHETIC_ENCRYPTED_CORRECTION'})
        changed = self.f.call(correction,phone=True)
        self.assertEqual(self.f.call(correction),changed)
        self.assertEqual(self.f.search('SYNTHETIC_ENCRYPTED_TAMIL'),[])
        self.f.call(dict(op='forget',project='alpha',request_id=self.f.rid(),id=first['id'],expected_revision=2))
        self.assertIsNone(self.f.get(first['id']))
        self.assertEqual(self.f.call(packet),first)
        timed = self.f.call(self.f.save_packet(key='timed',retention={'mode':'until','expires_at':self.f.now+1}))
        self.f.now += 1
        self.assertIsNone(self.f.get(timed['id']))
        self.assert_ciphertext(self.f.path,'SYNTHETIC_ENCRYPTED_TAMIL','SYNTHETIC_ENCRYPTED_CORRECTION')
        with self.f.m._db() as db:
            self.assertEqual(db.execute('PRAGMA cipher_integrity_check').fetchall(),[])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA temp_store').fetchone()[0],2)

    def test_wrong_missing_and_malformed_keys_preserve_existing_bytes(self):
        self.f.call(self.f.save_packet(value='SYNTHETIC_KEY_CHECK'))
        original = self.f.path.read_bytes()
        for key in (None,os.urandom(32)):
            with self.assertRaises((sqlite3.DatabaseError,cipher.DatabaseError,ValueError)):
                memory.SyntheticMemory(self.f.path,synthetic_only=True,encryption_key=key)
            self.assertEqual(self.f.path.read_bytes(),original)
        for key in (b'',b'short','password',True):
            path = self.f.path.with_name('invalid-key.sqlite')
            with self.assertRaises(ValueError):memory.SyntheticMemory(path,synthetic_only=True,encryption_key=key)
            self.assertFalse(path.exists())
        self.assertEqual(self.f.get(self.f.search('SYNTHETIC_KEY_CHECK')[0]['id'])['revision'],1)

    def test_absent_or_plaintext_driver_never_falls_back(self):
        import builtins
        original = builtins.__import__
        def unavailable(name,*args,**kwargs):
            if name == 'sqlcipher3':raise ImportError('synthetic missing driver')
            return original(name,*args,**kwargs)
        path = self.f.path.with_name('no-driver.sqlite')
        with patch('builtins.__import__',side_effect=unavailable):
            with self.assertRaises(RuntimeError):memory.SyntheticMemory(path,synthetic_only=True,encryption_key=self.key)
        self.assertFalse(path.exists())
        with patch.dict(sys.modules,{'sqlcipher3':types.SimpleNamespace(dbapi2=sqlite3)}):
            with self.assertRaises(ValueError):memory.SyntheticMemory(path,synthetic_only=True,encryption_key=self.key)
        if path.exists():self.assertEqual(path.stat().st_size,0)

    def test_plaintext_store_is_not_implicitly_migrated_or_modified(self):
        path = self.f.path.with_name('unrelated-plain.sqlite')
        plain = memory.SyntheticMemory(path,synthetic_only=True)
        plain.create_owner('b'*64)
        original = path.read_bytes()
        with self.assertRaises(cipher.DatabaseError):memory.SyntheticMemory(path,synthetic_only=True,encryption_key=self.key)
        self.assertEqual(path.read_bytes(),original)

    def test_corrupt_or_truncated_pages_cannot_be_acknowledged(self):
        for i in range(12):self.f.call(self.f.save_packet(key=f'large-{i}',value='SYNTHETIC_PAGE_'+'x'*3000))
        original = self.f.path.read_bytes()
        altered = bytearray(original);altered[len(altered)//2] ^= 1
        for index,data in enumerate((original[:-17],bytes(altered))):
            path = self.f.path.with_name(f'damaged-{index}.sqlite');path.write_bytes(data)
            target = self.f.path.with_name(f'damaged-{index}.enc')
            with self.assertRaises((cipher.DatabaseError,ValueError)):
                damaged = memory.SyntheticMemory(path,synthetic_only=True,encryption_key=self.key)
                self.r.backup(damaged,target,approved=True)
            self.assertFalse(target.exists())
            self.assertEqual(path.read_bytes(),data)

    def test_active_rollback_journal_has_no_plaintext_and_rollback_keeps_old_value(self):
        receipt = self.f.call(self.f.save_packet(value='SYNTHETIC_OLD_JOURNAL'))
        with self.assertRaises(RuntimeError):
            with self.f.m._db() as db:
                db.execute('UPDATE memories SET value=? WHERE id=?',('{"text":"SYNTHETIC_NEW_JOURNAL"}',receipt['id']))
                journal = Path(str(self.f.path)+'-journal')
                self.assertTrue(journal.exists())
                self.assert_ciphertext(journal,'SYNTHETIC_OLD_JOURNAL','SYNTHETIC_NEW_JOURNAL')
                raise RuntimeError('synthetic interrupted transaction')
        self.assertEqual(self.f.get(receipt['id'])['value']['text'],'SYNTHETIC_OLD_JOURNAL')

    def test_live_wal_snapshot_and_restore_are_encrypted_including_staging(self):
        reader = self.f.m._connect();self.addCleanup(reader.close)
        self.assertEqual(reader.execute('PRAGMA journal_mode=WAL').fetchone()[0],'wal')
        reader.execute('BEGIN');reader.execute('SELECT count(*) FROM memories').fetchone()
        receipt = self.f.call(self.f.save_packet(value='SYNTHETIC_ENCRYPTED_WAL'))
        wal = Path(str(self.f.path)+'-wal')
        self.assertTrue(wal.exists());self.assert_ciphertext(wal,'SYNTHETIC_ENCRYPTED_WAL')
        self.assertEqual(self.repo.sync(self.f.m,self.r,approved=True)['state'],'verified')
        destination = self.f.path.with_name('restored.enc.sqlite')
        lineage,sequence = self.repo._state(self.f.m)
        original = recovery._publish
        inspected = []
        def inspect(path,writer,cancelled):
            def checked(stage):
                writer(stage)
                self.assert_ciphertext(stage,'SYNTHETIC_ENCRYPTED_WAL')
                inspected.append(True)
            return original(path,checked,cancelled)
        with patch.object(recovery,'_publish',side_effect=inspect):
            result = self.repo.restore(lineage,self.r,destination,required_sequence=sequence,
                                       approved=True,storage_key=self.key)
        self.assertEqual(inspected,[True]);self.assertEqual(result['preserved'],1)
        self.assertEqual((result['active_bindings'],result['resumed_jobs']),(0,0))
        self.assert_ciphertext(destination,'SYNTHETIC_ENCRYPTED_WAL')
        restored = memory.SyntheticMemory(destination,synthetic_only=True,encryption_key=self.key)
        with restored._db() as db:
            row = db.execute('SELECT id,value FROM memories').fetchone()
            self.assertEqual(row['id'],receipt['id']);self.assertIn('SYNTHETIC_ENCRYPTED_WAL',row['value'])

    def test_cancel_and_sqlite_full_roll_back_all_projections(self):
        before = self.f.counts();turn = self.f.f.laptop();enqueue = self.f.m._enqueue
        def cancel(*args):enqueue(*args);turn._cancelled.set()
        with patch.object(self.f.m,'_enqueue',side_effect=cancel):
            with self.assertRaises(InterruptedError):self.f.call(self.f.save_packet(),turn=turn)
        self.assertEqual(self.f.counts(),before)
        with self.f.m._db() as db:pages = db.execute('PRAGMA page_count').fetchone()[0]
        failed = False
        with patch.object(memory,'MAX_PAGES',pages):
            for i in range(30):
                before = self.f.counts()
                try:self.f.call(self.f.save_packet(key=f'full-{i}',value='SYNTHETIC_FULL'+'x'*3000))
                except cipher.OperationalError as error:
                    self.assertIn('full',str(error).lower())
                    self.assertEqual(self.f.counts(),before);failed = True;break
        self.assertTrue(failed)

    def test_two_device_corrections_have_one_winner(self):
        first = self.f.call(self.f.save_packet());barrier = threading.Barrier(2);outcomes = []
        def run(turn,packet):
            barrier.wait(3)
            try:outcomes.append(self.f.m.handle(turn,packet,approved=True)['revision'])
            except memory.Conflict:outcomes.append('conflict')
        threads = []
        for turn,text in ((self.f.f.laptop(),'laptop'),(self.f.f.phone_turn(),'phone')):
            packet = dict(op='correct',project='alpha',request_id=self.f.rid(),id=first['id'],
                          expected_revision=1,value={'text':text})
            threads.append(threading.Thread(target=run,args=(turn,packet)))
        for thread in threads:thread.start()
        for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
        self.assertCountEqual(outcomes,[2,'conflict'])
        self.assertEqual(self.f.get(first['id'])['revision'],2)

    def test_child_process_death_before_commit_and_lost_reply_retry(self):
        program = '''
from contextlib import contextmanager
import os,sys,threading,time
from brain.conversation import Context,PublicTurn
from brain.memory_prototype import SyntheticMemory
path,binding,key,mode = sys.argv[1:]
memory = SyntheticMemory(path,synthetic_only=True,encryption_key=bytes.fromhex(key),clock=lambda:2000000000.)
context = Context(binding,'laptop','a'*64,binding,4102444800.,True)
turn = PublicTurn('f'*32,'SYNTHETIC_QUESTION',context,time.monotonic()+30,lambda:context,lambda:2000000000.,threading.Event())
original = memory._db
@contextmanager
def die(*args,**kwargs):
    with original(*args,**kwargs) as db:
        yield db
        os._exit(17)
if mode == 'before':memory._db = die
packet = dict(op='save',project='alpha',request_id=('d' if mode=='before' else 'e')*32,kind='fact',
              key='crash fixture',value={'text':'SYNTHETIC_SQLCIPHER_CRASH'},retention={'mode':'permanent'})
memory.handle(turn,packet,approved=True)
os._exit(18)
'''
        env = dict(os.environ)
        env['PYTHONPATH'] = str(Path(cipher.__file__).resolve().parents[1])
        before = self.f.counts()
        for mode,code in (('before',17),('after',18)):
            run = subprocess.run([sys.executable,'-c',program,str(self.f.path),self.f.f.binding,self.key.hex(),mode],
                                 cwd=Path(__file__).resolve().parent,env=env,capture_output=True,text=True,timeout=15,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(run.returncode,code,run.stderr)
            if mode == 'before':self.assertEqual(self.f.counts(),before)
        packet = dict(op='save',project='alpha',request_id='e'*32,kind='fact',key='crash fixture',
                      value={'text':'SYNTHETIC_SQLCIPHER_CRASH'},retention={'mode':'permanent'})
        first = self.f.call(packet)
        self.assertEqual(self.f.call(packet,phone=True),first)
        self.assertEqual(self.f.counts()['memories'],1)
        self.assert_ciphertext(self.f.path,'SYNTHETIC_SQLCIPHER_CRASH')


if __name__ == '__main__':unittest.main()
