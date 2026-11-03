"""Owner-controlled Windows key custody; never enables the synthetic memory engine.

Only the native verifier supplies a freshly signed exact-action Challenge. No
network/model endpoint may construct this proof. Vault/offline copies are owner
acknowledgements, not an inspection of those external stores.
"""
import base64
from dataclasses import dataclass,field
import hashlib
import hmac
import json
import math
from pathlib import Path
import secrets
import sys
import time

from cryptography.fernet import Fernet
from brain.memory_prototype import _json,_unlinked,_id
from brain.memory_recovery import _publish,_unique
from security.approval import Challenge
from security.policy import Session

PREPARE='Prepare new LYA recovery keys locally; show the unlock only in this private window. No upload or memory cutover.'
CONFIRM='Confirm the LYA recovery unlock was read back from Bitwarden and a separate offline copy. No memory cutover.'
ENTROPY=b'LYA-OWNER-RECOVERY-KEYS-1'
MAGIC=b'LYA-OWNER-RECOVERY-DPAPI-1\n'
CAPSULE_MAGIC=b'LYA-OWNER-RECOVERY-CAPSULE-1\n'
LIMIT=16384


@dataclass(frozen=True)
class KeyView:
    lineage:str
    capsule_sha256:str
    custody_acknowledged:bool
    unlock_key:bytes=field(repr=False)


def _protect(raw):
    if sys.platform!='win32':raise OSError('Windows DPAPI required; no plaintext fallback.')
    import win32crypt
    return win32crypt.CryptProtectData(raw,'LYA owner recovery',ENTROPY,None,None,1)


def _unprotect(blob):
    if sys.platform!='win32':raise OSError('Windows DPAPI required; no plaintext fallback.')
    import win32crypt
    return win32crypt.CryptUnprotectData(blob,ENTROPY,None,None,1)[1]


def _owner(proof,parameters,db_path,clock):
    if (type(proof) is not Challenge or type(proof.session) is not Session or proof.action!='memory_backup'
            or proof.parameters!=parameters or type(proof.deadline) not in (int,float) or not math.isfinite(proof.deadline)
            or proof.deadline<=time.monotonic()
            or proof.session.role!='admin' or proof.session.verified_until<=clock()):
        raise PermissionError('Fresh signed approval for this exact key operation required.')
    from storage import store
    with store.store_connection(db_path,read_only=True) as db:credential=store._profile_owner(db,proof.session)
    return proof.session.person_id,hashlib.sha256(credential.encode()).hexdigest()


def _read(path):
    _unlinked(path)
    with path.open('rb') as source:blob=source.read(LIMIT+1)
    if len(blob)>LIMIT:raise ValueError('Protected key record byte budget exceeded.')
    return blob


def _load(path):
    blob=_read(path)
    if not blob.startswith(MAGIC):raise ValueError('Wrong protected owner record.')
    data=json.loads(_unprotect(blob[len(MAGIC):]),object_pairs_hook=_unique)
    if type(data) is not dict:return None
    return data


def _write(path,data):
    raw=_json(data).encode();blob=MAGIC+_protect(raw)
    if len(blob)>LIMIT or _unprotect(blob[len(MAGIC):])!=raw:raise ValueError('DPAPI protection readback failed.')
    _publish(path,lambda stage:stage.write_bytes(blob),lambda:False)
    if _read(path)!=blob:raise ValueError('Protected owner record readback differs.')


def _keys(home,owner):
    data=_load(home/'keys.dpapi')
    fields={'version','lineage','owner_id','credential_sha256','storage_key','recovery_key','unlock_key'}
    if (type(data) is not dict or set(data)!=fields or type(data['version']) is not int or data['version']!=1
            or (data['owner_id'],data['credential_sha256'])!=owner):raise ValueError('Protected owner key identity/schema differs.')
    _id(data['lineage']);_id(data['credential_sha256'],64)
    if len(base64.b64decode(data['storage_key'],validate=True))!=32:raise ValueError('Wrong storage key.')
    Fernet(data['recovery_key'].encode('ascii'));Fernet(data['unlock_key'].encode('ascii'))
    return data


def _custody(home,data):
    blob=_read(home/'capsule.enc')
    capsule={key:value for key,value in data.items() if key!='unlock_key'}
    if (not blob.startswith(CAPSULE_MAGIC) or json.loads(Fernet(data['unlock_key'].encode()).decrypt(blob[len(CAPSULE_MAGIC):]),
            object_pairs_hook=_unique)!=capsule):raise ValueError('Capsule authentication/schema differs.')
    return dict(version=1,keys_sha256=hashlib.sha256(_read(home/'keys.dpapi')).hexdigest(),
        capsule_sha256=hashlib.sha256(blob).hexdigest(),owner_id=data['owner_id'],
        credential_sha256=data['credential_sha256'],owner_acknowledged_bitwarden_and_offline=True)


def prepare(directory,proof,*,db_path=None,clock=time.time):
    owner=_owner(proof,PREPARE,db_path,clock)
    home=Path(directory).absolute();_unlinked(home)
    if _unprotect(_protect(b'LYA owner protection preflight'))!=b'LYA owner protection preflight':raise ValueError('DPAPI unavailable.')
    home.mkdir(mode=0o700,parents=True,exist_ok=True)
    if not (home/'keys.dpapi').exists():
        if any(home.iterdir()):raise ValueError('Nonempty unknown key directory; never recreate trust.')
        data=dict(version=1,lineage=secrets.token_hex(16),owner_id=owner[0],credential_sha256=owner[1],
            storage_key=base64.b64encode(secrets.token_bytes(32)).decode(),recovery_key=Fernet.generate_key().decode(),
            unlock_key=Fernet.generate_key().decode())
        _owner(proof,PREPARE,db_path,clock);_write(home/'keys.dpapi',data)
    data=_keys(home,owner)
    capsule={key:value for key,value in data.items() if key!='unlock_key'}
    if not (home/'capsule.enc').exists():
        _owner(proof,PREPARE,db_path,clock)
        blob=CAPSULE_MAGIC+Fernet(data['unlock_key'].encode()).encrypt(_json(capsule).encode())
        _publish(home/'capsule.enc',lambda stage:stage.write_bytes(blob),lambda:False)
    blob=_read(home/'capsule.enc')
    if (not blob.startswith(CAPSULE_MAGIC) or json.loads(Fernet(data['unlock_key'].encode()).decrypt(blob[len(CAPSULE_MAGIC):]),
            object_pairs_hook=_unique)!=capsule):raise ValueError('Existing capsule differs; never replace it.')
    acknowledged=(home/'custody.dpapi').exists()
    if acknowledged and _load(home/'custody.dpapi')!=_custody(home,data):raise ValueError('Custody acknowledgement differs.')
    _owner(proof,PREPARE,db_path,clock)
    return KeyView(data['lineage'],hashlib.sha256(blob).hexdigest(),acknowledged,data['unlock_key'].encode())


def confirm(directory,proof,vault_copy,offline_copy,*,db_path=None,clock=time.time):
    owner=_owner(proof,CONFIRM,db_path,clock);home=Path(directory).absolute();_unlinked(home);data=_keys(home,owner)
    if (type(vault_copy) is not str or type(offline_copy) is not str or len(vault_copy)!=44 or len(offline_copy)!=44
            or not hmac.compare_digest(vault_copy,data['unlock_key']) or not hmac.compare_digest(offline_copy,data['unlock_key'])):
        raise ValueError('Both independently retrieved copies must match exactly; nothing was replaced.')
    expected=_custody(home,data);_owner(proof,CONFIRM,db_path,clock)
    if (home/'custody.dpapi').exists():
        if _load(home/'custody.dpapi')!=expected:raise ValueError('Existing custody acknowledgement differs.')
    else:_write(home/'custody.dpapi',expected)
    _owner(proof,CONFIRM,db_path,clock)
    return dict(custody_acknowledged=True,external_copy_survival_verified=False,production_enabled=False)
