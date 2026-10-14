"""Disposable FAKE-DATA recovery acknowledgements; no independent service or fencing.

The catalogue is a plaintext trusted fixture, not rollback-resistant authority.
Live memory can use the explicit SQLCipher candidate. Keys are supplied in memory.
"""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import uuid

from brain.memory_prototype import Conflict, SyntheticMemory, _id, _unlinked
from brain.memory_recovery import CheckpointAnchor, SyntheticRecovery, HEAD_FIELDS, _integer, _read

APPLICATION_ID = 0x4C594152


class SyntheticRepository:
    def __init__(self, path, *, synthetic_only=False):
        if synthetic_only is not True:raise PermissionError('Fake-data recovery opt-in required.')
        self.path = Path(path).absolute()
        self.catalog = self.path/'catalog.sqlite'
        self._unlinked(self.path)
        if self.path.exists() and not self.catalog.exists():
            raise ValueError('Recovery catalogue missing; freshness state must not be recreated.')
        self.path.mkdir(exist_ok=True)
        self._unlinked(self.path/'objects')
        (self.path/'objects').mkdir(exist_ok=True)
        with self._db(initializing=not self.catalog.exists()) as db:
            if db.execute('PRAGMA application_id').fetchone()[0] == 0:
                db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                db.execute('PRAGMA user_version=2')
                db.execute('''CREATE TABLE latest(lineage TEXT PRIMARY KEY, sequence INTEGER NOT NULL,
                    checkpoint_id TEXT NOT NULL, sha256 TEXT NOT NULL, backup_sha256 TEXT NOT NULL,
                    object_id TEXT NOT NULL, key_sha256 TEXT NOT NULL)''')

    @staticmethod
    def _unlinked(path):
        _unlinked(path)

    @contextmanager
    def _db(self, initializing=False):
        self._unlinked(self.catalog)
        db = sqlite3.connect(self.catalog if initializing else self.catalog.as_uri()+'?mode=rw',
                             uri=not initializing,timeout=3)
        try:
            db.row_factory = sqlite3.Row
            if not initializing and (db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                                    or db.execute('PRAGMA user_version').fetchone()[0] != 2):
                raise ValueError('Wrong recovery catalogue.')
            db.execute('PRAGMA synchronous=FULL')
            # shortcut: one catalogue writer; qualify off-host durability and writer fencing before live use.
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:db.close()

    @staticmethod
    def _state(memory):
        if type(memory) is not SyntheticMemory:raise ValueError('Synthetic store required.')
        with memory._db() as db:
            row = db.execute('SELECT lineage,sequence FROM store_meta WHERE id=1').fetchone()
            if not row:raise ValueError('Missing memory state.')
            return _id(row['lineage']),_integer(row['sequence'])

    def _verify(self, row, recovery):
        if type(recovery) is not SyntheticRecovery:raise ValueError('Synthetic recovery required.')
        if row['key_sha256'] != recovery.key_id:raise ValueError('Wrong acknowledged recovery key.')
        anchor = CheckpointAnchor(_id(row['lineage']),_integer(row['sequence']),
                                  _id(row['checkpoint_id']),_id(row['sha256'],64))
        folder = self.path/'objects'/_id(row['object_id'])
        self._unlinked(folder)
        backup,checkpoint = folder/'backup.enc',folder/'checkpoint.enc'
        saved,current,records,heads,_ = recovery._restore_inputs(
            backup,checkpoint,anchor,backup_sha256=_id(row['backup_sha256'],64))
        if (saved['sequence'] != current['sequence'] or saved['owners'] != current['owners']
                or set(records) != set(heads)
                or any(any(row[key] != heads[mid][key] for key in HEAD_FIELDS) for mid,row in records.items())):
            raise ValueError('Acknowledgement requires a complete matching snapshot.')
        return anchor,backup,checkpoint,saved,current

    @staticmethod
    def _same_snapshot(source, saved, current):
        snapshot = {key:saved[key] for key in ('lineage','sequence','owners','records','requests')}
        snapshot['deletions'] = current['deletions']
        return source == snapshot

    def sync(self, memory, recovery, *, approved=False, cancelled=lambda:False):
        """Acknowledge only after publishing, reading back and committing both files."""
        if approved is not True:raise PermissionError('Trusted recovery approval required.')
        if type(recovery) is not SyntheticRecovery:raise ValueError('Synthetic recovery required.')
        if cancelled():raise InterruptedError('Recovery cancelled.')
        with self._db() as db:
            source = recovery._capture(memory)
            lineage,sequence = _id(source['lineage']),_integer(source['sequence'])
            old = db.execute('SELECT * FROM latest WHERE lineage=?',(lineage,)).fetchone()
            if old and old['key_sha256'] != recovery.key_id:
                raise PermissionError('Recovery key rotation is not authorized by synchronization.')
            if old and old['sequence'] > sequence:raise Conflict('Source is behind the acknowledged state.')
            valid = False
            if old and old['sequence'] == sequence:
                try:
                    *_,saved,current = self._verify(old,recovery)
                    valid = True
                except (OSError,ValueError):pass
                if valid and not self._same_snapshot(source,saved,current):
                    raise Conflict('Different source state at the same sequence; writer fencing required.')
            if not valid:
                object_id = uuid.uuid4().hex
                folder = self.path/'objects'/object_id
                self._unlinked(folder)
                folder.mkdir()
                anchor = recovery.bundle(memory,folder/'backup.enc',folder/'checkpoint.enc',
                                         approved=True,cancelled=cancelled)
                if anchor.lineage != lineage or anchor.sequence < sequence:
                    raise Conflict('Memory state moved backwards during capture.')
                row = dict(lineage=lineage,sequence=anchor.sequence,checkpoint_id=anchor.checkpoint_id,
                           sha256=anchor.sha256,backup_sha256=hashlib.sha256(_read(folder/'backup.enc')).hexdigest(),
                           object_id=object_id,key_sha256=recovery.key_id)
                self._verify(row,recovery)
                db.execute('INSERT OR REPLACE INTO latest VALUES(?,?,?,?,?,?,?)',tuple(row.values()))
            if cancelled():raise InterruptedError('Recovery cancelled.')
        return self.status(memory,recovery)

    def status(self, memory, recovery):
        """Content-free status as of the observed memory sequence; never a live-safety claim."""
        source = recovery._capture(memory)
        lineage,sequence = _id(source['lineage']),_integer(source['sequence'])
        with self._db() as db:
            row = db.execute('SELECT * FROM latest WHERE lineage=?',(lineage,)).fetchone()
            acknowledged = row['sequence'] if row else None
            state = 'pending'
            if row:
                try:
                    *_,saved,current = self._verify(row,recovery)
                    state = 'verified' if acknowledged == sequence else 'source_behind' if acknowledged > sequence else 'pending'
                    if state == 'verified' and not self._same_snapshot(source,saved,current):state = 'diverged'
                except (OSError,ValueError):state = 'unavailable'
        return dict(state=state,memory_sequence=sequence,acknowledged_sequence=acknowledged,
                    current_snapshot_verified=state == 'verified',synthetic_only=True)

    def restore(self, lineage, recovery, destination, *, required_sequence, approved=False,
                cancelled=lambda:False, storage_key=None):
        if approved is not True:raise PermissionError('Trusted restore approval required.')
        _id(lineage);_integer(required_sequence)
        # Hold the catalogue transaction so another publisher cannot supersede this anchor mid-restore.
        with self._db() as db:
            row = db.execute('SELECT * FROM latest WHERE lineage=?',(lineage,)).fetchone()
            if not row:raise ValueError('No acknowledged recovery state.')
            if row['sequence'] != required_sequence:
                raise Conflict('Acknowledgement does not cover the independently required state.')
            anchor,backup,checkpoint,_,_ = self._verify(row,recovery)
            return recovery.restore(backup,checkpoint,destination,trusted_anchor=anchor,
                                    approved=True,cancelled=cancelled,trusted_backup_sha256=row['backup_sha256'],
                                    storage_key=storage_key)
