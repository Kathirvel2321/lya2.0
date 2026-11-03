"""FAKE-DATA full-authority survival drill; no real enrollment or runtime cutover.

The envelope never establishes its own freshness. An independently current latest
store and separately trusted envelope/capsule fingerprints must survive.
"""
import base64
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

from cryptography.fernet import InvalidToken
from brain.memory_custody import _approval,_cipher,open_keys
from brain.memory_prototype import Conflict,_id,_json,_unlinked
from brain.memory_publication_authority import SyntheticPublicationAuthority
from brain.memory_recovery import SyntheticRecovery,_publish,_unique
from brain.memory_recovery_latest import SyntheticRecoveryLatest,_decode

MAGIC=b'LYA-FAKE-AUTHORITY-TRANSFER-1\n'
MAX_RAW=16*1024**2
MAX_BLOB=32*1024**2
NAMES={'catalog.sqlite','live.sqlite','backup.enc','checkpoint.enc','keys.enc','trust.enc'}
MARKER='RECOVERY-INCOMPLETE'


def _read(path,limit):
    path=Path(path).absolute();_unlinked(path)
    with path.open('rb') as source:blob=source.read(limit+1)
    if len(blob)>limit:raise ValueError('Authority transfer byte budget exceeded.')
    return blob


def seal_authority(authority,destination,*,lineage,synthetic_only=False,approved=False,cancelled=lambda:False):
    _approval(synthetic_only,approved,cancelled)
    if type(authority) is not SyntheticPublicationAuthority:raise ValueError('Exact bound fake authority required.')
    with authority._repository._db() as db:
        row,head,_,entry,paths=authority._link(db,lineage)
        if row['operation_id'] is not None:raise Conflict('Reconcile before capturing authority.')
        if db.execute('SELECT 1 FROM recoveries').fetchone():raise Conflict('Complete pending owner recovery before capture.')
        if db.execute('SELECT COUNT(*) FROM latest').fetchone()[0]!=1:raise ValueError('Exactly one lineage required.')
        with authority._latest._db() as trusted:
            if authority._latest._confirmed(trusted,lineage)!=head:raise Conflict('Latest publication differs.')
            staged,_,record=authority._stage(head.pins,entry,paths)
            if staged!=head:raise Conflict('Published trust differs.')
            if db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0]>4*1024**2:
                raise ValueError('Authority catalogue byte budget exceeded.')
            files={'catalog.sqlite':db.serialize()};remaining=MAX_RAW-len(files['catalog.sqlite'])
            sources={**paths,'live.sqlite':authority._repository.path/'objects'/entry['object_id']/'live.sqlite','trust.enc':record}
            for name,path in sources.items():
                files[name]=_read(path,remaining);remaining-=len(files[name])
            payload=dict(version=1,head=asdict(head),object_id=entry['object_id'],
                files={name:base64.b64encode(blob).decode('ascii') for name,blob in files.items()})
            blob=MAGIC+_cipher(authority._unlock).encrypt(_json(payload).encode())
            if len(blob)>MAX_BLOB:raise ValueError('Sealed authority byte budget exceeded.')
            _approval(synthetic_only,approved,cancelled)
    digest=hashlib.sha256(blob).hexdigest()
    _publish(destination,lambda path:path.write_bytes(blob),cancelled)
    if hashlib.sha256(_read(destination,MAX_BLOB)).hexdigest()!=digest:raise ValueError('Authority envelope readback differs.')
    return dict(head=head,sha256=digest,bytes=len(blob),synthetic_only=True)


def _open_authority(home,latest,unlock_key,lineage,capsule_digest,clock):
    keys=open_keys(home/'keys.enc',unlock_key,lineage=lineage,trusted_digest=capsule_digest,synthetic_only=True,approved=True)
    return SyntheticPublicationAuthority(home/'authority',latest=latest,publications=home/'publications',
        capsule=home/'keys.enc',unlock_key=unlock_key,
        recovery=SyntheticRecovery(keys.recovery_key,synthetic_only=True,clock=clock),storage_key=keys.storage_key,
        synthetic_only=True,clock=clock)


def _finish(home,authority,lineage,quarantine,approved,cancelled):
    if quarantine not in ('quarantine.sqlite','retry-quarantine.sqlite'):raise ValueError('Use an explicit fixed quarantine name.')
    target=home/quarantine;_unlinked(target)
    authority.reconcile_publication(lineage,approved=approved,cancelled=cancelled)
    with authority._repository._db() as db:
        pending=db.execute('SELECT restored_sha256 FROM recoveries WHERE lineage=?',(lineage,)).fetchone()
        writer,anchor,*_=authority._entry(db,lineage,live=False)
        if pending:
            if writer['token_sha256'] is not None or writer['writer'] is not None:raise ValueError('Recovery writer is not fenced.')
            if hashlib.sha256(_read(target,MAX_RAW)).hexdigest()!=pending['restored_sha256']:
                raise ValueError('Acknowledged quarantine is missing or changed.')
    if not pending:authority.restore(lineage,target,expected_anchor=anchor,approved=approved,cancelled=cancelled)
    status=authority.head(lineage)
    if status['writer_active'] or not status['recovery_pending']:raise Conflict('Recovered authority is not fenced.')
    _approval(True,approved,cancelled)
    (home/MARKER).unlink()
    return dict(anchor=status['anchor'],writer_epoch=status['writer_epoch'],quarantine=str(target),
        publication_confirmed=True,quarantined=True,active_bindings=0,resumed_jobs=0,synthetic_only=True)


def restore_authority(bundle,destination,*,latest,lineage,unlock_key,trusted_digest,
                      synthetic_only=False,approved=False,cancelled=lambda:False,clock=time.time):
    """Restore a new private directory, fence writers, then expose recovery metadata only."""
    _approval(synthetic_only,approved,cancelled);_id(lineage);_id(trusted_digest,64)
    if type(latest) is not SyntheticRecoveryLatest:raise ValueError('Independent exact latest store required.')
    head=latest.head(lineage);blob=_read(bundle,MAX_BLOB)
    if not blob.startswith(MAGIC) or hashlib.sha256(blob).hexdigest()!=trusted_digest:raise ValueError('Authority envelope fingerprint differs.')
    try:
        data=json.loads(_cipher(unlock_key).decrypt(blob[len(MAGIC):]),object_pairs_hook=_unique)
        if (type(data) is not dict or set(data)!={'version','head','object_id','files'}
                or type(data['version']) is not int or data['version']!=1):raise ValueError('Wrong authority envelope schema.')
        if _decode(_json(data['head']))!=head:raise Conflict('Envelope is not the independent latest publication.')
        object_id=_id(data['object_id'])
        if type(data['files']) is not dict or set(data['files'])!=NAMES:raise ValueError('Wrong fixed authority files.')
        files={name:base64.b64decode(value,validate=True) for name,value in data['files'].items() if type(value) is str}
        if set(files)!=NAMES or sum(map(len,files.values()))>MAX_RAW or len(files['catalog.sqlite'])>4*1024**2:
            raise ValueError('Authority file byte budget exceeded.')
    except (InvalidToken,TypeError,KeyError,UnicodeError,RecursionError):
        raise ValueError('Authority authentication/schema refused; details withheld.') from None
    home=Path(destination).absolute();_unlinked(home)
    _approval(synthetic_only,approved,cancelled);home.mkdir(mode=0o700)
    (home/MARKER).write_text('Incomplete fake recovery. Preserve for explicit reconciliation.\n',encoding='utf-8')
    paths={'catalog.sqlite':home/'authority/catalog.sqlite','live.sqlite':home/'authority/objects'/object_id/'live.sqlite',
        'backup.enc':home/'authority/objects'/object_id/'backup.enc','checkpoint.enc':home/'authority/objects'/object_id/'checkpoint.enc',
        'keys.enc':home/'keys.enc','trust.enc':home/'publications'/(object_id+'-'+str(head.pins.state.writer_epoch))/'trust.enc'}
    for name,path in paths.items():
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(files[name])
    folder=paths['trust.enc'].parent/'pack';folder.mkdir()
    for name in ('backup.enc','checkpoint.enc','keys.enc'):(folder/name).write_bytes(files[name])
    authority=_open_authority(home,latest,unlock_key,lineage,head.pins.keys_digest,clock)
    return _finish(home,authority,lineage,'quarantine.sqlite',approved,cancelled)


def resume_authority(destination,*,latest,lineage,unlock_key,trusted_capsule_digest,quarantine='quarantine.sqlite',
                     synthetic_only=False,approved=False,cancelled=lambda:False,clock=time.time):
    """Resolve only an existing incomplete recovery; never overwrite or bootstrap trust."""
    _approval(synthetic_only,approved,cancelled);_id(lineage);_id(trusted_capsule_digest,64)
    if type(latest) is not SyntheticRecoveryLatest:raise ValueError('Independent exact latest store required.')
    home=Path(destination).absolute();_unlinked(home);_unlinked(home/MARKER)
    if not (home/MARKER).is_file():raise ValueError('Existing incomplete recovery required.')
    authority=_open_authority(home,latest,unlock_key,lineage,trusted_capsule_digest,clock)
    return _finish(home,authority,lineage,quarantine,approved,cancelled)
