"""Explicit shared-memory pilot configuration and pinned native control transport.

The desktop control packet is accepted only by the existing operator SSH command,
never by a browser endpoint. Phone authority comes from its live passkey session.
"""
from dataclasses import asdict
import ipaddress
import json
import math
import os
from pathlib import Path
import threading
import time

from brain.conversation import Context, PublicTurn
from brain.memory_authority import WriterGrant
from brain.memory_authority_transfer import _open_authority
from brain.memory_prototype import _id, _unlinked
from brain.memory_recovery import _unique
from brain.memory_recovery_latest import SyntheticRecoveryLatest
from brain.shared_memory import SharedMemoryService, SharedMemoryUncertain, parse_command

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'desktop/shared-memory.local.json'


def _settings(path):
    path = Path(path).absolute(); _unlinked(path)
    if not path.is_file() or (path.stat().st_mode & 0o077 and os.name != 'nt'):
        raise PermissionError('An existing private shared-memory configuration is required.')
    with path.open('rb') as source: raw = source.read(16385)
    if len(raw) > 16384: raise ValueError('Shared configuration is too large.')
    data = json.loads(raw, object_pairs_hook=_unique)
    if type(data) is not dict: raise ValueError('Invalid shared configuration.')
    return data


def configured_service(config, *, clock=time.time):
    setting = config.get('shared_memory')
    if setting is None or setting is False: return None
    if type(setting) is not dict or set(setting) != {'mode', 'state_file'} or setting['mode'] != 'synthetic':
        raise ValueError('Only explicitly selected synthetic shared-memory service is supported.')
    path = Path(setting['state_file']).absolute(); data = _settings(path)
    if (set(data) != {'version', 'synthetic_only', 'lineage', 'capsule_sha256', 'unlock', 'grant'}
            or type(data['version']) is not int or data['version'] != 1 or data['synthetic_only'] is not True):
        raise PermissionError('Existing fake-only service state is required; no automatic initialization.')
    lineage = _id(data['lineage']); _id(data['capsule_sha256'], 64)
    g = data['grant']
    if type(g) is not dict or set(g) != {'lineage', 'epoch', 'writer', 'token'} or g['lineage'] != lineage:
        raise ValueError('Invalid existing shared writer grant.')
    grant = WriterGrant(lineage, g['epoch'], g['writer'], bytes.fromhex(g['token']))
    latest = SyntheticRecoveryLatest(path.parent / 'latest.sqlite', synthetic_only=True)
    authority = _open_authority(path.parent, latest, data['unlock'].encode('ascii'), lineage, data['capsule_sha256'], clock)
    return SharedMemoryService(authority, grant, synthetic_only=True)


def desktop_request(packet, store, service, *, clock=time.time):
    """Trusted operator-control adapter; HTTP callers cannot choose these claims."""
    if service is None: raise ValueError('Shared memory is not configured.')
    if type(packet) is not dict or set(packet) != {'id', 'text', 'context', 'synthetic_only'} or packet['synthetic_only'] is not True:
        raise ValueError('Invalid shared control packet.')
    _id(packet['id']); parse_command(packet['text'], packet['id'])
    c = packet['context']
    if (type(c) is not dict or set(c) != {'principal', 'device', 'session', 'generation', 'expires_at', 'owner_verified'}
            or c['device'] != 'laptop' or c['owner_verified'] is not True
            or type(c['expires_at']) not in (int, float) or not math.isfinite(c['expires_at'])
            or not clock() < c['expires_at'] <= clock() + 300):
        raise PermissionError('Fresh native owner verification is required.')
    for name in ('principal', 'session', 'generation'): _id(c[name], 64)
    if c['generation'] != c['principal']: raise PermissionError('Native identity generation differs.')
    credential = store.credential()
    if not credential: raise PermissionError('An existing phone pairing is required.')
    stamp = credential['stamp']
    context = Context(**c)
    def resolve():
        current = store.credential()
        with store.db() as db: row = db.execute('SELECT owner FROM binding WHERE id=1').fetchone()
        if not current or current['stamp'] != stamp or not row or row[0] != c['principal']:
            raise PermissionError('Shared phone binding was revoked or changed.')
        return context
    turn = PublicTurn(packet['id'], packet['text'], context, time.monotonic() + 30,
                      resolve, clock, threading.Event())
    turn.check()
    return service.respond(turn)


class OracleSharedMemory:
    synthetic_only = True

    def __init__(self, config, *, exchange=None):
        self.config, self.exchange = config, exchange

    def respond(self, turn):
        if type(turn) is not PublicTurn or not turn.context.owner_verified or turn.context.device != 'laptop':
            raise PermissionError('A verified native owner turn is required.')
        turn.check(); parsed, _, _ = parse_command(turn.text, turn.request_id)
        config = self.config
        if config.get('enabled') is not True or config.get('mode') != 'synthetic':
            raise ValueError('Shared memory is disabled; no request was sent.')
        try:
            key = (ROOT / config['key_file']).resolve(); key.relative_to(ROOT)
            pins = ROOT / 'oracle_known_hosts.local'
            if not key.is_file() or not pins.is_file(): raise ValueError('Pinned transport unavailable.')
            command = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'ConnectTimeout=7',
                       '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no', '-o', 'ForwardAgent=no',
                       '-o', 'ClearAllForwardings=yes', '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
                       '-o', 'UserKnownHostsFile=' + str(pins), '-i', str(key),
                       'ubuntu@' + str(ipaddress.ip_address(config['host'])),
                       'sudo -n -u lya-connect /opt/lya-connect/venv/bin/python -I /opt/lya-connect/control.py shared-memory']
            packet = dict(id=turn.request_id, text=turn.text, context=asdict(turn.context), synthetic_only=True)
            exchange = self.exchange
            if exchange is None:
                from cloud.ssh_session import exchange
            run = exchange(command, json.dumps(packet), turn._cancelled, timeout=30, close_stdin=True, output_limit=65536)
            turn.check()
            if run.returncode or len(run.stdout.encode()) > 65536: raise ValueError('Unconfirmed control result.')
            result = json.loads(run.stdout, object_pairs_hook=_unique)
            if (type(result) is not dict or set(result) != {'text', 'project', 'synthetic_only', 'publication_confirmed', 'expires_at'}
                    or result['synthetic_only'] is not True or result['publication_confirmed'] is not True
                    or type(result['text']) is not str or not 1 <= len(result['text']) <= 8000
                    or result['project'] != parsed['project']):
                raise ValueError('Invalid shared result.')
            expiry = result['expires_at']
            if expiry is not None and (type(expiry) not in (int, float) or not math.isfinite(expiry) or turn._clock() >= expiry):
                raise PermissionError('Shared memory expired before delivery.')
            turn.check()
            return result
        except (PermissionError, InterruptedError): raise
        except Exception:
            raise SharedMemoryUncertain('Shared memory completion is unconfirmed. A write may have committed; resend the same command to check its original request.') from None


def configured_client():
    if not CONFIG.exists(): raise ValueError('Shared memory is not configured. Local notes remain available.')
    return OracleSharedMemory(_settings(CONFIG))
