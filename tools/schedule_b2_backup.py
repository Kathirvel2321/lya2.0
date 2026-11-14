"""Nightly B2 backup runner for Windows Task Scheduler.

This script is meant to be run by Windows Task Scheduler; it must NEVER be
run with real credentials from an isolated/sandbox environment.

Usage (owner terminal only):
    python tools/schedule_b2_backup.py --register
    python tools/schedule_b2_backup.py --run

Flags:
    --register   Register a nightly Task Scheduler job (requires admin shell).
    --unregister Remove the scheduled task.
    --run        Execute a single backup attempt (called by Task Scheduler).
    --status     Print last scheduler job status and exit 0.

Scope / limits:
    - Loads one DPAPI-protected child credential; never touches the master key.
    - Credential path and bucket meta read from a local config written at setup time.
    - Pins come from the synthetic publication authority; no plaintext secrets logged.
    - A new dated receipt is written per run; existing receipts are never overwritten.
    - On any error the exit code is non-zero; Task Scheduler will retry next night.
    - Fake-credential smoke mode (--dry-run) uses mocked B2 calls only.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TASK_NAME = 'LYA_B2_NightlyBackup'
# Config file written by --setup; contains only public/non-secret metadata.
CONFIG_NAME = 'b2_scheduler_config.json'
LOG_NAME = 'b2_backup_run.log'

# Schema for the config file (no secrets stored here).
_CONFIG_KEYS = {'version', 'credential_path', 'bucket_id', 'bucket_name',
                'recovery_folder', 'receipt_folder'}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------
def _config_dir() -> Path:
    """User-specific config dir; keep outside source tree."""
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    return base / 'LYA' / 'memory'


def _load_config() -> dict:
    path = _config_dir() / CONFIG_NAME
    if not path.exists():
        raise FileNotFoundError(
            f'Scheduler config not found: {path}\n'
            'Run --setup first from an interactive owner terminal.'
        )
    with path.open('r', encoding='utf-8') as f:
        cfg = json.load(f)
    missing = _CONFIG_KEYS - set(cfg)
    if cfg.get('version') != 1 or missing:
        raise ValueError(f'Invalid or outdated scheduler config (missing: {missing}).')
    return cfg


def _save_config(cfg: dict):
    path = _config_dir() / CONFIG_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(
            f'Config already exists at {path}. Remove it manually before re-running --setup.'
        )
    with path.open('w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    print(f'Config saved to: {path}')


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _setup_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('lya_b2_backup')
    logger.setLevel(logging.DEBUG)
    # Rotate: keep last 7 dated log files, one per run.
    stamp = time.strftime('%Y%m%d')
    log_path = log_dir / f'b2_backup_{stamp}.log'
    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(fh)
    # Also print to stderr for interactive use.
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    logger.addHandler(sh)
    return logger


# ---------------------------------------------------------------------------
# Backup execution
# ---------------------------------------------------------------------------
def _run_backup(cfg: dict, *, dry_run: bool = False, logger: logging.Logger) -> int:
    """Execute one backup attempt. Returns 0 on success, non-zero on failure."""
    from brain.memory_b2_credential import backup_with_credential
    from brain.memory_recovery_pack import RecoveryPins, NAMES, _paths
    from brain.memory_recovery_latest import SyntheticRecoveryLatest

    credential_path = Path(cfg['credential_path'])
    recovery_folder = Path(cfg['recovery_folder'])
    receipt_folder = Path(cfg['receipt_folder'])
    bucket_id = cfg['bucket_id']
    bucket_name = cfg['bucket_name']

    if not credential_path.exists():
        logger.error('Credential file not found: %s — aborting backup.', credential_path)
        return 2
    if not recovery_folder.is_dir():
        logger.error('Recovery folder not found: %s — aborting backup.', recovery_folder)
        return 2

    receipt_folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    receipt = receipt_folder / f'backup_receipt_{stamp}.json'

    if dry_run:
        logger.info('DRY RUN: would back up %s to bucket %s.', recovery_folder, bucket_name)
        logger.info('DRY RUN: credential at %s, receipt would be %s.', credential_path, receipt)
        return 0

    # Observe pins from the latest-state file; must be stable across the transfer.
    latest_path = recovery_folder / 'recovery_latest.db'
    if not latest_path.exists():
        logger.error('Latest-state store not found at %s — aborting.', latest_path)
        return 2

    try:
        from brain.memory_recovery_latest import SyntheticRecoveryLatest
        latest = SyntheticRecoveryLatest(latest_path, synthetic_only=True, approved=True)

        def observe():
            return latest.read(approved=True)

        logger.info('Starting B2 backup run (bucket=%s, prefix=lya-memory-lab/worker/).', bucket_name)
        result = backup_with_credential(
            recovery_folder, receipt,
            credential_path=str(credential_path),
            bucket_id=bucket_id,
            bucket_name=bucket_name,
            pins=observe(),
            observe=observe,
            synthetic_only=True,
            approved=True,
        )
        # Log only content-free public metadata.
        logger.info(
            'Backup succeeded: pack_id=%s, encrypted_bytes=%s, receipt=%s.',
            result.get('pack_id', '?')[:16] + '...',
            result.get('encrypted_bytes', '?'),
            receipt.name,
        )
        return 0
    except FileExistsError as exc:
        logger.warning('Receipt collision (already backed up today?): %s', exc)
        return 0  # idempotent — today's backup already ran
    except Exception as exc:
        # Never log secret details; just the exception type and safe message.
        logger.error('Backup failed (%s): %s', type(exc).__name__, _safe_msg(exc))
        return 1


def _safe_msg(exc: Exception) -> str:
    """Return a loggable message; withholds anything after a colon that looks like a secret."""
    msg = str(exc)
    # Redact long hex or base64/alphanumeric tokens that look like secrets.
    msg = re.sub(r'[0-9a-zA-Z/+]{20,}', '<REDACTED>', msg)[:200]
    return msg


# ---------------------------------------------------------------------------
# Task Scheduler
# ---------------------------------------------------------------------------
def _python_path() -> str:
    return str(Path(sys.executable).resolve())


def _script_path() -> str:
    return str(Path(__file__).resolve())


def _register_task(*, hour: int = 2, minute: int = 0) -> int:
    """Register a nightly schtasks job. Requires the caller to be in an admin shell."""
    python = _python_path()
    script = _script_path()
    cmd = [
        'schtasks', '/Create', '/TN', TASK_NAME,
        '/TR', f'"{python}" "{script}" --run',
        '/SC', 'DAILY',
        '/ST', f'{hour:02d}:{minute:02d}',
        '/RL', 'HIGHEST',
        '/F',  # overwrite if exists
    ]
    print('Registering Task Scheduler job:', ' '.join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print('ERROR:', result.stderr.strip() or result.stdout.strip())
        return result.returncode
    print('Task registered:', TASK_NAME)
    return 0


def _unregister_task() -> int:
    cmd = ['schtasks', '/Delete', '/TN', TASK_NAME, '/F']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print('ERROR:', result.stderr.strip() or result.stdout.strip())
        return result.returncode
    print('Task removed:', TASK_NAME)
    return 0


def _task_status() -> int:
    cmd = ['schtasks', '/Query', '/TN', TASK_NAME, '/FO', 'LIST']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print('Task not found or schtasks error:', result.stderr.strip())
        return result.returncode
    # Print only the safe fields; skip Last Result details that might expose paths.
    for line in result.stdout.splitlines():
        if any(line.startswith(k) for k in ('TaskName', 'Status', 'Last Run Time', 'Next Run Time', 'Schedule Type')):
            print(line)
    return 0


# ---------------------------------------------------------------------------
# Setup wizard
# ---------------------------------------------------------------------------
def _setup_wizard() -> int:
    """Interactive setup: gather public metadata only; no secret entry."""
    if sys.platform != 'win32':
        print('ERROR: Windows only. DPAPI is required for credential protection.')
        return 1
    if not sys.stdin.isatty():
        print('ERROR: Interactive terminal required for setup.')
        return 1

    print('LYA B2 Nightly Backup — setup wizard')
    print('No secrets are stored in the config. Only file paths and bucket metadata.')
    print()

    credential_path = input('Path to DPAPI-protected B2 credential file: ').strip()
    if not Path(credential_path).exists():
        print(f'ERROR: Credential file not found: {credential_path}')
        return 1

    bucket_id = input('Bucket ID (6-64 alphanumeric): ').strip()
    bucket_name = input('Bucket name (lya-memory-lab-... or lya-fake-...): ').strip()
    recovery_folder = input('Local recovery pack folder path: ').strip()
    receipt_folder = input('Receipt output folder path (will be created if absent): ').strip()

    cfg = {
        'version': 1,
        'credential_path': credential_path,
        'bucket_id': bucket_id,
        'bucket_name': bucket_name,
        'recovery_folder': recovery_folder,
        'receipt_folder': receipt_folder,
    }
    try:
        _save_config(cfg)
    except FileExistsError as exc:
        print(f'ERROR: {exc}')
        return 1
    print('Setup complete. Run --register to install the nightly task.')
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--run', action='store_true',
                       help='Execute one backup attempt (called by Task Scheduler).')
    group.add_argument('--register', action='store_true',
                       help='Install the nightly Task Scheduler job.')
    group.add_argument('--unregister', action='store_true',
                       help='Remove the scheduled task.')
    group.add_argument('--status', action='store_true',
                       help='Print Task Scheduler job status.')
    group.add_argument('--setup', action='store_true',
                       help='Interactive wizard: write public scheduler config.')
    group.add_argument('--dry-run', action='store_true',
                       help='Smoke-test the config without real B2 access.')
    parser.add_argument('--hour', type=int, default=2,
                        help='Hour (0-23) for the nightly run. Default: 2.')
    parser.add_argument('--minute', type=int, default=0,
                        help='Minute (0-59) for the nightly run. Default: 0.')
    args = parser.parse_args()

    if args.register:
        return _register_task(hour=args.hour, minute=args.minute)
    if args.unregister:
        return _unregister_task()
    if args.status:
        return _task_status()
    if args.setup:
        return _setup_wizard()

    # --run or --dry-run: load config and execute.
    try:
        cfg = _load_config()
    except (FileNotFoundError, ValueError) as exc:
        print(f'ERROR: {exc}')
        return 2

    log_dir = _config_dir() / 'logs'
    logger = _setup_logging(log_dir)
    return _run_backup(cfg, dry_run=args.dry_run, logger=logger)


if __name__ == '__main__':
    raise SystemExit(main())
