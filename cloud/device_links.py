"""Owner-approved clients and encrypted recent conversation on the private host."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import secrets
import stat
import threading

from cryptography.fernet import Fernet

from cloud.answering import bounded_history


def token_hash(token):
    if type(token) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise PermissionError('Link or device credential unavailable.')
    return hashlib.sha256(token.encode('ascii')).hexdigest()


class DeviceLinks:
    def __init__(self, store, cipher, clock):
        self.store, self.cipher, self.clock = store, cipher, clock
        self.pending = {}
        self.turn_lock = threading.Lock()
        with store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS linked_devices (id TEXT PRIMARY KEY, token TEXT UNIQUE, stamp TEXT, name TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS linked_history (id INTEGER PRIMARY KEY CHECK(id=1), stamp TEXT, data BLOB)')
            db.execute('CREATE TABLE IF NOT EXISTS linked_turns (id TEXT PRIMARY KEY, stamp TEXT)')

    @classmethod
    def configured(cls, store, key_path, clock):
        path = Path(key_path)
        mode = path.lstat().st_mode
        if not path.is_absolute() or not stat.S_ISREG(mode) or mode & 0o077:
            raise PermissionError('Use a private service history key file.')
        with path.open('rb') as file:
            return cls(store, Fernet(file.read(64).strip()), clock)

    def start(self, name, stamp):
        if type(name) is not str or not 1 <= len(name.strip()) <= 60 or not name.isprintable():
            raise ValueError('Enter a printable device name.')
        now = self.clock()
        self.pending = {key: row for key, row in self.pending.items() if now < row['expires']}
        if len(self.pending) >= 8:
            raise PermissionError('Too many outstanding requests.')
        link, secret = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        code = f'{secrets.randbelow(10**6):06d}'
        self.pending[link] = dict(name=name.strip(), code=code, token=token_hash(secret),
                                  stamp=stamp, expires=now+180)
        return dict(link=link, credential=secret, code=code)

    def request(self, link, stamp):
        token_hash(link)
        row = self.pending.get(link)
        if not row or self.clock() >= row['expires'] or row['stamp'] != stamp:
            raise PermissionError('Link expired.')
        return row

    def approve(self, link, stamp):
        row = self.request(link, stamp)
        with self.store.db() as db:
            if db.execute('SELECT stamp FROM credential WHERE id=1').fetchone() != (stamp,):
                raise PermissionError('Phone credential changed.')
            db.execute('DELETE FROM linked_devices WHERE stamp<>?', (stamp,))
            if db.execute('SELECT COUNT(*) FROM linked_devices').fetchone()[0] >= 12:
                raise PermissionError('Unlink an older device first.')
            db.execute('INSERT INTO linked_devices VALUES(?,?,?,?)', (link, row['token'], stamp, row['name']))
        del self.pending[link]

    def check(self, token):
        with self.store.db() as db:
            row = db.execute('SELECT stamp FROM linked_devices WHERE token=? AND stamp=(SELECT stamp FROM credential WHERE id=1)',
                             (token_hash(token),)).fetchone()
        if not row:
            raise PermissionError('Device is pending or unlinked.')
        return row[0]

    def devices(self, stamp, remove=None):
        with self.store.db() as db:
            if db.execute('SELECT stamp FROM credential WHERE id=1').fetchone() != (stamp,):
                raise PermissionError('Phone credential changed.')
            if remove is not None:
                token_hash(remove)
                db.execute('DELETE FROM linked_devices WHERE id=? AND stamp=?', (remove, stamp))
            return [dict(id=id, name=name) for id, name in db.execute(
                'SELECT id,name FROM linked_devices WHERE stamp=? ORDER BY name,id', (stamp,))]

    def history(self, stamp):
        with self.store.db() as db:
            row = db.execute('SELECT data FROM linked_history WHERE id=1 AND stamp=?', (stamp,)).fetchone()
        return bounded_history(json.loads(self.cipher.decrypt(row[0]))) if row else []

    def check_turn(self, stamp, request_id):
        with self.store.db() as db:
            if db.execute('SELECT 1 FROM linked_turns WHERE stamp=? AND id=?',(stamp,request_id)).fetchone():
                raise ValueError('Already saved. Refresh the conversation.')

    def save(self, stamp, history, request_id, device=None):
        sealed = self.cipher.encrypt(json.dumps(bounded_history(history)).encode())
        with self.store.db() as db:
            if db.execute('SELECT stamp FROM credential WHERE id=1').fetchone() != (stamp,):
                raise PermissionError('Phone credential changed.')
            if device and not db.execute('SELECT 1 FROM linked_devices WHERE token=? AND stamp=?',
                                         (token_hash(device), stamp)).fetchone():
                raise PermissionError('Device unlinked.')
            db.execute('INSERT OR REPLACE INTO linked_history VALUES(1,?,?)', (stamp, sealed))
            db.execute('DELETE FROM linked_turns WHERE stamp<>?',(stamp,))
            db.execute('INSERT INTO linked_turns VALUES(?,?)',(request_id,stamp))
            db.execute('DELETE FROM linked_turns WHERE rowid NOT IN (SELECT rowid FROM linked_turns ORDER BY rowid DESC LIMIT 100)')

    @contextmanager
    def turn(self):
        if not self.turn_lock.acquire(blocking=False):
            raise ValueError('Another device is sending a message. Try again shortly.')
        try:
            yield
        finally:
            self.turn_lock.release()
