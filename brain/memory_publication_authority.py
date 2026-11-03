"""Opt-in FAKE-DATA authority: acknowledgement waits for recovery publication.

Local trusted SQLite stores only. No production caller or independent host is
configured. Schema 5 prevents older authorities from ignoring this binding.
"""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import secrets
import time

from brain.memory_authority import SyntheticAuthority
from brain.memory_custody import WitnessState,open_keys,_blob as key_blob,_cipher
from brain.memory_prototype import Conflict,_id,_json,_unlinked
from brain.memory_recovery import _publish,_unique
from brain.memory_recovery_latest import RecoveryHead,SyntheticRecoveryLatest,_decode
from brain.memory_recovery_pack import RecoveryPins,NAMES,MAX_PACK_BYTES,inspect_pack
from brain.memory_recovery_trust import seal_trust,open_trust,_blob as trust_blob,_pins


def _marker(operation,head):
    return _json({'publication_operation':_id(operation),'previous_head':asdict(head)})


def _reservation(raw,head):
    try:
        data=json.loads(raw,object_pairs_hook=_unique)
        if type(data) is not dict or set(data)!={'publication_operation','previous_head'}:raise ValueError('Wrong reservation.')
        operation=_id(data['publication_operation'])
        if _marker(operation,head)!=raw:raise ValueError('Wrong reservation predecessor.')
        return operation
    except (ValueError,TypeError,KeyError):raise Conflict('Publication reservation differs.') from None


def _transition(old,new):
    if (old.keys_digest!=new.keys_digest or old.state.anchor.lineage!=new.state.anchor.lineage
            or new.state.anchor.sequence<old.state.anchor.sequence or new.state.writer_epoch<old.state.writer_epoch
            or (new.state.anchor.sequence==old.state.anchor.sequence
                and (new.state.anchor!=old.state.anchor or new.backup_sha256!=old.backup_sha256))):
        raise Conflict('Publication source moved backwards or diverged.')


class SyntheticPublicationAuthority(SyntheticAuthority):
    def __init__(self,path,*,latest,publications,capsule,unlock_key,recovery,storage_key,synthetic_only=False,clock=time.time):
        if synthetic_only is not True:raise PermissionError('Explicit fake publication authority required.')
        if type(latest) is not SyntheticRecoveryLatest:raise ValueError('Existing exact latest store required.')
        path=Path(path).absolute();_unlinked(path)
        if not (path/'catalog.sqlite').is_file():raise ValueError('Existing authority required; never bootstrap on recovery.')
        self._latest=latest;self._publications=Path(publications).absolute();_unlinked(self._publications)
        if not self._publications.is_dir():raise ValueError('Existing explicit publication directory required.')
        self._capsule=Path(capsule).absolute();self._capsule_digest=hashlib.sha256(key_blob(self._capsule)).hexdigest()
        _cipher(unlock_key);self._unlock=unlock_key
        super().__init__(path,recovery=recovery,storage_key=storage_key,synthetic_only=True,clock=clock)

    def _schema(self,db):
        rows=[tuple(row) for row in db.execute('SELECT id,version FROM authority_meta')]
        if rows!=[(1,5)]:return super()._schema(db)
        db.execute('SELECT lineage,epoch,writer,token_sha256,live_sha256,storage_key_sha256 FROM writers LIMIT 0')
        db.execute('SELECT lineage,principal_sha256,owner FROM owner_bindings LIMIT 0')
        db.execute('SELECT lineage,epoch,anchor_sha256,restored_sha256 FROM recoveries LIMIT 0')
        db.execute('SELECT lineage,confirmed_head,operation_id,next_pins FROM publication_links LIMIT 0')
        return 5

    def register(self,*args,**kwargs):raise PermissionError('Bootstrap with the existing authority, then explicitly bind publication.')

    def activate_restored(self,lineage,restored,turn,writer,*,expected_anchor,expected_epoch,
                          approved=False,cancelled=lambda:False):
        reply=super().activate_restored(lineage,restored,turn,writer,expected_anchor=expected_anchor,
            expected_epoch=expected_epoch,approved=approved,cancelled=cancelled)
        turn.check();self._approval(approved,cancelled)
        return {**reply,'publication_confirmed':True}

    def _inputs(self,db,lineage):
        writer,anchor,_,backup,checkpoint,row=self._entry(db,lineage)
        pins=RecoveryPins(WitnessState(anchor,writer['epoch']),self._capsule_digest,row['backup_sha256'])
        keys=open_keys(self._capsule,self._unlock,lineage=lineage,trusted_digest=self._capsule_digest,synthetic_only=True,approved=True)
        if keys.storage_key!=self._key or hashlib.sha256(keys.recovery_key).hexdigest()!=self._recovery.key_id:
            raise ValueError('Capsule keys differ from this authority.')
        return pins,row,dict(zip(NAMES,(backup,checkpoint,self._capsule)))

    def _stage(self,pins,row,paths,initial_trust=None):
        home=self._publications/(_id(row['object_id'])+'-'+str(pins.state.writer_epoch));_unlinked(home);home.mkdir(exist_ok=True)
        folder=home/'pack';_unlinked(folder);folder.mkdir(exist_ok=True);remaining=MAX_PACK_BYTES
        expected=dict(zip(NAMES,(pins.backup_sha256,pins.state.anchor.sha256,pins.keys_digest)))
        for name in NAMES:
            _unlinked(paths[name])
            with paths[name].open('rb') as source:blob=source.read(remaining+1)
            if len(blob)>remaining or hashlib.sha256(blob).hexdigest()!=expected[name]:raise ValueError('Bounded publication source differs.')
            remaining-=len(blob);target=folder/name;_unlinked(target)
            if target.exists():
                with target.open('rb') as source:existing=source.read(len(blob)+1)
                if existing!=blob:raise Conflict('Existing publication differs; refusing overwrite.')
            else:_publish(target,lambda stage,data=blob:stage.write_bytes(data),lambda:False)
        record=home/'trust.enc';_unlinked(record)
        if initial_trust is not None:
            if record.exists():
                if trust_blob(record)!=initial_trust:raise Conflict('Existing trust record differs.')
            else:_publish(record,lambda stage:stage.write_bytes(initial_trust),lambda:False)
        elif not record.exists():seal_trust(record,pins,self._unlock,synthetic_only=True,approved=True)
        digest=hashlib.sha256(trust_blob(record)).hexdigest()
        if open_trust(record,self._unlock,trusted_digest=digest,synthetic_only=True,approved=True)!=pins:
            raise Conflict('Published trust differs from the canonical source.')
        inspect_pack(folder,pins=pins,unlock_key=self._unlock,synthetic_only=True,approved=True)
        return RecoveryHead(pins,digest),folder,record

    def bind_publication(self,lineage,trust_path,*,approved=False):
        self._approval(approved,lambda:False)
        with self._repository._db() as db:
            if self._schema(db)!=2:raise Conflict('Bind only a previously bootstrapped unwitnessed authority.')
            if db.execute('SELECT COUNT(*) FROM latest').fetchone()[0]!=1:raise Conflict('This cutover supports exactly one registered lineage.')
            if db.execute('SELECT 1 FROM recoveries WHERE lineage=?',(_id(lineage),)).fetchone():raise Conflict('Recovery already pending.')
            pins,row,paths=self._inputs(db,lineage)
            with self._latest._db() as trusted:
                head=self._latest._confirmed(trusted,lineage)
                if head.pins!=pins:raise Conflict('Latest publication does not match the source.')
                if open_trust(trust_path,self._unlock,trusted_digest=head.trust_digest,synthetic_only=True,approved=True)!=pins:
                    raise Conflict('Initial trust differs.')
                staged,_,_=self._stage(pins,row,paths,trust_blob(trust_path))
                if staged!=head:raise Conflict('Initial staged publication differs.')
            db.execute('CREATE TABLE publication_links(lineage TEXT PRIMARY KEY, confirmed_head TEXT NOT NULL, operation_id TEXT, next_pins TEXT)')
            db.execute('INSERT INTO publication_links VALUES(?,?,NULL,NULL)',(lineage,_json(asdict(head))))
            db.execute('UPDATE authority_meta SET version=5 WHERE id=1')
        return head

    def _link(self,db,lineage):
        if self._schema(db)!=5:raise PermissionError('Explicit publication binding required.')
        row=db.execute('SELECT * FROM publication_links WHERE lineage=?',(_id(lineage),)).fetchone()
        if not row:raise ValueError('Publication binding is missing; never recreate it.')
        head=_decode(row['confirmed_head'])
        if head is None or head.pins.state.anchor.lineage!=lineage:raise ValueError('Wrong publication lineage.')
        pins,entry,paths=self._inputs(db,lineage)
        if row['operation_id'] is None:
            if row['next_pins'] is not None or pins!=head.pins:raise Conflict('Source changed outside its publication journal.')
        else:
            _id(row['operation_id'])
            target=_pins(json.loads(row['next_pins'],object_pairs_hook=_unique));_transition(head.pins,target)
            if target!=pins:raise Conflict('Committed source differs from its publication journal.')
        return row,head,pins,entry,paths

    @contextmanager
    def _transaction(self,lineage,cancelled=lambda:False):
        self._approval(True,cancelled)
        with self._repository._db() as db:
            row,head,_,_,_=self._link(db,lineage)
            if row['operation_id'] is not None:raise Conflict('Publication pending; reconcile before another operation.')
            operation=secrets.token_hex(16)
            with self._latest._db() as trusted:
                if self._latest._confirmed(trusted,lineage)!=head:raise Conflict('Latest state changed outside the authority.')
                trusted.execute('UPDATE heads SET pending=? WHERE lineage=?',(_marker(operation,head),lineage))
                self._approval(True,cancelled)
            yield db
            target,_,_=self._inputs(db,lineage);_transition(head.pins,target)
            db.execute('UPDATE publication_links SET operation_id=?,next_pins=? WHERE lineage=?',
                (operation,_json({'version':1,'pins':asdict(target)}),lineage))
            self._approval(True,cancelled)
        self._approval(True,cancelled)
        with self._repository._db() as db:self._complete(db,lineage,cancelled,operation,target)
        self._approval(True,cancelled)

    def _complete(self,db,lineage,cancelled,expected_operation=None,expected_target=None):
        row,head,pins,entry,paths=self._link(db,lineage)
        if expected_target is not None and pins!=expected_target:raise Conflict('Source advanced before acknowledgement.')
        if expected_operation is not None and row['operation_id'] not in (None,expected_operation):raise Conflict('Operation was superseded.')
        with self._latest._db() as trusted:
            raw=trusted.execute('SELECT confirmed,pending FROM heads WHERE lineage=?',(lineage,)).fetchone()
            if not raw:raise ValueError('Latest trust is missing.')
            current=_decode(raw[0]);pending=raw[1]
            if pending is not None:
                operation=_reservation(pending,head)
                if current!=head or (row['operation_id'] is not None and operation!=row['operation_id']):raise Conflict('Reservation changed.')
                if expected_operation is not None and operation!=expected_operation:raise Conflict('Reservation was superseded.')
            elif current is None or current.pins!=pins:raise Conflict('Confirmed latest state differs.')
            staged,folder,record=self._stage(pins,entry,paths)
            if pins==head.pins and staged!=head:raise Conflict('Unchanged source requires its exact prior trust record.')
            if pending is None and current!=staged:raise Conflict('Confirmed trust fingerprint differs.')
            trusted.execute('UPDATE heads SET confirmed=?,pending=NULL WHERE lineage=?',(_json(asdict(staged)),lineage))
            self._approval(True,cancelled)
        db.execute('UPDATE publication_links SET confirmed_head=?,operation_id=NULL,next_pins=NULL WHERE lineage=?',(_json(asdict(staged)),lineage))
        self._approval(True,cancelled)
        return staged,folder,record

    def reconcile_publication(self,lineage,*,approved=False,cancelled=lambda:False):
        self._approval(approved,cancelled)
        # The source writer lock proves commit or rollback before releasing the recovery reservation.
        with self._repository._db() as db:head,_,_=self._complete(db,lineage,cancelled)
        return {'anchor':head.pins.state.anchor,'writer_epoch':head.pins.state.writer_epoch,
                'publication_confirmed':True,'synthetic_only':True}

    def handle(self,grant,turn,request,*,expected_anchor,approved=False,cancelled=lambda:False):
        reply=super().handle(grant,turn,request,expected_anchor=expected_anchor,approved=approved,cancelled=cancelled)
        turn.check();self._approval(approved,cancelled)
        return {**reply,'publication_confirmed':True}

    def head(self,lineage):
        with self._repository._db() as db:
            row,head,_,_,_=self._link(db,lineage)
            if row['operation_id'] is not None:raise Conflict('Publication is pending.')
            if self._latest.head(lineage)!=head:raise Conflict('Latest publication differs.')
            writer,anchor,*_=self._entry(db,lineage,live=False)
            return {'anchor':anchor,'writer_epoch':writer['epoch'],'writer_active':writer['token_sha256'] is not None,
                'recovery_pending':db.execute('SELECT 1 FROM recoveries WHERE lineage=?',(lineage,)).fetchone() is not None,
                'publication_confirmed':True,'synthetic_only':True}
