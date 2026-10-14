"""FAKE-DATA authority coordinator for the loopback witness; no deployed callers."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
from pathlib import Path
import secrets
import time

from brain.memory_authority import SyntheticAuthority
from brain.memory_custody import SyntheticWitness
from brain.memory_prototype import Conflict, _id, _json
from brain.memory_recovery import _integer
from brain.memory_witness_service import SyntheticWitnessClient


class SyntheticNetworkAuthority(SyntheticAuthority):
    """Reuse authority operations; schema 4 owns durable network operation intent."""
    def __init__(self, path, *, client, recovery, storage_key, synthetic_only=False, clock=time.time):
        if synthetic_only is not True:raise PermissionError('Explicit fake-data coordinator opt-in required.')
        if type(client) is not SyntheticWitnessClient:raise ValueError('Exact loopback witness client required.')
        if not (Path(path)/'catalog.sqlite').is_file():raise ValueError('Bootstrap locally before network binding; never recreate trust.')
        self._client = client
        super().__init__(path,recovery=recovery,storage_key=storage_key,synthetic_only=True,clock=clock)
        self._witness = client  # Reused authority replies retain their post-commit identity checks.

    def _schema(self, db):
        rows = [tuple(row) for row in db.execute('SELECT id,version FROM authority_meta')]
        if rows==[(1,2)]:return super()._schema(db)
        if rows!=[(1,4)]:raise ValueError('Explicit local schema-2 or network schema-4 authority required.')
        db.execute('SELECT lineage,epoch,writer,token_sha256,live_sha256,storage_key_sha256 FROM writers LIMIT 0')
        db.execute('SELECT lineage,principal_sha256,owner FROM owner_bindings LIMIT 0')
        db.execute('SELECT lineage,epoch,anchor_sha256,restored_sha256 FROM recoveries LIMIT 0')
        links = db.execute('SELECT * FROM network_links').fetchall()
        if len(links)!=1:raise ValueError('Pinned network binding unavailable; never recreate it.')
        row = links[0]
        if (row['lineage'],row['service'],row['client'],row['protocol_key_sha256'])!=self._identity():
            raise ValueError('Network identity or protocol key changed.')
        return 4

    def _identity(self):
        c = self._client
        return c.lineage,c.service,c.client,hashlib.sha256(c._key).hexdigest()

    def bind_witness(self, lineage, keys_digest, *, approved=False):
        """Explicit one-lineage cutover; no migration from local witnessed schema 3."""
        self._approval(approved,lambda:False);_id(lineage);_id(keys_digest,64)
        if lineage!=self._client.lineage:raise ValueError('Wrong configured lineage.')
        with self._repository._db() as db:
            if self._schema(db)!=2:raise Conflict('Network witness already bound.')
            state = self._witness_state(db,lineage);self._entry(db,lineage)
            head = self._client.observe()
            self._expect(head,state,keys_digest,None,head['generation'])
            db.execute('''CREATE TABLE network_links(lineage TEXT PRIMARY KEY,service TEXT NOT NULL,client TEXT NOT NULL,
                protocol_key_sha256 TEXT NOT NULL,keys_digest TEXT NOT NULL,previous_state TEXT NOT NULL,next_state TEXT NOT NULL,
                generation INTEGER NOT NULL,operation_id TEXT,finish_id TEXT,reserved_generation INTEGER,
                phase TEXT NOT NULL CHECK(phase IN ('idle','intent','prepared','committed')))''')
            encoded = _json(asdict(state))
            db.execute('INSERT INTO network_links VALUES(?,?,?,?,?,?,?,?,NULL,NULL,NULL,?)',
                       (*self._identity(),keys_digest,encoded,encoded,head['generation'],'idle'))
            db.execute('UPDATE authority_meta SET version=4 WHERE id=1')
        return state

    @staticmethod
    def _expect(head, state, digest, reservation, generation):
        if head!=dict(state=state,keys_digest=digest,reservation_id=reservation,generation=generation):
            raise Conflict('Witness state, custody or reservation generation differs.')

    def _link(self, db, lineage, operation=None):
        if self._schema(db)!=4:raise PermissionError('Explicit network witness binding required.')
        row = db.execute('SELECT * FROM network_links WHERE lineage=?',(_id(lineage),)).fetchone()
        if not row:raise ValueError('Wrong bound lineage.')
        previous,target = [SyntheticWitness._state(SyntheticWitness._decode(row[name],lineage))
                           for name in ('previous_state','next_state')]
        _id(row['keys_digest'],64);_integer(row['generation'])
        phase = row['phase']
        if phase=='idle':
            if any(row[name] is not None for name in ('operation_id','finish_id','reserved_generation')) or previous!=target:
                raise ValueError('Malformed idle network journal.')
        elif phase in ('intent','prepared','committed'):
            _id(row['operation_id']);_id(row['finish_id'])
            if row['operation_id']==row['finish_id']:raise ValueError('Distinct prepare and finish identities required.')
            if phase=='intent':
                if row['reserved_generation'] is not None:raise ValueError('Malformed operation intent.')
            elif _integer(row['reserved_generation'],1)!=row['generation']+1:
                raise ValueError('Malformed reservation generation.')
            if phase!='committed' and previous!=target:raise ValueError('Uncommitted operation changed its target.')
        else:raise ValueError('Unknown operation phase.')
        if operation is not None and row['operation_id']!=operation:raise Conflict('Operation was reconciled or superseded.')
        if self._witness_state(db,lineage)!=target:raise Conflict('Source changed outside its durable operation journal.')
        return row,previous,target

    def _begin(self, lineage, cancelled):
        self._approval(True,cancelled)
        with self._repository._db() as db:
            row,_,state = self._link(db,lineage)
            if row['phase']!='idle':raise Conflict('Pending operation; explicit approved reconciliation required.')
            self._expect(self._client.observe(require_prepare_capacity=True),state,row['keys_digest'],None,row['generation'])
            operation,finish = secrets.token_hex(16),secrets.token_hex(16)
            db.execute("UPDATE network_links SET operation_id=?,finish_id=?,phase='intent' WHERE lineage=?",
                       (operation,finish,lineage))
            self._approval(True,cancelled)
        return operation

    def _reserve(self, lineage, operation, cancelled):
        with self._repository._db() as db:
            row,previous,_ = self._link(db,lineage,operation)
            if row['phase']!='intent':raise Conflict('Operation already resumed or resolved.')
            reserved = self._client.prepare(previous,row['keys_digest'],request_id=operation,expected_generation=row['generation'])
            generation = _integer(row['generation']+1)
            self._expect(reserved,previous,row['keys_digest'],operation,generation)
            db.execute("UPDATE network_links SET reserved_generation=?,phase='prepared' WHERE lineage=?",(generation,lineage))
            self._approval(True,cancelled)

    def _finish(self, db, lineage, operation):
        row,previous,target = self._link(db,lineage,operation)
        if row['phase']=='idle':raise Conflict('No pending operation.')
        # The source writer lock and journal prove rollback before any unchanged finish.
        self._entry(db,lineage,live=False)
        generation = _integer(row['generation']+1)
        digest = row['keys_digest'];head = self._client.observe()
        if row['phase']=='intent' and head==dict(state=previous,keys_digest=digest,reservation_id=None,generation=row['generation']):
            head = self._client.prepare(previous,digest,request_id=operation,expected_generation=row['generation'])
        if head['reservation_id'] is not None:
            self._expect(head,previous,digest,operation,generation)
        else:
            # A lost finish reply needs its exact signed receipt, not head-only acceptance.
            self._expect(head,target,digest,None,generation)
        reservation = dict(reservation_id=operation,generation=generation)
        confirmed = self._client.finish(reservation,previous,target,digest,request_id=row['finish_id'])
        self._expect(confirmed,target,digest,None,generation)
        encoded = _json(asdict(target))
        db.execute("""UPDATE network_links SET previous_state=?,next_state=?,generation=?,operation_id=NULL,
            finish_id=NULL,reserved_generation=NULL,phase='idle' WHERE lineage=?""",(encoded,encoded,generation,lineage))
        return target

    @contextmanager
    def _transaction(self, lineage, cancelled=lambda:False):
        operation = self._begin(lineage,cancelled)  # Intent commits before any prepare request.
        self._reserve(lineage,operation,cancelled)  # Persist the remote fencing generation before source mutation.
        with self._repository._db() as db:
            row,previous,_ = self._link(db,lineage,operation)
            if row['phase']!='prepared':raise Conflict('Operation cannot mutate in this phase.')
            self._expect(self._client.observe(),previous,row['keys_digest'],operation,row['reserved_generation'])
            self._approval(True,cancelled)
            yield db
            target = self._witness_state(db,lineage)
            db.execute("UPDATE network_links SET next_state=?,phase='committed' WHERE lineage=?",
                       (_json(asdict(target)),lineage))
            self._approval(True,cancelled)
        self._approval(True,cancelled)
        with self._repository._db() as db:
            self._finish(db,lineage,operation)
            self._approval(True,cancelled)
        self._approval(True,cancelled)

    def reconcile_witness(self, lineage, *, approved=False, cancelled=lambda:False):
        """Resolve only recorded outcomes; never replay a request, content or writer token."""
        self._approval(approved,cancelled)
        with self._repository._db() as db:
            row,_,target = self._link(db,lineage)
            if row['phase']=='idle':
                self._entry(db,lineage,live=False)
                self._expect(self._client.observe(),target,row['keys_digest'],None,row['generation'])
            else:target = self._finish(db,lineage,row['operation_id'])
            self._approval(approved,cancelled)
        self._approval(approved,cancelled)
        return dict(anchor=target.anchor,writer_epoch=target.writer_epoch,witness_confirmed=True,synthetic_only=True)

    def retire_receipts(self, lineage, *, approved=False, cancelled=lambda:False):
        """Acknowledge only a locally confirmed generation; never discard pending recovery evidence."""
        self._approval(approved,cancelled)
        with self._repository._db() as db:
            row,_,state = self._link(db,lineage)
            if row['phase']!='idle':raise Conflict('Resolve the pending source operation before retiring receipts.')
            self._entry(db,lineage,live=False)
            self._expect(self._client.observe(),state,row['keys_digest'],None,row['generation'])
            self._approval(approved,cancelled)
            result = self._client.retire(state,row['keys_digest'],generation=row['generation'])
            generation = result.pop('retired_generation')
            self._expect(result,state,row['keys_digest'],None,row['generation'])
            if generation!=row['generation']:raise Conflict('Wrong confirmed retirement generation.')
            self._approval(approved,cancelled)
        self._approval(approved,cancelled)
        return dict(anchor=state.anchor,writer_epoch=state.writer_epoch,retired_generation=generation,
                    witness_confirmed=True,synthetic_only=True)
