"""Portable FAKE-DATA pins; separate unlock and current trusted digest are mandatory.

An authenticated old record is still old. Never learn its trusted digest from the
backup, this record, or an old transfer receipt. No independent custody is deployed.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from cryptography.fernet import InvalidToken
from brain.memory_custody import WitnessState, _approval, _cipher
from brain.memory_prototype import _id, _json, _unlinked
from brain.memory_recovery import CheckpointAnchor, _publish, _unique
from brain.memory_recovery_pack import RecoveryPins

MAGIC=b'LYA-FAKE-RECOVERY-TRUST-1\n'
MAX_BYTES=8192


def _blob(path):
    path=Path(path).absolute();_unlinked(path)
    with path.open('rb') as source:blob=source.read(MAX_BYTES+1)
    if len(blob)>MAX_BYTES or not blob.startswith(MAGIC):raise ValueError('Invalid bounded recovery trust record.')
    return blob


def _pins(data):
    if (type(data) is not dict or set(data)!={'version','pins'}
            or type(data['version']) is not int or data['version']!=1):raise ValueError('Wrong trust schema.')
    pins=data['pins']
    if type(pins) is not dict or set(pins)!={'state','keys_digest','backup_sha256'}:raise ValueError('Wrong pins fields.')
    state=pins['state']
    if (type(state) is not dict or set(state)!={'anchor','writer_epoch'}
            or type(state['anchor']) is not dict):raise ValueError('Wrong witness fields.')
    return RecoveryPins(WitnessState(CheckpointAnchor(**state['anchor']),state['writer_epoch']),
                        pins['keys_digest'],pins['backup_sha256'])


def open_trust(path,unlock_key,*,trusted_digest,synthetic_only=False,approved=False,cancelled=lambda:False):
    """Return pins only after exact independently supplied current-digest verification."""
    _approval(synthetic_only,approved,cancelled);_id(trusted_digest,64)
    blob=_blob(path)
    if hashlib.sha256(blob).hexdigest()!=trusted_digest:raise ValueError('Recovery trust differs from the independent digest.')
    try:pins=_pins(json.loads(_cipher(unlock_key).decrypt(blob[len(MAGIC):]),object_pairs_hook=_unique))
    except (InvalidToken,ValueError,TypeError,KeyError,UnicodeError,RecursionError):
        raise ValueError('Recovery trust authentication/schema failed; details withheld.') from None
    _approval(synthetic_only,approved,cancelled)
    return pins


def seal_trust(destination,pins,unlock_key,*,synthetic_only=False,approved=False,cancelled=lambda:False):
    """Create a new encrypted pins record; caller protects the returned digest separately."""
    _approval(synthetic_only,approved,cancelled)
    if type(pins) is not RecoveryPins:raise ValueError('Independent recovery pins required.')
    pins.__post_init__()
    blob=MAGIC+_cipher(unlock_key).encrypt(_json({'version':1,'pins':asdict(pins)}).encode())
    if len(blob)>MAX_BYTES:raise ValueError('Recovery trust byte budget exceeded.')
    digest=hashlib.sha256(blob).hexdigest()
    def check(path):
        if open_trust(path,unlock_key,trusted_digest=digest,synthetic_only=True,approved=True,cancelled=cancelled)!=pins:
            raise ValueError('Recovery trust readback differs.')
    def write(stage):Path(stage).write_bytes(blob);check(stage)
    _publish(destination,write,cancelled);check(destination)
    return digest
