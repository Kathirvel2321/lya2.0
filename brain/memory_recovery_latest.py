"""FAKE-DATA publication head in a separately trusted store, never in a backup.

This store must survive independently. Rolling it back together with every backup
is outside this local protocol's protection. No host/service is deployed here.
"""
from contextlib import closing,contextmanager
from dataclasses import asdict,dataclass
import json
from pathlib import Path
import sqlite3
import time

from brain.memory_custody import _approval
from brain.memory_prototype import Conflict,_id,_json,_unlinked
from brain.memory_recovery import _publish,_unique
from brain.memory_recovery_pack import RecoveryPins,inspect_pack,restore_pack
from brain.memory_recovery_trust import _pins,open_trust

APPLICATION_ID=0x4C59414C


@dataclass(frozen=True)
class RecoveryHead:
    pins: RecoveryPins
    trust_digest: str

    def __post_init__(self):
        if type(self.pins) is not RecoveryPins:raise ValueError('Exact recovery pins required.')
        self.pins.__post_init__();_id(self.trust_digest,64)


def _head(value):
    if type(value) is not RecoveryHead:raise ValueError('Exact recovery publication head required.')
    value.__post_init__();return value


def _decode(raw):
    if raw is None:return None
    if type(raw) is not str or len(raw.encode())>8192:raise ValueError('Invalid bounded publication head.')
    try:
        data=json.loads(raw,object_pairs_hook=_unique)
        if type(data) is not dict or set(data)!={'pins','trust_digest'}:raise ValueError('Wrong head fields.')
        return RecoveryHead(_pins({'version':1,'pins':data['pins']}),data['trust_digest'])
    except (ValueError,KeyError,TypeError,RecursionError):raise ValueError('Malformed publication head.') from None


class SyntheticRecoveryLatest:
    def __init__(self,path,*,synthetic_only=False):
        if synthetic_only is not True:raise PermissionError('Explicit fake-data latest-store opt-in required.')
        self.path=Path(path).absolute();_unlinked(self.path)
        with self._db():pass

    @classmethod
    def create(cls,path,*,synthetic_only=False,approved=False,cancelled=lambda:False):
        """Explicit first-time trusted bootstrap, never a recovery fallback."""
        _approval(synthetic_only,approved,cancelled)
        def write(stage):
            with closing(sqlite3.connect(stage)) as db:
                db.execute(f'PRAGMA application_id={APPLICATION_ID}');db.execute('PRAGMA user_version=1')
                db.execute('CREATE TABLE heads(lineage TEXT PRIMARY KEY, confirmed TEXT, pending TEXT, '
                           'CHECK(confirmed IS NOT NULL OR pending IS NOT NULL))')
                db.commit()
        _publish(path,write,cancelled)
        return cls(path,synthetic_only=True)

    @contextmanager
    def _db(self):
        _unlinked(self.path)
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=3)) as db:
            try:
                if (db.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_ID
                        or db.execute('PRAGMA user_version').fetchone()[0]!=1):raise ValueError('Wrong latest-store schema.')
                db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
                db.execute('SELECT lineage,confirmed,pending FROM heads LIMIT 0')
                yield db;db.commit()
            except BaseException:db.rollback();raise

    @staticmethod
    def _row(db,lineage):
        _id(lineage)
        row=db.execute('SELECT confirmed,pending FROM heads WHERE lineage=?',(lineage,)).fetchone()
        if row is None:raise ValueError('Trusted latest head is missing; no backup-derived bootstrap.')
        values=tuple(_decode(raw) for raw in row)
        if not any(values) or any(value and value.pins.state.anchor.lineage!=lineage for value in values):
            raise ValueError('Latest-store lineage differs.')
        return values

    @classmethod
    def _confirmed(cls,db,lineage):
        current,pending=cls._row(db,lineage)
        if pending is not None:raise Conflict('Publication is pending; recovery must wait for verified completion.')
        return _head(current)

    def head(self,lineage):
        with self._db() as db:return self._confirmed(db,lineage)

    def begin(self,previous,candidate,*,approved=False,cancelled=lambda:False):
        """Persist uncertainty before publishing artifacts; exact retries are idempotent."""
        _approval(True,approved,cancelled);_head(candidate)
        lineage=candidate.pins.state.anchor.lineage
        if previous is not None:
            _head(previous);old=previous.pins;new=candidate.pins
            if (old.state.anchor.lineage!=lineage or old.keys_digest!=new.keys_digest
                    or new.state.anchor.sequence<old.state.anchor.sequence or new.state.writer_epoch<old.state.writer_epoch
                    or new.state==old.state
                    or (new.state.anchor.sequence==old.state.anchor.sequence
                        and (new.state.anchor!=old.state.anchor or new.backup_sha256!=old.backup_sha256))):
                raise Conflict('Publication must advance without key rotation, rollback or divergence.')
        with self._db() as db:
            exists=db.execute('SELECT 1 FROM heads WHERE lineage=?',(lineage,)).fetchone()
            if not exists:
                if previous is not None:raise Conflict('Previous trusted head is missing.')
                db.execute('INSERT INTO heads VALUES(?,NULL,?)',(lineage,_json(asdict(candidate))))
            else:
                current,pending=self._row(db,lineage)
                if pending is None and current==candidate:return candidate
                if current!=previous or pending not in (None,candidate):raise Conflict('Latest publication changed; refresh first.')
                db.execute('UPDATE heads SET pending=? WHERE lineage=?',(_json(asdict(candidate)),lineage))
            _approval(True,approved,cancelled)
        return candidate

    def finish(self,candidate,folder,trust_path,unlock_key,*,approved=False,cancelled=lambda:False):
        """Confirm only the reserved head after complete artifact/trust readback."""
        _approval(True,approved,cancelled);_head(candidate)
        lineage=candidate.pins.state.anchor.lineage
        with self._db() as db:
            current,pending=self._row(db,lineage)
            if pending!=candidate and not (pending is None and current==candidate):raise Conflict('Exact pending publication required.')
            pins=open_trust(trust_path,unlock_key,trusted_digest=candidate.trust_digest,
                            synthetic_only=True,approved=True,cancelled=cancelled)
            if pins!=candidate.pins:raise Conflict('Trust record differs from reserved publication.')
            inspect_pack(folder,pins=pins,unlock_key=unlock_key,synthetic_only=True,approved=True,cancelled=cancelled)
            db.execute('UPDATE heads SET confirmed=?,pending=NULL WHERE lineage=?',(_json(asdict(candidate)),lineage))
            _approval(True,approved,cancelled)
        return candidate

    def restore(self,lineage,folder,trust_path,destination,unlock_key,*,approved=False,cancelled=lambda:False,clock=time.time):
        _approval(True,approved,cancelled)
        # shortcut: serialize local restore/publication with one SQLite lock; remote placement needs a fenced protocol.
        with self._db() as db:
            current=self._confirmed(db,lineage)
            pins=open_trust(trust_path,unlock_key,trusted_digest=current.trust_digest,
                            synthetic_only=True,approved=True,cancelled=cancelled)
            if pins!=current.pins:raise Conflict('Trust differs from the current publication.')
            return restore_pack(folder,destination,pins=pins,unlock_key=unlock_key,synthetic_only=True,
                                approved=True,cancelled=cancelled,clock=clock)
