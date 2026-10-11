"""Operator-controlled public documents only; no private-store or model imports.

Run as a one-request SSH worker with a fixed, separate database. Scope IDs are
opaque namespaces, not authenticated identities. The SSH account is the authority.
"""
import hashlib
from contextlib import closing
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

MAX_WIRE = 65536
MAX_TEXT = 24000
MAX_ROWS = 10000
MAX_CONTENT = 128 * 1024 * 1024
FIELDS = {'owner', 'project', 'id', 'revision', 'title', 'source', 'text',
          'expires_at', 'sensitivity'}


def slug(value):
    if type(value) is not str or not re.fullmatch(r'[a-z0-9_-]{1,64}', value):
        raise ValueError('invalid_scope')
    return value


def revision(value, *, zero=False):
    if type(value) is not int or not (0 if zero else 1) <= value <= 1000000:
        raise ValueError('invalid_revision')
    return value


def record(value):
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError('invalid_record')
    for key in ('owner', 'project', 'id'):
        slug(value[key])
    revision(value['revision'])
    if value['sensitivity'] != 'public':
        raise ValueError('public_only')
    for key, limit in (('title', 256), ('source', 2048), ('text', MAX_TEXT)):
        if type(value[key]) is not str or not value[key].strip() or len(value[key].encode('utf-8')) > limit:
            raise ValueError('invalid_content')
    expiry = value['expires_at']
    if expiry is not None and (type(expiry) not in (int, float) or not math.isfinite(expiry) or expiry <= 0):
        raise ValueError('invalid_expiry')
    return value


def encoded(value):
    data = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode()
    if len(data) > MAX_WIRE:
        raise ValueError('request_too_large')
    return data


def validate_request(request, *, now=None):
    encoded(request)
    if type(request) is not dict:
        raise ValueError('invalid_request')
    op = request.get('op')
    fields = {'put': {'record', 'expected_revision', 'reviewed_public'},
              'get': {'id', 'revision'}, 'search': {'query'},
              'delete': {'id', 'expected_revision'}}
    if op not in fields or set(request) != {'op', 'owner', 'project'} | fields[op]:
        raise ValueError('invalid_request')
    owner, project = slug(request['owner']), slug(request['project'])
    if op == 'put':
        if request['reviewed_public'] is not True:
            raise PermissionError('public_review_required')
        item = record(request['record'])
        if (item['owner'], item['project']) != (owner, project):
            raise ValueError('scope_mismatch')
        expected = revision(request['expected_revision'], zero=True)
        if item['revision'] != expected + 1:
            raise ValueError('revision_conflict')
        if item['expires_at'] is not None and item['expires_at'] <= (time.time() if now is None else now):
            raise ValueError('expired_record')
    elif op in ('get', 'delete'):
        slug(request['id'])
        revision(request.get('revision', request.get('expected_revision')))
    elif type(request['query']) is not str or not 1 <= len(request['query']) <= 400:
        raise ValueError('invalid_query')
    return request


class PublicArchive:
    def __init__(self, path, *, clock=time.time):
        self.path = Path(path).resolve()
        self.clock = clock

    def handle(self, request):
        validate_request(request, now=self.clock())
        op = request.get('op')
        owner, project = request['owner'], request['project']
        item = request.get('record')
        if op == 'put':
            expected = request['expected_revision']

        # ponytail: single SQLite writer, 10k records/128MiB text; measure before replacing.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=3)) as db, db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA secure_delete=ON')
            db.execute('PRAGMA max_page_count=65536')  # <=256MiB at the default 4KiB page size.
            db.execute('''CREATE TABLE IF NOT EXISTS documents (
                owner TEXT, project TEXT, id TEXT, revision INTEGER,
                payload TEXT, expires_at REAL, deleted INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(owner,project,id))''')
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS document_search USING fts5(title,text)')
            db.execute('CREATE INDEX IF NOT EXISTS document_expiry ON documents(owner,project,expires_at)')
            db.execute('BEGIN IMMEDIATE')
            expired = db.execute('SELECT rowid FROM documents WHERE owner=? AND project=? AND deleted=0 AND expires_at<=?',
                                 (owner, project, self.clock())).fetchall()
            for row in expired:
                db.execute('DELETE FROM document_search WHERE rowid=?', (row[0],))
                db.execute("UPDATE documents SET payload='',expires_at=NULL,deleted=1,revision=revision+1 WHERE rowid=?", (row[0],))
            if op in ('put', 'delete'):
                old = db.execute('SELECT rowid,* FROM documents WHERE owner=? AND project=? AND id=?',
                                 (owner, project, item['id'] if item else request['id'])).fetchone()
                if op == 'put':
                    payload = encoded(item).decode()
                    if old and old['revision'] == item['revision'] and old['payload'] == payload and not old['deleted']:
                        return {'revision': item['revision'], 'acknowledged': True}
                    if (old['revision'] if old else 0) != expected:
                        raise ValueError('revision_conflict')
                    count, size = db.execute('SELECT count(*),coalesce(sum(length(CAST(payload AS BLOB))),0) FROM documents').fetchone()
                    if (not old and count >= MAX_ROWS) or size - (len(old['payload'].encode()) if old else 0) + len(payload.encode()) > MAX_CONTENT:
                        raise ValueError('archive_full')
                    if old:
                        db.execute('DELETE FROM document_search WHERE rowid=?', (old['rowid'],))
                        db.execute('UPDATE documents SET revision=?,payload=?,expires_at=?,deleted=0 WHERE rowid=?',
                                   (item['revision'], payload, item['expires_at'], old['rowid']))
                        rowid = old['rowid']
                    else:
                        rowid = db.execute('INSERT INTO documents VALUES (?,?,?,?,?,?,0)',
                                           (owner, project, item['id'], item['revision'], payload, item['expires_at'])).lastrowid
                    db.execute('INSERT INTO document_search(rowid,title,text) VALUES (?,?,?)',
                               (rowid, item['title'], item['text']))
                    return {'revision': item['revision'], 'acknowledged': True}
                if old and old['deleted'] and old['revision'] == request['expected_revision'] + 1:
                    return {'revision': old['revision'], 'acknowledged': True}
                if not old or old['revision'] != request['expected_revision']:
                    raise ValueError('revision_conflict')
                db.execute('DELETE FROM document_search WHERE rowid=?', (old['rowid'],))
                db.execute("UPDATE documents SET payload='',expires_at=NULL,deleted=1,revision=revision+1 WHERE rowid=?", (old['rowid'],))
                return {'revision': old['revision'] + 1, 'acknowledged': True}
            if op == 'get':
                row = db.execute('''SELECT payload FROM documents WHERE owner=? AND project=? AND id=?
                    AND revision=? AND deleted=0 AND (expires_at IS NULL OR expires_at>?)''',
                    (owner, project, request['id'], request['revision'], self.clock())).fetchone()
                return {'record': json.loads(row[0]) if row else None}
            tokens = re.findall(r'\w+', request['query'])[:32]
            if not tokens:
                return {'records': []}
            query = ' OR '.join('"' + token + '"' for token in tokens)
            rows = db.execute('''SELECT d.payload FROM document_search s JOIN documents d ON d.rowid=s.rowid
                WHERE document_search MATCH ? AND d.owner=? AND d.project=? AND d.deleted=0
                AND (d.expires_at IS NULL OR d.expires_at>?) ORDER BY bm25(document_search),d.rowid DESC LIMIT 6''',
                (query, owner, project, self.clock()))
            results = []
            for row in rows:
                hit = json.loads(row[0])
                hit['text'] = hit['text'][:500]
                results.append(hit)
            return {'records': results}

    def backup(self, destination):
        """Consistent public-only snapshot; caller supplies an independent destination."""
        destination = Path(destination)
        if not self.path.is_file() or destination.exists():
            raise ValueError('backup_requires_new_destination')
        try:
            with closing(sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)) as src, \
                    closing(sqlite3.connect(destination)) as dst, dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('backup_invalid')
        except Exception:
            destination.unlink(missing_ok=True)
            raise


class PublicCache:
    """Evictable public revisions, never an offline authority or write queue."""
    def __init__(self, directory, *, budget=256 * 1024 * 1024, clock=time.time):
        if type(budget) is not int or budget < 1:
            raise ValueError('invalid_budget')
        self.directory, self.budget, self.clock = Path(directory), budget, clock

    def _path(self, owner, project, doc_id, version):
        key = [slug(owner), slug(project), slug(doc_id), revision(version)]
        return self.directory / (hashlib.sha256(encoded(key)).hexdigest() + '.json')

    def put(self, item):
        record(item)
        data = encoded({'record': item, 'sha256': hashlib.sha256(encoded(item)).hexdigest()})
        if len(data) > self.budget:
            return False
        if self.directory.is_symlink():
            raise ValueError('invalid_cache_directory')
        self.directory.mkdir(parents=True, exist_ok=True)
        # Remove this single writer's interrupted temporary files before accounting.
        for interrupted in self.directory.glob('.lya-public-*.tmp'):
            interrupted.unlink(missing_ok=True)
        path = self._path(item['owner'], item['project'], item['id'], item['revision'])
        # ponytail: trusted one-process cache; atomic files, OS locking if shared later.
        entries = [p for p in self.directory.glob('*.json') if p.is_file() and not p.is_symlink() and p != path]
        size = sum(p.stat().st_size for p in entries)
        for victim in sorted(entries, key=lambda p: p.stat().st_mtime_ns):
            if size + len(data) <= self.budget:
                break
            size -= victim.stat().st_size
            victim.unlink()
        import tempfile
        fd, temporary = tempfile.mkstemp(dir=self.directory, prefix='.lya-public-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'wb') as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return True

    def get(self, owner, project, doc_id, version):
        if self.directory.is_symlink():
            return None
        path = self._path(owner, project, doc_id, version)
        if path.is_symlink():
            return None
        try:
            with path.open('rb') as source:
                envelope = json.loads(source.read(MAX_WIRE + 1))
            if set(envelope) != {'record', 'sha256'}:
                return None
            item = record(envelope['record'])
            if hashlib.sha256(encoded(item)).hexdigest() != envelope['sha256']:
                return None
            if self._path(item['owner'], item['project'], item['id'], item['revision']) != path:
                return None
            if item['expires_at'] is not None and item['expires_at'] <= self.clock():
                path.unlink(missing_ok=True)
                return None
            return {'record': item, 'freshness': 'offline_unverified'}
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def invalidate(self, owner, project, doc_id):
        for path in self.directory.glob('*.json'):
            if path.is_symlink():
                continue
            try:
                with path.open('rb') as source:
                    item = json.loads(source.read(MAX_WIRE + 1))['record']
                if (item['owner'], item['project'], item['id']) == (owner, project, doc_id):
                    path.unlink()
            except (OSError, ValueError, TypeError, KeyError):
                continue


def main():
    os.umask(0o077)
    try:
        raw = sys.stdin.buffer.read(MAX_WIRE + 1)
        if len(raw) > MAX_WIRE:
            raise ValueError('request_too_large')
        archive = PublicArchive(Path.home() / '.local/share/lya-public/archive.sqlite')
        result = archive.handle(json.loads(raw))
        sys.stdout.buffer.write(encoded(result))
    except Exception:
        # Never echo requests, file paths, provider keys or arbitrary exception strings.
        sys.stdout.write('{"error":"archive_request_failed"}')


if __name__ == '__main__':
    main()
