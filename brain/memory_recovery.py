"""Encrypted recovery qualification for disposable FAKE-DATA stores only.

The live/staged database remains plaintext. No real key custody, independent
storage, approval workflow, account recovery or production cutover is enabled.
"""
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
import uuid

from cryptography.fernet import Fernet, InvalidToken
from brain.memory_prototype import SyntheticMemory, APPLICATION_ID, SCHEMA_VERSION, MAX_RECORDS, MAX_REQUESTS, _id, _json, _validate

MAX_RAW = 64 * 1024 * 1024
MAX_BLOB = MAX_RAW * 2
BACKUP_MAGIC = b'LYA-FAKE-BACKUP-1\n'
CHECKPOINT_MAGIC = b'LYA-FAKE-CHECKPOINT-1\n'
RECORD_FIELDS = ('id','owner','project','kind','key','normkey','value','retention','expires_at',
                 'revision','recorded_at','updated_at','source_request','deleted')
HEAD_FIELDS = ('id','owner','project','revision','deleted','expires_at','updated_at')
DELETE_FIELDS = ('owner','project','memory_id','revision','deleted_at','reason')


@dataclass(frozen=True)
class CheckpointAnchor:
    """Caller must supply the latest independently trusted anchor, not one from backup."""
    lineage: str
    sequence: int
    checkpoint_id: str
    sha256: str


def _number(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid recovery time.')
    return value


def _integer(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 2**63-1:
        raise ValueError('Invalid recovery counter.')
    return value


def _project(value):
    if type(value) is not str or not re.fullmatch('[a-z0-9_-]{1,64}', value):
        raise ValueError('Invalid recovery scope.')


def _unique(pairs):
    value = {}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate recovery field.')
        value[key] = item
    return value


def _read(path):
    path = Path(path)
    if path.is_symlink():raise ValueError('No linked recovery input.')
    with path.open('rb') as source:data = source.read(MAX_BLOB+1)
    if len(data) > MAX_BLOB:raise ValueError('Recovery input too large.')
    return data


def _publish(path, writer, cancelled):
    """Same-volume atomic create, never replace an existing file."""
    path = Path(path).absolute()
    if path.exists() or path.is_symlink() or path.parent.is_symlink():
        raise FileExistsError('Recovery output must be new and unlinked.')
    with tempfile.TemporaryDirectory(prefix='.lya-fake-recovery-', dir=path.parent) as folder:
        stage = Path(folder)/'staged'
        writer(stage)
        with stage.open('r+b') as source:os.fsync(source.fileno())
        if cancelled():raise InterruptedError('Recovery cancelled.')
        # shortcut: no portable directory fsync; qualify power-loss durability before live use.
        os.link(stage,path)


def _metadata(data, fields):
    if type(data) is not dict or set(data) != fields:raise ValueError('Unexpected recovery fields.')
    _id(data['lineage']);_integer(data['sequence'])
    _number(data['created_at'])
    if type(data['owners']) is not list or len(data['owners']) > MAX_RECORDS:
        raise ValueError('Invalid owner count.')
    owners = {_id(owner) for owner in data['owners']}
    if len(owners) != len(data['owners']):raise ValueError('Duplicate owners.')
    return owners


def _heads(rows, owners, *, records=False):
    if type(rows) is not list or len(rows) > MAX_RECORDS:raise ValueError('Invalid record count.')
    result = {}
    for row in rows:
        if type(row) is not dict or set(row) != set(RECORD_FIELDS if records else HEAD_FIELDS):
            raise ValueError('Unexpected record fields.')
        mid = _id(row['id']);_id(row['owner']);_project(row['project'])
        if mid in result or row['owner'] not in owners:raise ValueError('Duplicate or unowned record.')
        _integer(row['revision'],1);_number(row['updated_at'])
        if type(row['deleted']) is not int or row['deleted'] not in (0,1):raise ValueError('Invalid deletion state.')
        if row['expires_at'] is not None:_number(row['expires_at'])
        if row['deleted'] and row['expires_at'] is not None:raise ValueError('Invalid tombstone expiry.')
        if records:
            _number(row['recorded_at'])
            if row['deleted']:
                if any(row[k] != '' for k in ('kind','key','normkey','retention','source_request')) or row['value'] is not None:
                    raise ValueError('Tombstone contains content.')
            else:
                retention = {'mode':row['retention']}
                if row['retention'] == 'until':retention['expires_at'] = row['expires_at']
                value = json.loads(row['value'], object_pairs_hook=_unique)
                packet = dict(op='save',project=row['project'],request_id=row['source_request'],kind=row['kind'],
                              key=row['key'],value=value,retention=retention)
                _validate(packet)
                import unicodedata
                if row['normkey'] != unicodedata.normalize('NFC',row['key'].strip()).casefold():
                    raise ValueError('Invalid normalized key.')
                if (row['retention'] == 'permanent') != (row['expires_at'] is None):
                    raise ValueError('Retention/expiry mismatch.')
        result[mid] = row
    return result


class SyntheticRecovery:
    def __init__(self, recovery_key, *, synthetic_only=False, clock=time.time):
        if synthetic_only is not True:raise PermissionError('Synthetic recovery opt-in required.')
        if type(recovery_key) is not bytes:raise ValueError('A random recovery key is required.')
        try:self.cipher = Fernet(recovery_key)
        except (TypeError,ValueError):raise ValueError('Invalid recovery key.') from None
        self.clock = clock

    @staticmethod
    def new_key():
        return Fernet.generate_key()

    def _open(self, path, magic):
        blob = _read(path)
        if not blob.startswith(magic):raise ValueError('Wrong recovery format.')
        try:raw = self.cipher.decrypt(blob[len(magic):])
        except InvalidToken:raise ValueError('Recovery authentication failed.') from None
        if len(raw) > MAX_RAW:raise ValueError('Recovery payload too large.')
        return json.loads(raw, object_pairs_hook=_unique), blob

    def _seal(self, data, magic, destination, cancelled):
        raw = _json(data).encode()
        if len(raw) > MAX_RAW:raise ValueError('Recovery payload too large.')
        blob = magic + self.cipher.encrypt(raw)
        if len(blob) > MAX_BLOB:raise ValueError('Encrypted payload too large.')
        _publish(destination, lambda path:path.write_bytes(blob), cancelled)
        return blob

    @staticmethod
    def _capture(memory):
        if type(memory) is not SyntheticMemory:raise ValueError('Synthetic store required.')
        # SQLite's backup API copies a consistent snapshot, including committed WAL state.
        with closing(sqlite3.connect(memory.path.as_uri()+'?mode=ro',uri=True,timeout=3)) as source, \
                closing(sqlite3.connect(':memory:')) as db:
            source.backup(db)
            db.row_factory = sqlite3.Row
            if (db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                    or db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION
                    or db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok'
                    or db.execute('PRAGMA foreign_key_check').fetchall()):
                raise ValueError('Invalid source database.')
            meta = db.execute('SELECT lineage,sequence FROM store_meta WHERE id=1').fetchone()
            if not meta:raise ValueError('Missing recovery lineage.')
            return dict(lineage=meta['lineage'], sequence=meta['sequence'],
                        owners=[row[0] for row in db.execute('SELECT id FROM owners ORDER BY id')],
                        records=[dict(row) for row in db.execute('SELECT '+','.join(RECORD_FIELDS)+' FROM memories ORDER BY id')],
                        requests=[dict(row) for row in db.execute('SELECT * FROM requests ORDER BY owner,request_id')],
                        deletions=[dict(row) for row in db.execute('SELECT * FROM deletions ORDER BY memory_id')])

    @staticmethod
    def _validate_checkpoint(data):
        owners = _metadata(data, {'format','lineage','sequence','created_at','checkpoint_id','owners','heads','deletions'})
        if data['format'] != 'lya-fake-checkpoint/1':raise ValueError('Wrong checkpoint version.')
        _id(data['checkpoint_id'])
        heads = _heads(data['heads'],owners)
        if type(data['deletions']) is not list or len(data['deletions']) > MAX_RECORDS:
            raise ValueError('Invalid deletion register.')
        deleted = {}
        for row in data['deletions']:
            if type(row) is not dict or set(row) != set(DELETE_FIELDS):raise ValueError('Invalid deletion entry.')
            mid = _id(row['memory_id'])
            head = heads.get(mid)
            if (not head or not head['deleted'] or mid in deleted
                    or (row['owner'],row['project'],row['revision'],row['deleted_at']) != (head['owner'],head['project'],head['revision'],head['updated_at'])
                    or row['reason'] not in ('forget','expiry','restore_unavailable')):
                raise ValueError('Incomplete or mismatched deletion state.')
            deleted[mid] = row
        if set(deleted) != {mid for mid,row in heads.items() if row['deleted']}:
            raise ValueError('Incomplete deletion register.')
        return heads,deleted

    def checkpoint(self, memory, destination, *, approved=False, cancelled=lambda:False):
        if approved is not True:raise PermissionError('Trusted checkpoint approval required.')
        if cancelled():raise InterruptedError('Recovery cancelled.')
        data = self._capture(memory)
        checkpoint = dict(format='lya-fake-checkpoint/1',lineage=data['lineage'],sequence=data['sequence'],
                          created_at=_number(self.clock()),checkpoint_id=uuid.uuid4().hex,owners=data['owners'],
                          heads=[{key:row[key] for key in HEAD_FIELDS} for row in data['records']],deletions=data['deletions'])
        self._validate_checkpoint(checkpoint)
        blob = self._seal(checkpoint,CHECKPOINT_MAGIC,destination,cancelled)
        return CheckpointAnchor(data['lineage'],data['sequence'],checkpoint['checkpoint_id'],hashlib.sha256(blob).hexdigest())

    def backup(self, memory, destination, *, approved=False, cancelled=lambda:False):
        if approved is not True:raise PermissionError('Trusted backup approval required.')
        if cancelled():raise InterruptedError('Recovery cancelled.')
        data = self._capture(memory)
        data.pop('deletions')
        data.update(format='lya-fake-backup/1',created_at=_number(self.clock()))
        self._validate_backup(data)
        blob = self._seal(data,BACKUP_MAGIC,destination,cancelled)
        return {'records':len(data['records']),'sequence':data['sequence'],'encrypted_bytes':len(blob)}

    @staticmethod
    def _validate_backup(data):
        owners = _metadata(data, {'format','lineage','sequence','created_at','owners','records','requests'})
        if data['format'] != 'lya-fake-backup/1':raise ValueError('Wrong backup version.')
        records = _heads(data['records'],owners,records=True)
        if type(data['requests']) is not list or len(data['requests']) > MAX_REQUESTS+MAX_RECORDS:
            raise ValueError('Invalid receipt count.')
        seen = set()
        for row in data['requests']:
            if type(row) is not dict or set(row) != {'owner','request_id','fingerprint','result'}:
                raise ValueError('Invalid receipt.')
            _id(row['owner']);_id(row['request_id']);_id(row['fingerprint'],64)
            pair = (row['owner'],row['request_id'])
            result = json.loads(row['result'],object_pairs_hook=_unique)
            if type(result) is not dict or set(result) != {'id','revision','operation','committed'}:
                raise ValueError('Invalid receipt result.')
            record = records.get(_id(result['id']))
            _integer(result['revision'],1)
            if (pair in seen or not record or row['owner'] != record['owner']
                    or result['revision'] > record['revision'] or result['operation'] not in ('save','correct','forget')
                    or result['committed'] is not True):raise ValueError('Invalid receipt binding.')
            seen.add(pair)
        return records

    def restore(self, backup, checkpoint, destination, *, trusted_anchor, approved=False, cancelled=lambda:False):
        if approved is not True:raise PermissionError('Trusted restore approval required.')
        if type(trusted_anchor) is not CheckpointAnchor:raise ValueError('Latest independent checkpoint anchor required.')
        if cancelled():raise InterruptedError('Recovery cancelled.')
        saved,_ = self._open(backup,BACKUP_MAGIC)
        current,blob = self._open(checkpoint,CHECKPOINT_MAGIC)
        records = self._validate_backup(saved)
        heads,deletions = self._validate_checkpoint(current)
        expected = CheckpointAnchor(current['lineage'],current['sequence'],current['checkpoint_id'],hashlib.sha256(blob).hexdigest())
        if expected != trusted_anchor:raise ValueError('Checkpoint is not the trusted latest version.')
        if (saved['lineage'] != current['lineage'] or saved['sequence'] > current['sequence']
                or not set(saved['owners']) <= set(current['owners']) or not set(records) <= set(heads)):
            raise ValueError('Checkpoint does not cover this snapshot.')
        for mid,row in records.items():
            head = heads[mid]
            if (row['owner'],row['project']) != (head['owner'],head['project']) or row['revision'] > head['revision']:
                raise ValueError('Record state moved backwards or changed scope.')
            if row['revision'] == head['revision'] and any(row[key] != head[key] for key in HEAD_FIELDS):
                raise ValueError('Record changed without a revision.')
        now = _number(self.clock())
        restored, markers = [], []
        counts = {'preserved':0,'suppressed_deleted':0,'suppressed_expired':0,'suppressed_unavailable':0}
        for mid,head in heads.items():
            row = records.get(mid)
            expired = head['expires_at'] is not None and head['expires_at'] <= now
            available = row and row['revision'] == head['revision'] and not row['deleted']
            if not head['deleted'] and not expired and available:
                restored.append(row);counts['preserved'] += 1
                continue
            category = 'deleted' if head['deleted'] else 'expired' if expired else 'unavailable'
            counts['suppressed_'+category] += 1
            revision = head['revision'] if head['deleted'] else head['revision']+1
            stamp = head['updated_at'] if head['deleted'] else now
            restored.append(dict(id=mid,owner=head['owner'],project=head['project'],kind='',key='',normkey='',value=None,
                                 retention='',expires_at=None,revision=revision,recorded_at=row['recorded_at'] if row else stamp,
                                 updated_at=stamp,source_request='',deleted=1))
            markers.append(deletions[mid] if head['deleted'] else dict(owner=head['owner'],project=head['project'],
                           memory_id=mid,revision=revision,deleted_at=stamp,reason='expiry' if expired else 'restore_unavailable'))
        def write(path):
            memory = SyntheticMemory(path,synthetic_only=True,clock=self.clock)
            with memory._db() as db:
                db.execute('UPDATE store_meta SET lineage=?,sequence=? WHERE id=1', (current['lineage'],current['sequence']+1))
                db.executemany('INSERT INTO owners VALUES(?)',[(owner,) for owner in current['owners']])
                for row in restored:
                    rowid = db.execute('INSERT INTO memories('+','.join(RECORD_FIELDS)+') VALUES('+','.join('?' for _ in RECORD_FIELDS)+')',
                                       [row[key] for key in RECORD_FIELDS]).lastrowid
                    if not row['deleted']:
                        value = json.loads(row['value'])
                        text = (row['key']+' '+' '.join(str(item) for item in value.values())).casefold()
                        db.execute('INSERT INTO memory_search(rowid,text) VALUES(?,?)',(rowid,text))
                for row in saved['requests']:
                    db.execute('INSERT INTO requests VALUES(?,?,?,?)',[row[key] for key in ('owner','request_id','fingerprint','result')])
                for row in markers:
                    db.execute('INSERT INTO deletions VALUES(?,?,?,?,?,?)',[row[key] for key in DELETE_FIELDS])
                if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Restore scope check failed.')
                if cancelled():raise InterruptedError('Recovery cancelled.')
            with memory._db() as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':raise ValueError('Restore integrity failed.')
        _publish(destination,write,cancelled)
        # No bindings, sessions or old outbox jobs are restored. Explicit new authority is required.
        return {**counts,'quarantined':True,'active_bindings':0,'resumed_jobs':0}
