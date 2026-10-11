"""Disposable FAKE-DATA SQLite baseline. Not encrypted or production-connected.

Explicit path and synthetic_only=True required. Trusted fixtures provide fresh
authentication and per-operation approval; model/client fields never grant it.
"""
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
import uuid

from brain.conversation import PublicTurn

APPLICATION_ID = 0x4C59414D
SCHEMA_VERSION = 2
MAX_PAGES = 16384
MAX_RECORDS = 10000
MAX_REQUESTS = 40000
LIFETIMES = {'short': 7 * 86400, 'long': 90 * 86400, 'permanent': None}


class Conflict(ValueError):
    pass


def _text(value, limit):
    if type(value) is not str or not value.strip() or len(value.encode('utf-8')) > limit:
        raise ValueError('Invalid bounded text.')
    return unicodedata.normalize('NFC', value.strip())


def _id(value, length=32):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{%d}' % length, value):
        raise ValueError('Invalid opaque ID.')
    return value


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':'))


def _validate(request):
    fields = {
        'save': {'request_id', 'kind', 'key', 'value', 'retention'},
        'correct': {'request_id', 'id', 'expected_revision', 'value'},
        'forget': {'request_id', 'id', 'expected_revision'},
        'get': {'id'}, 'search': {'query'},
    }
    if type(request) is not dict or type(request.get('op')) is not str:
        raise ValueError('Invalid request.')
    op = request['op']
    if op not in fields or set(request) != fields[op] | {'op', 'project'}:
        raise ValueError('Unknown operation or fields.')
    if type(request['project']) is not str or not re.fullmatch('[a-z0-9_-]{1,64}', request['project']):
        raise ValueError('Invalid project.')
    if 'request_id' in request:_id(request['request_id'])
    if 'id' in request:_id(request['id'])
    if 'expected_revision' in request:
        rev = request['expected_revision']
        if type(rev) is not int or not 1 <= rev < 1000000:raise ValueError('Invalid revision.')
    if 'value' in request:
        value = request['value']
        if (type(value) is not dict or not 1 <= len(value) <= 16
                or any(type(k) is not str or not re.fullmatch('[a-z][a-z0-9_]{0,63}', k) for k in value)
                or any(type(v) not in (str, int, float, bool, type(None)) for v in value.values())
                or len(_json(value).encode('utf-8')) > 4096):
            raise ValueError('Use a bounded flat JSON value.')
    if op == 'save':
        if request['kind'] not in ('fact', 'preference', 'decision', 'lesson'):
            raise ValueError('Not a conversational memory kind.')
        _text(request['key'], 640)
        retention = request['retention']
        if type(retention) is not dict:raise ValueError('Explicit retention required.')
        mode = retention.get('mode')
        if type(mode) is not str:raise ValueError('Invalid retention.')
        if mode == 'until':
            if set(retention) != {'mode', 'expires_at'}:raise ValueError('Invalid retention.')
            expiry = retention['expires_at']
            if type(expiry) not in (int, float) or not math.isfinite(expiry):raise ValueError('Invalid expiry.')
        elif mode not in LIFETIMES or set(retention) != {'mode'}:
            raise ValueError('Invalid retention.')
    if op == 'search':_text(request['query'], 400)
    # Copy validated primitives: caller mutation cannot change a pending write.
    return json.loads(_json(request))


class SyntheticMemory:
    def __init__(self, path, *, synthetic_only=False, clock=time.time):
        if synthetic_only is not True:raise PermissionError('Fake-data opt-in required; database is plaintext.')
        self.path = Path(path).absolute()
        if self.path.is_symlink() or self.path.parent.is_symlink():raise ValueError('No linked storage.')
        self.clock = clock
        fresh = not self.path.exists()
        with self._db(initializing=fresh) as db:
            if fresh:
                db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
                for sql in (
                    'CREATE TABLE store_meta(id INTEGER PRIMARY KEY CHECK(id=1), lineage TEXT NOT NULL, sequence INTEGER NOT NULL)',
                    'CREATE TABLE owners(id TEXT PRIMARY KEY)',
                    'CREATE TABLE bindings(binding TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owners(id), active INTEGER NOT NULL)',
                    '''CREATE TABLE memories(rowid INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE,
                        owner TEXT NOT NULL REFERENCES owners(id), project TEXT NOT NULL, kind TEXT NOT NULL,
                        key TEXT NOT NULL, normkey TEXT NOT NULL, value TEXT, retention TEXT NOT NULL,
                        expires_at REAL, revision INTEGER NOT NULL, recorded_at REAL NOT NULL,
                        updated_at REAL NOT NULL, source_request TEXT NOT NULL, deleted INTEGER NOT NULL DEFAULT 0,
                        UNIQUE(owner,project,id))''',
                    'CREATE UNIQUE INDEX active_key ON memories(owner,project,normkey) WHERE deleted=0',
                    'CREATE INDEX owner_expiry ON memories(owner,project,deleted,expires_at)',
                    'CREATE VIRTUAL TABLE memory_search USING fts5(text)',
                    '''CREATE TABLE outbox(id INTEGER PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL,
                        memory_id TEXT NOT NULL, revision INTEGER NOT NULL, operation TEXT NOT NULL,
                        state TEXT NOT NULL DEFAULT 'pending', FOREIGN KEY(owner,project,memory_id)
                        REFERENCES memories(owner,project,id))''',
                    '''CREATE TABLE deletions(owner TEXT NOT NULL, project TEXT NOT NULL, memory_id TEXT NOT NULL,
                        revision INTEGER NOT NULL, deleted_at REAL NOT NULL, reason TEXT NOT NULL,
                        PRIMARY KEY(owner,project,memory_id), FOREIGN KEY(owner,project,memory_id)
                        REFERENCES memories(owner,project,id))''',
                    '''CREATE TABLE requests(owner TEXT NOT NULL REFERENCES owners(id), request_id TEXT NOT NULL,
                        fingerprint TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(owner,request_id))''',
                ):db.execute(sql)
                db.execute('INSERT INTO store_meta VALUES(1,?,0)', (uuid.uuid4().hex,))

    @contextmanager
    def _db(self, initializing=False):
        # shortcut: reads and writes share one writer; qualify encrypted engines/concurrency before live use.
        db = sqlite3.connect(self.path, timeout=3)
        try:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            db.execute('PRAGMA synchronous=FULL')
            if not initializing:
                if (db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                        or db.execute('PRAGMA user_version').fetchone()[0] != SCHEMA_VERSION):
                    raise ValueError('Wrong database.')
            db.execute('PRAGMA secure_delete=ON')
            db.execute(f'PRAGMA max_page_count={MAX_PAGES}')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:db.close()

    def create_owner(self, binding):
        """Trusted synthetic provisioning only; never a client operation."""
        _id(binding, 64)
        with self._db() as db:
            row = db.execute('SELECT owner,active FROM bindings WHERE binding=?', (binding,)).fetchone()
            if row:
                if not row['active']:raise PermissionError('Binding revoked.')
                return row['owner']
            owner = uuid.uuid4().hex
            db.execute('INSERT INTO owners VALUES(?)', (owner,))
            db.execute('INSERT INTO bindings VALUES(?,?,1)', (binding, owner))
            db.execute('UPDATE store_meta SET sequence=sequence+1 WHERE id=1')
            return owner

    def rotate_binding(self, old, new, *, approved=False):
        """Trusted fixture simulates exact approved rotation; not a recovery API."""
        if approved is not True:raise PermissionError('Exact rotation approval required.')
        _id(old, 64);_id(new, 64)
        with self._db() as db:
            row = db.execute('SELECT owner FROM bindings WHERE binding=? AND active=1', (old,)).fetchone()
            if not row or db.execute('SELECT 1 FROM bindings WHERE binding=?', (new,)).fetchone():
                raise Conflict('Binding unavailable.')
            db.execute('UPDATE bindings SET active=0 WHERE binding=?', (old,))
            db.execute('INSERT INTO bindings VALUES(?,?,1)', (new, row['owner']))
            db.execute('UPDATE store_meta SET sequence=sequence+1 WHERE id=1')
            return row['owner']

    @staticmethod
    def _owner(db, turn, approved):
        if type(turn) is not PublicTurn or approved is not True:
            raise PermissionError('Trusted per-operation approval required.')
        turn.check()
        if not turn.context.owner_verified:raise PermissionError('Fresh signed owner verification required.')
        row = db.execute('SELECT owner FROM bindings WHERE binding=? AND active=1', (turn.context.principal,)).fetchone()
        if not row:raise PermissionError('Memory binding unavailable.')
        return row['owner']

    def _delete(self, db, row, now, reason):
        db.execute('DELETE FROM memory_search WHERE rowid=?', (row['rowid'],))
        db.execute("UPDATE memories SET key='',normkey='',value=NULL,kind='',retention='',expires_at=NULL,source_request='',deleted=1,revision=revision+1,updated_at=? WHERE rowid=?", (now, row['rowid']))
        self._enqueue(db, row['owner'], row['project'], row['id'], row['revision'] + 1, 'delete')
        db.execute('INSERT INTO deletions VALUES(?,?,?,?,?,?)',
                   (row['owner'], row['project'], row['id'], row['revision'] + 1, now, reason))

    @staticmethod
    def _enqueue(db, owner, project, mid, rev, op):
        db.execute('UPDATE store_meta SET sequence=sequence+1 WHERE id=1')
        db.execute("UPDATE outbox SET state='obsolete' WHERE owner=? AND project=? AND memory_id=? AND state='pending'", (owner, project, mid))
        db.execute('INSERT INTO outbox(owner,project,memory_id,revision,operation) VALUES(?,?,?,?,?)', (owner, project, mid, rev, op))

    def handle(self, turn, request, *, approved=False):
        request = _validate(request)
        with self._db() as db:
            owner = self._owner(db, turn, approved)
            now, op, project = self.clock(), request['op'], request['project']
            fingerprint = hashlib.sha256(_json(request).encode()).hexdigest()
            if 'request_id' in request:
                previous = db.execute('SELECT fingerprint,result FROM requests WHERE owner=? AND request_id=?', (owner, request['request_id'])).fetchone()
                if previous:
                    if previous['fingerprint'] != fingerprint:raise Conflict('Request ID reused with different content.')
                    turn.check()
                    return json.loads(previous['result'])
                # Reserve deletion receipts beyond the ordinary request budget.
                if op != 'forget' and db.execute('SELECT count(*) FROM requests').fetchone()[0] >= MAX_REQUESTS:
                    raise ValueError('Synthetic request budget full.')
            expired = db.execute('SELECT * FROM memories WHERE owner=? AND project=? AND deleted=0 AND expires_at<=?', (owner, project, now)).fetchall()
            for row in expired:self._delete(db, row, now, 'expiry')
            if op == 'save':
                key = _text(request['key'], 640)
                normkey = key.casefold()
                if db.execute('SELECT 1 FROM memories WHERE owner=? AND project=? AND normkey=? AND deleted=0', (owner, project, normkey)).fetchone():
                    raise Conflict('Use correction with the current revision.')
                if db.execute('SELECT count(*) FROM memories').fetchone()[0] >= MAX_RECORDS:raise ValueError('Synthetic record budget full.')
                mode = request['retention']['mode']
                expiry = request['retention'].get('expires_at') if mode == 'until' else now + LIFETIMES[mode] if LIFETIMES[mode] else None
                if expiry is not None and expiry <= now:raise ValueError('Expiry must be in the future.')
                mid, rev = uuid.uuid4().hex, 1
                rowid = db.execute('''INSERT INTO memories(id,owner,project,kind,key,normkey,value,retention,expires_at,revision,recorded_at,updated_at,source_request)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (mid, owner, project, request['kind'], key, normkey,
                    _json(request['value']), mode, expiry, rev, now, now, request['request_id'])).lastrowid
            elif op in ('correct', 'forget'):
                row = db.execute('SELECT * FROM memories WHERE owner=? AND project=? AND id=? AND deleted=0', (owner, project, request['id'])).fetchone()
                if not row or row['revision'] != request['expected_revision']:raise Conflict('Missing active record or revision conflict.')
                mid, rev, rowid = row['id'], row['revision'] + 1, row['rowid']
                if op == 'forget':self._delete(db, row, now, 'forget')
                else:
                    key = row['key']
                    db.execute('DELETE FROM memory_search WHERE rowid=?', (rowid,))
                    db.execute('UPDATE memories SET value=?,revision=?,updated_at=?,source_request=? WHERE rowid=?', (_json(request['value']), rev, now, request['request_id'], rowid))
            elif op == 'get':
                row = db.execute('SELECT * FROM memories WHERE owner=? AND project=? AND id=? AND deleted=0 AND (expires_at IS NULL OR expires_at>?)', (owner, project, request['id'], now)).fetchone()
                result = {'record': self._record(row) if row else None}
            else:
                # Quote the entire query as FTS data; never accept MATCH operators.
                query = '"' + _text(request['query'], 400).casefold().replace('"', '""') + '"'
                rows = db.execute('''SELECT m.* FROM memory_search s JOIN memories m ON m.rowid=s.rowid
                    WHERE memory_search MATCH ? AND m.owner=? AND m.project=? AND m.deleted=0
                    AND (m.expires_at IS NULL OR m.expires_at>?) ORDER BY m.rowid DESC LIMIT 6''', (query, owner, project, now))
                result = {'records': [self._record(row) for row in rows]}
            if op in ('save', 'correct'):
                text = (key + ' ' + ' '.join(str(v) for v in request['value'].values())).casefold()
                db.execute('INSERT INTO memory_search(rowid,text) VALUES(?,?)', (rowid, text))
                self._enqueue(db, owner, project, mid, rev, 'upsert')
            if op in ('save', 'correct', 'forget'):
                # Receipts contain no values; replay cannot return a forgotten fact.
                result = {'id': mid, 'revision': rev, 'operation': op, 'committed': True}
                db.execute('INSERT INTO requests VALUES(?,?,?,?)', (owner, request['request_id'], fingerprint, _json(result)))
            if self._owner(db, turn, approved) != owner:raise PermissionError('Owner changed.')
            return result

    @staticmethod
    def _record(row):
        fields = ('id', 'owner', 'project', 'kind', 'key', 'revision', 'recorded_at', 'updated_at', 'source_request', 'retention', 'expires_at')
        return {**{k: row[k] for k in fields}, 'value': json.loads(row['value']),
                'approval_state': 'owner_confirmed', 'storage_domain': 'synthetic_only'}

    def finish_job(self, job_id):
        """Fake projection acknowledgement only; no external worker/index model."""
        if type(job_id) is not int or job_id < 1:raise ValueError('Invalid job ID.')
        with self._db() as db:
            row = db.execute('''SELECT j.state,j.revision AS job_revision,j.operation,m.revision,m.deleted,m.expires_at
                FROM outbox j JOIN memories m ON m.owner=j.owner AND m.project=j.project AND m.id=j.memory_id WHERE j.id=?''', (job_id,)).fetchone()
            if not row:return False
            current = (row['job_revision'] == row['revision']
                       and ((row['operation'] == 'delete' and row['deleted'])
                            or row['operation'] == 'upsert' and not row['deleted'] and (row['expires_at'] is None or row['expires_at'] > self.clock())))
            if row['state'] == 'done':return current
            db.execute('UPDATE outbox SET state=? WHERE id=?', ('done' if current and row['state'] == 'pending' else 'obsolete', job_id))
            return current and row['state'] == 'pending'
