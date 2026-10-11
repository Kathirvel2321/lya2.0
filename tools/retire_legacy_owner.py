"""Offline operator maintenance only; never exposed to voice or the browser API."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from security import vault
from storage import store


def protect_directory(path):
    if os.name == 'nt':
        import win32api
        import win32con
        import win32security
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        try:
            sid = win32security.ConvertSidToStringSid(
                win32security.GetTokenInformation(token, win32security.TokenUser)[0])
        finally:
            token.Close()
        descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
            f'D:P(A;OICI;FA;;;{sid})(A;OICI;FA;;;SY)', win32security.SDDL_REVISION_1)
        win32security.SetFileSecurity(str(path),
            win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
            descriptor)
    else:
        path.chmod(0o700)


def target_path(db_path):
    target = Path(db_path) if db_path is not None else store.get_data_dir()/'lya.db.enc'
    if not target.is_file() or not target.stat().st_size:
        raise FileNotFoundError('No existing protected identity store; nothing to retire.')
    if vault._F is None and not Path(vault.KEY_PATH).is_file():
        raise PermissionError('Existing encryption key unavailable. No key will be created.')
    return target


def legacy_owners(db):
    if db.execute('SELECT 1 FROM owner_passkeys LIMIT 1').fetchone():
        raise PermissionError('A phone-passkey registration exists. This legacy-only tool refuses to change it.')
    return [row[0] for row in db.execute("SELECT person_id FROM people WHERE role='admin' AND active=1")]


def check(db_path=None):
    target = target_path(db_path)
    with store.store_connection(target, read_only=True) as db:
        owners = legacy_owners(db)
        return dict(legacy_owner_present=bool(owners), readable=True, phone_registration_present=False)


def retire(db_path=None):
    target = target_path(db_path)
    if not check(target)['legacy_owner_present']:
        return dict(changed=False, backup=None)
    with store.store_connection(target) as db:
        owners = legacy_owners(db)
        if not owners:
            raise PermissionError('Owner registration changed during maintenance; no reset performed.')
        archive_root = target.parent/'registration-archive'
        if archive_root.is_symlink() or archive_root.is_junction():
            raise PermissionError('Archive directory cannot be a link.')
        archive_root.mkdir(exist_ok=True)
        folder = archive_root/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(6))
        folder.mkdir()
        protect_directory(folder)
        backup = folder/'identity-before.enc'
        original = target.read_bytes()
        with backup.open('xb') as output:
            output.write(original)
            output.flush()
            os.fsync(output.fileno())
        if hashlib.sha256(backup.read_bytes()).digest() != hashlib.sha256(original).digest():
            raise OSError('Encrypted backup verification failed; owner registration was not changed.')
        for person_id in owners:
            for table in ('face_templates', 'voice_templates', 'admin_recovery'):
                db.execute(f'DELETE FROM {table} WHERE person_id=?', (person_id,))
            db.execute('UPDATE people SET active=0 WHERE person_id=?', (person_id,))
        db.execute('INSERT INTO audit_events(time,action_type,outcome,person_id) VALUES(?,?,?,NULL)',
            (datetime.now(timezone.utc).isoformat(), 'legacy_owner_retired', 'explicit_operator_reset'))
    return dict(changed=True, backup=backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Retire old owners after a verified encrypted backup.')
    args = parser.parse_args()
    try:
        result = retire() if args.apply else check()
        # Output only maintenance status/location, never names, credentials or private content.
        print(json.dumps(result, default=str))
        return 0
    except Exception as exc:
        print(json.dumps(dict(changed=False, error=type(exc).__name__)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
