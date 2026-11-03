"""Fake-data transport of existing encrypted artifacts; independent trust stays outside."""
from dataclasses import dataclass
import hashlib
from itertools import islice
from pathlib import Path
import time

from brain.memory_custody import WitnessState, SyntheticWitness, open_keys, _approval
from brain.memory_prototype import _id, _unlinked
from brain.memory_recovery import SyntheticRecovery, HEAD_FIELDS, _publish

NAMES=('backup.enc','checkpoint.enc','keys.enc')
MAX_PACK_BYTES=8*1024*1024


@dataclass(frozen=True)
class RecoveryPins:
    """Caller-supplied fresh independent observation; never learned from a pack."""
    state: WitnessState
    keys_digest: str
    backup_sha256: str

    def __post_init__(self):
        SyntheticWitness._state(self.state)
        _id(self.keys_digest,64);_id(self.backup_sha256,64)


def _paths(folder):
    folder=Path(folder).absolute();_unlinked(folder)
    if not folder.is_dir() or {p.name for p in islice(folder.iterdir(),4)}!=set(NAMES):
        raise ValueError('A pack must contain exactly the three encrypted artifacts.')
    return {name:folder/name for name in NAMES}


def _verified(paths,pins,unlock_key,cancelled,clock=time.time):
    if type(pins) is not RecoveryPins:raise ValueError('Independent recovery pins required.')
    pins.__post_init__();remaining=MAX_PACK_BYTES;blobs={}
    for name in NAMES:
        if cancelled():raise InterruptedError('Recovery pack cancelled.')
        path=Path(paths[name]);_unlinked(path)
        with path.open('rb') as source:blob=source.read(remaining+1)
        if len(blob)>remaining:raise ValueError('Recovery pack byte budget exceeded.')
        blobs[name]=blob;remaining-=len(blob)
    for name,digest in (('backup.enc',pins.backup_sha256),('checkpoint.enc',pins.state.anchor.sha256),('keys.enc',pins.keys_digest)):
        if hashlib.sha256(blobs[name]).hexdigest()!=digest:raise ValueError('Pack differs from independent recovery pins.')
    keys=open_keys(paths['keys.enc'],unlock_key,lineage=pins.state.anchor.lineage,
                   trusted_digest=pins.keys_digest,synthetic_only=True,approved=True,cancelled=cancelled)
    recovery=SyntheticRecovery(keys.recovery_key,synthetic_only=True,clock=clock)
    saved,current,records,heads,_=recovery._restore_inputs(paths['backup.enc'],paths['checkpoint.enc'],
        pins.state.anchor,backup_sha256=pins.backup_sha256)
    if (saved['sequence']!=current['sequence'] or saved['owners']!=current['owners'] or set(records)!=set(heads)
            or any(any(row[key]!=heads[mid][key] for key in HEAD_FIELDS) for mid,row in records.items())):
        raise ValueError('Transport requires one complete acknowledged snapshot.')
    if cancelled():raise InterruptedError('Recovery pack cancelled.')
    return recovery,keys,blobs


def inspect_pack(folder,*,pins,unlock_key,synthetic_only=False,approved=False,cancelled=lambda:False):
    _approval(synthetic_only,approved,cancelled)
    _,_,blobs=_verified(_paths(folder),pins,unlock_key,cancelled)
    return {'verified':True,'encrypted_bytes':sum(map(len,blobs.values())),'synthetic_only':True}


def stage_pack(destination,*,backup,checkpoint,capsule,pins,unlock_key,
               synthetic_only=False,approved=False,cancelled=lambda:False):
    _approval(synthetic_only,approved,cancelled)
    _,_,blobs=_verified(dict(zip(NAMES,(backup,checkpoint,capsule))),pins,unlock_key,cancelled)
    destination=Path(destination).absolute();_unlinked(destination);destination.mkdir()
    for name,blob in blobs.items():
        _publish(destination/name,lambda path,data=blob:path.write_bytes(data),cancelled)
    # shortcut: per-file atomic publication; a partial directory has no transfer acknowledgement.
    return inspect_pack(destination,pins=pins,unlock_key=unlock_key,synthetic_only=True,
                        approved=True,cancelled=cancelled)


def restore_pack(folder,destination,*,pins,unlock_key,synthetic_only=False,approved=False,
                 cancelled=lambda:False,clock=time.time):
    _approval(synthetic_only,approved,cancelled)
    paths=_paths(folder);recovery,keys,_=_verified(paths,pins,unlock_key,cancelled,clock)
    return recovery.restore(paths['backup.enc'],paths['checkpoint.enc'],destination,
        trusted_anchor=pins.state.anchor,trusted_backup_sha256=pins.backup_sha256,
        storage_key=keys.storage_key,approved=True,cancelled=cancelled)
