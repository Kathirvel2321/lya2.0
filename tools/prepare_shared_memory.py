"""Prepare a new empty, explicitly fake-only shared-memory service. No networking."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))


def prepare(directory, principal, *, synthetic_only=False, approved=False, clock=time.time):
    from brain.memory_custody import _approval, RecoveryKeys, WitnessState, seal_keys
    from brain.memory_prototype import _id, _unlinked, SyntheticMemory
    from brain.memory_recovery import SyntheticRecovery
    from brain.memory_authority import SyntheticAuthority
    from brain.memory_publication_authority import SyntheticPublicationAuthority
    from brain.memory_recovery_pack import RecoveryPins, stage_pack
    from brain.memory_recovery_trust import seal_trust
    from brain.memory_recovery_latest import RecoveryHead, SyntheticRecoveryLatest
    from cloud.shared_memory import configured_service
    _approval(synthetic_only, approved, lambda: False); _id(principal, 64)
    home = Path(directory).absolute(); _unlinked(home)
    home.mkdir(mode=0o700)
    # Generated fake custody is never a production key ceremony or a Git artifact.
    (home / '.gitignore').write_text('*\n', encoding='ascii')
    storage = secrets.token_bytes(32); recovery_key = SyntheticRecovery.new_key(); unlock = SyntheticRecovery.new_key()
    source = SyntheticMemory(home / 'initial.sqlite', encryption_key=storage, synthetic_only=True, clock=clock)
    source.create_owner(principal)
    recovery = SyntheticRecovery(recovery_key, synthetic_only=True, clock=clock)
    authority = SyntheticAuthority(home / 'authority', recovery=recovery, storage_key=storage, synthetic_only=True, clock=clock)
    anchor = authority.register(source, approved=True)
    grant = authority.acquire(anchor.lineage, secrets.token_hex(16), expected_epoch=0, approved=True)
    capsule = home / 'keys.enc'
    capsule_digest = seal_keys(capsule, unlock, RecoveryKeys(anchor.lineage, storage, recovery_key), synthetic_only=True, approved=True)
    with authority._repository._db() as db:
        _, _, _, backup, checkpoint, row = authority._entry(db, anchor.lineage)
        pins = RecoveryPins(WitnessState(anchor, grant.epoch), capsule_digest, row['backup_sha256'])
        stage_pack(home / 'initial-pack', backup=backup, checkpoint=checkpoint, capsule=capsule,
                   pins=pins, unlock_key=unlock, synthetic_only=True, approved=True)
    trust = home / 'initial-trust.enc'
    digest = seal_trust(trust, pins, unlock, synthetic_only=True, approved=True)
    latest = SyntheticRecoveryLatest.create(home / 'latest.sqlite', synthetic_only=True, approved=True)
    head = RecoveryHead(pins, digest)
    latest.begin(None, head, approved=True)
    latest.finish(head, home / 'initial-pack', trust, unlock, approved=True)
    (home / 'publications').mkdir(mode=0o700)
    authority = SyntheticPublicationAuthority(home / 'authority', latest=latest, publications=home / 'publications',
        capsule=capsule, unlock_key=unlock, recovery=recovery, storage_key=storage, synthetic_only=True, clock=clock)
    authority.bind_publication(anchor.lineage, trust, approved=True)
    settings = dict(version=1, synthetic_only=True, lineage=anchor.lineage, capsule_sha256=capsule_digest,
                    unlock=unlock.decode('ascii'), grant={**asdict(grant), 'token': grant.token.hex()})
    path = home / 'shared-memory.local.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(json.dumps(settings)); stream.flush(); os.fsync(stream.fileno())
    config = {'shared_memory': {'mode': 'synthetic', 'state_file': str(path)}}
    configured_service(config, clock=clock)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--principal', required=True, help='Binding of a generated fake identity only.')
    parser.add_argument('--synthetic-only', action='store_true', required=True)
    parser.add_argument('--approved', action='store_true', required=True)
    args = parser.parse_args()
    prepare(args.directory, args.principal, synthetic_only=args.synthetic_only, approved=args.approved)
    print(json.dumps(dict(prepared=True, synthetic_only=True, empty_memory=True, production_enabled=False)))


if __name__ == '__main__':
    try: main()
    except Exception: raise SystemExit('Shared demo preparation failed; preserve any incomplete destination. Details withheld.')
