"""FAKE-DATA canonical snapshots and writer fencing; no independent deployed service.

Only this authority's committed pointer defines current memory. Device copies and
uncommitted candidates cannot publish directly. The local catalogue is trusted;
optional witness binding detects source rollback while that trusted witness survives.
Independent placement and real key custody remain outside this fixture.
"""
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass, field
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import tempfile
import time
import uuid

from brain.conversation import PublicTurn
from brain.memory_prototype import Conflict, SyntheticMemory, _id, _json, _unlinked, _validate
from brain.memory_recovery import CheckpointAnchor, SyntheticRecovery, _integer, _publish, _read
from brain.memory_repository import SyntheticRepository
from brain.memory_custody import SyntheticWitness, WitnessState


@dataclass(frozen=True)
class WriterGrant:
    lineage: str
    epoch: int
    writer: str
    token: bytes = field(repr=False)


class SyntheticAuthority:
    def __init__(self, path, *, recovery, storage_key, synthetic_only=False, clock=time.time, witness=None):
        if synthetic_only is not True:raise PermissionError('Fake-data authority opt-in required.')
        if type(recovery) is not SyntheticRecovery:raise ValueError('Synthetic recovery required.')
        if type(storage_key) is not bytes or len(storage_key) != 32:raise ValueError('Generated 32-byte storage key required.')
        if witness is not None and type(witness) is not SyntheticWitness:raise ValueError('Synthetic witness required.')
        self._witness = witness
        self._recovery,self._key,self.clock = recovery,storage_key,clock
        self._key_id = hashlib.sha256(storage_key).hexdigest()
        path = Path(path).absolute();_unlinked(path)
        fresh = not path.exists()
        if fresh and witness is not None:raise ValueError('Bootstrap locally, register the witness, then explicitly bind it.')
        self._repository = SyntheticRepository(path,synthetic_only=True)
        with self._repository._db() as db:
            if fresh:
                db.execute('CREATE TABLE authority_meta(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL)')
                db.execute('INSERT INTO authority_meta VALUES(1,2)')
                db.execute('''CREATE TABLE writers(lineage TEXT PRIMARY KEY REFERENCES latest(lineage),
                    epoch INTEGER NOT NULL, writer TEXT, token_sha256 TEXT,
                    live_sha256 TEXT NOT NULL, storage_key_sha256 TEXT NOT NULL)''')
                db.execute('''CREATE TABLE owner_bindings(lineage TEXT NOT NULL, principal_sha256 TEXT NOT NULL,
                    owner TEXT NOT NULL, PRIMARY KEY(lineage,principal_sha256))''')
                db.execute('''CREATE TABLE recoveries(lineage TEXT PRIMARY KEY, epoch INTEGER NOT NULL,
                    anchor_sha256 TEXT NOT NULL, restored_sha256 TEXT NOT NULL)''')
            self._schema(db)

    def _schema(self, db):
        try:rows = db.execute('SELECT id,version FROM authority_meta').fetchall()
        except sqlite3.DatabaseError as error:raise ValueError('Missing authority state; never recreate it.') from error
        versions = [tuple(row) for row in rows]
        if versions == [(1,3)]:
            if self._witness is None:raise PermissionError('This authority requires its bound witness.')
            db.execute('SELECT lineage,keys_digest,previous_state,next_state FROM witness_links LIMIT 0')
        elif versions != [(1,2)]:raise ValueError('Wrong authority schema.')
        # Missing custody/activation state must not be recreated on reopening.
        db.execute('SELECT lineage,epoch,writer,token_sha256,live_sha256,storage_key_sha256 FROM writers LIMIT 0')
        db.execute('SELECT lineage,principal_sha256,owner FROM owner_bindings LIMIT 0')
        db.execute('SELECT lineage,epoch,anchor_sha256,restored_sha256 FROM recoveries LIMIT 0')
        return versions[0][1]

    def _witness_state(self, db, lineage):
        writer,anchor,*_ = self._entry(db,lineage,live=False)
        return WitnessState(anchor,writer['epoch'])

    def _witness_link(self, db, lineage):
        if self._schema(db)!=3:raise PermissionError('Explicit witness binding required.')
        row = db.execute('SELECT * FROM witness_links WHERE lineage=?',(_id(lineage),)).fetchone()
        if not row:raise ValueError('Witness binding unavailable; never recreate it.')
        previous = self._witness._decode(row['previous_state'],lineage)
        target = self._witness._decode(row['next_state'],lineage)
        if self._witness_state(db,lineage)!=target:raise Conflict('Authority changed outside its witnessed transition.')
        return previous,target,_id(row['keys_digest'],64)

    def bind_witness(self, lineage, keys_digest, *, approved=False):
        """Explicit schema-2 to schema-3 cutover against an already registered witness."""
        self._approval(approved,lambda:False);_id(lineage);_id(keys_digest,64)
        if self._witness is None:raise PermissionError('Supply the existing synthetic witness before binding.')
        with self._witness._db() as trusted,self._repository._db() as db:
            version = self._schema(db)
            writer,anchor,*_ = self._entry(db,lineage)
            state = WitnessState(anchor,writer['epoch'])
            if self._witness._head(trusted,lineage)!=(state,keys_digest):
                raise Conflict('Binding requires the exact existing witness and key-capsule digest.')
            if version==2:
                db.execute('CREATE TABLE witness_links(lineage TEXT PRIMARY KEY, keys_digest TEXT NOT NULL, previous_state TEXT NOT NULL, next_state TEXT NOT NULL)')
                db.execute('UPDATE authority_meta SET version=3 WHERE id=1')
            if db.execute('SELECT 1 FROM witness_links WHERE lineage=?',(lineage,)).fetchone():
                raise Conflict('Witness already bound; replacement is not a retry.')
            encoded = _json(asdict(state))
            db.execute('INSERT INTO witness_links VALUES(?,?,?,?)',(lineage,keys_digest,encoded,encoded))
        return state

    @contextmanager
    def _transaction(self, lineage, cancelled=lambda:False):
        if self._witness is None:
            with self._repository._db() as db:yield db
            return
        # shortcut: one local witness writer lock spans both stores; a remote service needs its own serialized protocol.
        with self._witness._db() as trusted:
            with self._repository._db() as db:
                _,before,digest = self._witness_link(db,lineage)
                if self._witness._head(trusted,lineage)!=(before,digest):
                    raise Conflict('Witness is not current; explicit reconciliation required.')
                yield db
                after = self._witness_state(db,lineage)
                if after!=before:
                    db.execute('UPDATE witness_links SET previous_state=?,next_state=? WHERE lineage=?',
                               (_json(asdict(before)),_json(asdict(after)),lineage))
                self._approval(True,cancelled)
            # The durable local transition survives failure before the witness commit.
            self._approval(True,cancelled)
            self._witness._advance(trusted,before,after,digest)
            self._approval(True,cancelled)
        self._approval(True,cancelled)

    def reconcile_witness(self, lineage, *, approved=False, cancelled=lambda:False):
        """Confirm only the journaled local transition; never issue a grant or replay content."""
        self._approval(approved,cancelled)
        if self._witness is None:raise PermissionError('Bound witness required.')
        with self._witness._db() as trusted,self._repository._db() as db:
            previous,target,digest = self._witness_link(db,lineage)
            self._witness._advance(trusted,previous,target,digest)
            self._approval(approved,cancelled)
        self._approval(approved,cancelled)
        return dict(anchor=target.anchor,writer_epoch=target.writer_epoch,witness_confirmed=True,synthetic_only=True)

    @staticmethod
    def _approval(approved, cancelled):
        if approved is not True:raise PermissionError('Exact trusted authority approval required.')
        if cancelled():raise InterruptedError('Authority operation cancelled.')

    @staticmethod
    def _anchor(anchor):
        if type(anchor) is not CheckpointAnchor:raise ValueError('Exact authority anchor required.')
        _id(anchor.lineage);_integer(anchor.sequence);_id(anchor.checkpoint_id);_id(anchor.sha256,64)
        return anchor

    def _entry(self, db, lineage, *, live=True):
        self._schema(db);_id(lineage)
        row = db.execute('SELECT * FROM latest WHERE lineage=?',(lineage,)).fetchone()
        writer = db.execute('SELECT * FROM writers WHERE lineage=?',(lineage,)).fetchone()
        if not row or not writer:raise ValueError('Registered authority state unavailable.')
        if writer['storage_key_sha256'] != self._key_id:raise ValueError('Wrong authority storage key.')
        _integer(writer['epoch'])
        anchor,backup,checkpoint,saved,current = self._repository._verify(row,self._recovery)
        path = self._repository.path/'objects'/_id(row['object_id'])/'live.sqlite'
        memory = None
        if live:
            if hashlib.sha256(_read(path)).hexdigest() != _id(writer['live_sha256'],64):
                raise ValueError('Canonical database differs from the committed authority state.')
            memory = SyntheticMemory(path,synthetic_only=True,encryption_key=self._key,clock=self.clock)
            if not self._repository._same_snapshot(self._recovery._capture(memory),saved,current):
                raise ValueError('Canonical database and recovery snapshot differ.')
        return writer,anchor,memory,backup,checkpoint,row

    def _clone(self, source, path):
        if type(source) is not SyntheticMemory or source._key != self._key:
            raise ValueError('Matching encrypted synthetic source required.')
        target = SyntheticMemory(path,synthetic_only=True,encryption_key=self._key,clock=self.clock)
        with closing(source._connect(read_only=True)) as origin,closing(target._connect()) as destination:
            origin.backup(destination)
        return target

    def _publish(self, db, candidate, cancelled):
        """Publish immutable encrypted files, verify, then change the transaction's pointer."""
        object_id = uuid.uuid4().hex
        folder = self._repository.path/'objects'/object_id
        _unlinked(folder);folder.mkdir()
        _publish(folder/'live.sqlite',lambda stage:shutil.copyfile(candidate.path,stage),cancelled)
        anchor = self._recovery.bundle(candidate,folder/'backup.enc',folder/'checkpoint.enc',
                                       approved=True,cancelled=cancelled)
        row = dict(lineage=anchor.lineage,sequence=anchor.sequence,checkpoint_id=anchor.checkpoint_id,
                   sha256=anchor.sha256,backup_sha256=hashlib.sha256(_read(folder/'backup.enc')).hexdigest(),
                   object_id=object_id,key_sha256=self._recovery.key_id)
        self._repository._verify(row,self._recovery)
        live_hash = hashlib.sha256(_read(folder/'live.sqlite')).hexdigest()
        if live_hash != hashlib.sha256(_read(candidate.path)).hexdigest():raise ValueError('Live snapshot readback failed.')
        db.execute('''INSERT INTO latest VALUES(?,?,?,?,?,?,?) ON CONFLICT(lineage) DO UPDATE SET
            sequence=excluded.sequence,checkpoint_id=excluded.checkpoint_id,sha256=excluded.sha256,
            backup_sha256=excluded.backup_sha256,object_id=excluded.object_id,key_sha256=excluded.key_sha256''',tuple(row.values()))
        return anchor,live_hash

    def register(self, memory, *, approved=False, cancelled=lambda:False):
        """Trusted one-time synthetic bootstrap; not device enrollment or import."""
        self._approval(approved,cancelled)
        if self._witness is not None:raise PermissionError('Witnessed mode requires a previously bootstrapped lineage.')
        if type(memory) is not SyntheticMemory or memory._key != self._key:
            raise ValueError('Matching encrypted synthetic source required.')
        lineage,_ = self._repository._state(memory)
        with self._repository._db() as db:
            self._schema(db)
            if db.execute('SELECT 1 FROM latest WHERE lineage=?',(lineage,)).fetchone():
                raise Conflict('Lineage already registered; device copies cannot reset it.')
            with tempfile.TemporaryDirectory(prefix='.candidate-',dir=self._repository.path) as folder:
                candidate = self._clone(memory,Path(folder)/'live.sqlite')
                anchor,digest = self._publish(db,candidate,cancelled)
                if anchor.lineage != lineage:raise Conflict('Source lineage changed.')
                db.execute('INSERT INTO writers VALUES(?,0,NULL,NULL,?,?)',(lineage,digest,self._key_id))
                with closing(candidate._connect(read_only=True)) as source:
                    for binding in source.execute('SELECT binding,owner FROM bindings WHERE active=1'):
                        principal = hashlib.sha256(_id(binding['binding'],64).encode()).hexdigest()
                        db.execute('INSERT INTO owner_bindings VALUES(?,?,?)',(lineage,principal,_id(binding['owner'])))
                self._approval(approved,cancelled)
        return anchor

    def head(self, lineage):
        """Trusted content-free observation, not a public unauthenticated endpoint."""
        with self._transaction(lineage) as db:
            writer,anchor,*_ = self._entry(db,lineage,live=False)
            result = dict(anchor=anchor,writer_epoch=writer['epoch'],writer_active=writer['token_sha256'] is not None,
                        recovery_pending=db.execute('SELECT 1 FROM recoveries WHERE lineage=?',(lineage,)).fetchone() is not None,
                        synthetic_only=True)
            if self._witness is not None:result['witness_confirmed'] = True
            return result

    def acquire(self, lineage, writer, *, expected_epoch, approved=False):
        """An explicitly approved takeover increments the durable fencing generation."""
        self._approval(approved,lambda:False);_id(lineage);_id(writer);_integer(expected_epoch)
        with self._transaction(lineage) as db:
            self._schema(db)
            if db.execute('SELECT 1 FROM recoveries WHERE lineage=?',(lineage,)).fetchone():
                raise Conflict('Recovery pending; explicit owner reactivation required.')
            state,*_ = self._entry(db,lineage)
            if state['epoch'] != expected_epoch:raise Conflict('Writer generation changed.')
            epoch = _integer(expected_epoch+1)
            grant = WriterGrant(lineage,epoch,writer,secrets.token_bytes(32))
            db.execute('UPDATE writers SET epoch=?,writer=?,token_sha256=? WHERE lineage=?',
                       (epoch,writer,hashlib.sha256(grant.token).hexdigest(),lineage))
        return grant

    @staticmethod
    def _grant(db, grant):
        if type(grant) is not WriterGrant:raise PermissionError('Issued writer grant required.')
        _id(grant.lineage);_id(grant.writer);_integer(grant.epoch,1)
        if type(grant.token) is not bytes or len(grant.token) != 32:raise PermissionError('Invalid writer grant.')
        state = db.execute('SELECT * FROM writers WHERE lineage=?',(grant.lineage,)).fetchone()
        if (not state or state['epoch'] != grant.epoch or state['writer'] != grant.writer
                or not state['token_sha256'] or not hmac.compare_digest(state['token_sha256'],hashlib.sha256(grant.token).hexdigest())):
            raise PermissionError('Writer grant revoked or superseded.')

    def handle(self, grant, turn, request, *, expected_anchor, approved=False, cancelled=lambda:False):
        self._approval(approved,cancelled)
        request = _validate(request);self._anchor(expected_anchor)
        if type(turn) is not PublicTurn:raise PermissionError('Fresh authenticated turn required.')
        turn.check()
        if type(grant) is not WriterGrant:raise PermissionError('Issued writer grant required.')
        # shortcut: serialize and copy a bounded whole store; qualify server-scale transactions before live use.
        with self._transaction(grant.lineage,cancelled) as db:
            self._schema(db);self._grant(db,grant)
            if expected_anchor.lineage != grant.lineage:raise Conflict('Wrong authority lineage.')
            _,anchor,current,_,_,row = self._entry(db,grant.lineage)
            with closing(current._connect(read_only=True)) as source:
                owner = current._owner(source,turn,approved)
                prior = source.execute('SELECT fingerprint,result FROM requests WHERE owner=? AND request_id=?',
                                       (owner,request.get('request_id'))).fetchone()
            if prior and prior['fingerprint'] != hashlib.sha256(_json(request).encode()).hexdigest():
                raise Conflict('Request ID reused with different content.')
            if expected_anchor != anchor and not prior:raise Conflict('Memory changed; refresh the authority anchor.')
            if prior:
                result = json.loads(prior['result'])
            else:
                with tempfile.TemporaryDirectory(prefix='.candidate-',dir=self._repository.path) as folder:
                    candidate = self._clone(current,Path(folder)/'live.sqlite')
                    before = self._recovery._capture(candidate)
                    *_,saved,checkpoint = self._repository._verify(row,self._recovery)
                    if not self._repository._same_snapshot(before,saved,checkpoint):
                        raise ValueError('Candidate copy differs from the committed authority snapshot.')
                    result = candidate.handle(turn,request,approved=approved)
                    after = self._recovery._capture(candidate)
                    if after != before:
                        if after['lineage'] != anchor.lineage or after['sequence'] <= anchor.sequence:
                            raise Conflict('Candidate state did not advance monotonically.')
                        anchor,digest = self._publish(db,candidate,cancelled)
                        db.execute('UPDATE writers SET live_sha256=? WHERE lineage=?',(digest,grant.lineage))
            turn.check();self._approval(approved,cancelled)
        reply = dict(result=result,anchor=anchor,writer_epoch=grant.epoch)
        if self._witness is not None:
            turn.check();reply['witness_confirmed'] = True
        return reply

    def restore(self, lineage, destination, *, expected_anchor, approved=False, cancelled=lambda:False):
        """Latest authority snapshot only; successful recovery revokes all writer grants."""
        self._approval(approved,cancelled);self._anchor(expected_anchor)
        with self._transaction(lineage,cancelled) as db:
            state,anchor,_,backup,checkpoint,row = self._entry(db,lineage,live=False)
            if expected_anchor != anchor:raise Conflict('Restore anchor is not the authority latest state.')
            epoch = _integer(state['epoch']+1)
            db.execute('UPDATE writers SET epoch=?,writer=NULL,token_sha256=NULL WHERE lineage=?',(epoch,lineage))
            result = self._recovery.restore(backup,checkpoint,destination,trusted_anchor=anchor,approved=True,
                                           trusted_backup_sha256=row['backup_sha256'],storage_key=self._key,cancelled=cancelled)
            digest = hashlib.sha256(_read(destination)).hexdigest()
            db.execute('INSERT OR REPLACE INTO recoveries VALUES(?,?,?,?)',(lineage,epoch,anchor.sha256,digest))
            self._approval(approved,cancelled)
        reply = dict(result=result,anchor=anchor,writer_epoch=epoch)
        if self._witness is not None:reply['witness_confirmed'] = True
        return reply

    def activate_restored(self, lineage, restored, turn, writer, *, expected_anchor, expected_epoch,
                          approved=False, cancelled=lambda:False):
        """Synthetic reactivation of one pre-existing owner; never enroll a new identity."""
        self._approval(approved,cancelled);self._anchor(expected_anchor);_id(writer);_integer(expected_epoch)
        if type(turn) is not PublicTurn or not turn.context.owner_verified:
            raise PermissionError('Fresh pre-existing owner verification required.')
        turn.check();principal = _id(turn.context.principal,64)
        with self._transaction(lineage,cancelled) as db:
            state,anchor,*_ = self._entry(db,lineage,live=False)
            pending = db.execute('SELECT * FROM recoveries WHERE lineage=?',(lineage,)).fetchone()
            if (not pending or anchor != expected_anchor or state['epoch'] != expected_epoch
                    or pending['epoch'] != expected_epoch or pending['anchor_sha256'] != anchor.sha256):
                raise Conflict('Recovery state changed or no activation is pending.')
            binding = db.execute('SELECT owner FROM owner_bindings WHERE lineage=? AND principal_sha256=?',
                                 (lineage,hashlib.sha256(principal.encode()).hexdigest())).fetchone()
            if not binding:raise PermissionError('Verified identity is not a pre-existing owner of this lineage.')
            if hashlib.sha256(_read(restored)).hexdigest() != _id(pending['restored_sha256'],64):
                raise ValueError('Restored file differs from the acknowledged quarantine.')
            recovered = SyntheticMemory(restored,synthetic_only=True,encryption_key=self._key,clock=self.clock)
            snapshot = self._recovery._capture(recovered)
            if snapshot['lineage'] != lineage or snapshot['sequence'] != anchor.sequence+1:
                raise ValueError('Wrong quarantine lineage or sequence.')
            with tempfile.TemporaryDirectory(prefix='.candidate-',dir=self._repository.path) as folder:
                candidate = self._clone(recovered,Path(folder)/'live.sqlite')
                if (self._recovery._capture(candidate) != snapshot
                        or hashlib.sha256(_read(restored)).hexdigest() != pending['restored_sha256']):
                    raise ValueError('Quarantine changed during activation capture.')
                with candidate._db() as source:
                    if (source.execute('SELECT count(*) FROM bindings').fetchone()[0]
                            or source.execute('SELECT count(*) FROM outbox').fetchone()[0]):
                        raise ValueError('Restore is not quarantined.')
                    owner = _id(binding['owner'])
                    if not source.execute('SELECT 1 FROM owners WHERE id=?',(owner,)).fetchone():
                        raise ValueError('Registered owner missing from quarantine.')
                    source.execute('INSERT INTO bindings VALUES(?,?,1)',(principal,owner))
                    source.execute('UPDATE store_meta SET sequence=sequence+1 WHERE id=1')
                anchor,digest = self._publish(db,candidate,cancelled)
                grant = WriterGrant(lineage,_integer(expected_epoch+1),writer,secrets.token_bytes(32))
                db.execute('UPDATE writers SET epoch=?,writer=?,token_sha256=?,live_sha256=? WHERE lineage=?',
                           (grant.epoch,writer,hashlib.sha256(grant.token).hexdigest(),digest,lineage))
                db.execute('DELETE FROM recoveries WHERE lineage=?',(lineage,))
                turn.check();self._approval(approved,cancelled)
        reply = dict(anchor=anchor,grant=grant,active_bindings=1,resumed_jobs=0,quarantined=False)
        if self._witness is not None:
            turn.check();reply['witness_confirmed'] = True
        return reply
