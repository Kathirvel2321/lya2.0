"""FAKE-DATA key envelopes and a separately trusted latest-state witness.

No password-manager integration or independent deployed storage.
The unlock key must be held outside the backup/witness host. Whole-witness rollback
remains outside this local protocol's protection.
"""
from contextlib import contextmanager,closing
from dataclasses import asdict,dataclass,field
import base64
import hashlib
import json
from pathlib import Path
import sqlite3

from cryptography.fernet import Fernet,InvalidToken
from brain.memory_prototype import Conflict,_id,_json,_unlinked
from brain.memory_recovery import CheckpointAnchor,_integer,_publish,_unique

MAGIC = b'LYA-FAKE-KEY-CUSTODY-1\n'
APPLICATION_ID = 0x4C594157


def _approval(synthetic_only,approved,cancelled):
    if synthetic_only is not True or approved is not True:raise PermissionError('Explicit fake-data custody approval required.')
    if cancelled():raise InterruptedError('Custody operation cancelled.')


def _anchor(anchor):
    if type(anchor) is not CheckpointAnchor:raise ValueError('Exact checkpoint anchor required.')
    _id(anchor.lineage);_integer(anchor.sequence);_id(anchor.checkpoint_id);_id(anchor.sha256,64)
    return anchor


def _cipher(key):
    if type(key) is not bytes or len(key)!=44:raise ValueError('Generated Fernet key required, never a password.')
    try:
        raw = base64.b64decode(key,altchars=b'-_',validate=True)
        if len(raw)!=32 or base64.urlsafe_b64encode(raw)!=key:raise ValueError('Noncanonical key.')
        return Fernet(key)
    except (TypeError,ValueError):raise ValueError('Invalid generated unlock/recovery key.') from None


@dataclass(frozen=True)
class RecoveryKeys:
    lineage: str
    storage_key: bytes = field(repr=False)
    recovery_key: bytes = field(repr=False)


@dataclass(frozen=True)
class WitnessState:
    anchor: CheckpointAnchor
    writer_epoch: int

    def __post_init__(self):
        _anchor(self.anchor);_integer(self.writer_epoch)


def _keys(data,lineage):
    if type(data) is not dict or set(data)!={'version','lineage','storage_key','recovery_key'}:
        raise ValueError('Unexpected key-envelope fields.')
    if type(data['version']) is not int or data['version']!=1 or _id(data['lineage'])!=_id(lineage):
        raise ValueError('Wrong key-envelope schema or lineage.')
    if type(data['storage_key']) is not str or type(data['recovery_key']) is not str:
        raise ValueError('Invalid encoded recovery keys.')
    try:storage = bytes.fromhex(_id(data['storage_key'],64));recovery = data['recovery_key'].encode('ascii')
    except (ValueError,UnicodeError):raise ValueError('Invalid encoded recovery keys.') from None
    _cipher(recovery)
    return RecoveryKeys(lineage,storage,recovery)


def _blob(path):
    path = Path(path);_unlinked(path)
    with path.open('rb') as source:blob = source.read(8193)
    if len(blob)>8192 or not blob.startswith(MAGIC):raise ValueError('Invalid bounded key envelope.')
    return blob


def seal_keys(destination,unlock_key,keys,*,synthetic_only=False,approved=False,cancelled=lambda:False):
    _approval(synthetic_only,approved,cancelled)
    if (type(keys) is not RecoveryKeys or type(keys.storage_key) is not bytes or len(keys.storage_key)!=32
            or type(keys.recovery_key) is not bytes):
        raise ValueError('Generated synthetic recovery keys required.')
    data = dict(version=1,lineage=keys.lineage,storage_key=keys.storage_key.hex(),recovery_key=keys.recovery_key.decode('ascii'))
    _keys(data,keys.lineage);cipher = _cipher(unlock_key)
    if unlock_key==keys.recovery_key or base64.urlsafe_b64decode(unlock_key)==keys.storage_key:
        raise ValueError('Custody unlock key must be independent of both stored keys.')
    blob = MAGIC+cipher.encrypt(_json(data).encode())
    def write(stage):
        Path(stage).write_bytes(blob)
        if cipher.decrypt(_blob(stage)[len(MAGIC):])!=_json(data).encode():raise ValueError('Key-envelope readback failed.')
    _publish(destination,write,cancelled)
    if _blob(destination)!=blob:raise ValueError('Published key-envelope readback failed.')
    _approval(synthetic_only,approved,cancelled)
    return hashlib.sha256(blob).hexdigest()


def open_keys(path,unlock_key,*,lineage,trusted_digest,synthetic_only=False,approved=False,cancelled=lambda:False):
    _approval(synthetic_only,approved,cancelled);_id(trusted_digest,64);_id(lineage)
    blob = _blob(path)
    if hashlib.sha256(blob).hexdigest()!=trusted_digest:raise ValueError('Key envelope differs from trusted custody state.')
    try:raw = _cipher(unlock_key).decrypt(blob[len(MAGIC):])
    except InvalidToken:raise ValueError('Key-envelope authentication failed.') from None
    keys = _keys(json.loads(raw,object_pairs_hook=_unique),lineage)
    _approval(synthetic_only,approved,cancelled)
    return keys


class SyntheticWitness:
    def __init__(self,path,*,synthetic_only=False):
        if synthetic_only is not True:raise PermissionError('Explicit fake-data witness opt-in required.')
        self.path = Path(path).absolute();_unlinked(self.path)
        with self._db():pass

    @classmethod
    def create(cls,path,*,synthetic_only=False,approved=False,cancelled=lambda:False):
        _approval(synthetic_only,approved,cancelled)
        def write(stage):
            with closing(sqlite3.connect(stage)) as db:
                db.execute(f'PRAGMA application_id={APPLICATION_ID}');db.execute('PRAGMA user_version=1')
                db.execute('CREATE TABLE heads(lineage TEXT PRIMARY KEY, state TEXT NOT NULL, keys_digest TEXT NOT NULL)')
                db.commit()
        _publish(path,write,cancelled)
        _approval(synthetic_only,approved,cancelled)
        return cls(path,synthetic_only=True)

    @contextmanager
    def _db(self):
        _unlinked(self.path)
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=3)) as db:
            try:
                if (db.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_ID
                        or db.execute('PRAGMA user_version').fetchone()[0]!=1):raise ValueError('Wrong witness schema.')
                db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
                db.execute('SELECT lineage,state,keys_digest FROM heads LIMIT 0')
                yield db;db.commit()
            except BaseException:db.rollback();raise

    @staticmethod
    def _state(state):
        if type(state) is not WitnessState:raise ValueError('Exact witness state required.')
        _anchor(state.anchor);_integer(state.writer_epoch)
        return state

    @staticmethod
    def _decode(raw,lineage):
        data = json.loads(raw,object_pairs_hook=_unique)
        if type(data) is not dict or set(data)!={'anchor','writer_epoch'}:raise ValueError('Malformed witness state.')
        state = WitnessState(CheckpointAnchor(**data['anchor']),data['writer_epoch'])
        if state.anchor.lineage!=lineage:raise ValueError('Wrong witness lineage.')
        return state

    def _head(self,db,lineage):
        _id(lineage)
        row = db.execute('SELECT state,keys_digest FROM heads WHERE lineage=?',(lineage,)).fetchone()
        if not row:raise ValueError('Witness lineage unavailable; never infer freshness from a backup.')
        return self._decode(row[0],lineage),_id(row[1],64)

    def head(self,lineage):
        with self._db() as db:return self._head(db,lineage)

    def register(self,state,keys_digest,*,approved=False,cancelled=lambda:False):
        _approval(True,approved,cancelled);self._state(state);_id(keys_digest,64)
        with self._db() as db:
            if db.execute('SELECT 1 FROM heads WHERE lineage=?',(state.anchor.lineage,)).fetchone():raise Conflict('Witness lineage already registered.')
            db.execute('INSERT INTO heads VALUES(?,?,?)',(state.anchor.lineage,_json(asdict(state)),keys_digest))
            _approval(True,approved,cancelled)
        return state

    def _advance(self,db,previous,state,keys_digest):
        """Reuse the caller's witness transaction to serialize a cross-store transition."""
        self._state(previous);self._state(state);_id(keys_digest,64)
        if previous.anchor.lineage!=state.anchor.lineage:raise Conflict('Wrong witness lineage.')
        observed,digest = self._head(db,state.anchor.lineage)
        if digest!=keys_digest:raise Conflict('Key custody changed; rotation requires a separate verified workflow.')
        if observed!=state:
            if observed!=previous:raise Conflict('Witness changed; refresh before advancing.')
            if (state.anchor.sequence<previous.anchor.sequence or state.writer_epoch<previous.writer_epoch
                    or (state.anchor.sequence==previous.anchor.sequence and state.anchor!=previous.anchor)
                    or state==previous):raise Conflict('Witness state must advance without divergence.')
            db.execute('UPDATE heads SET state=? WHERE lineage=?',(_json(asdict(state)),state.anchor.lineage))
        return state

    def advance(self,previous,state,keys_digest,*,approved=False,cancelled=lambda:False):
        _approval(True,approved,cancelled)
        with self._db() as db:
            self._advance(db,previous,state,keys_digest)
            _approval(True,approved,cancelled)
        return state

    def require(self,state,keys_digest):
        self._state(state);_id(keys_digest,64)
        if self.head(state.anchor.lineage)!=(state,keys_digest):raise Conflict('Source is not the exact trusted latest witnessed state.')
        return state
