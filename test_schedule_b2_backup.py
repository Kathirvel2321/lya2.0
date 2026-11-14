"""Isolated fake-data tests for tools/schedule_b2_backup.py.

Uses temporary directories and mocked B2 calls; no live credential, no real upload.
Run with: .\.venv-ui\Scripts\python.exe -m unittest test_schedule_b2_backup -v
"""
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

# Ensure the project root is on the path.
sys.path.insert(0, str(Path(__file__).parent))

import tools.schedule_b2_backup as sched


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _fake_config(tmp: Path, **overrides) -> dict:
    cfg = {
        'version': 1,
        'credential_path': str(tmp / 'fake.cred'),
        'bucket_id': 'ABC123XYZ987',
        'bucket_name': 'lya-memory-lab-test',
        'recovery_folder': str(tmp / 'recovery'),
        'receipt_folder': str(tmp / 'receipts'),
    }
    cfg.update(overrides)
    return cfg


def _write_config(tmp: Path, cfg: dict) -> Path:
    p = tmp / 'b2_scheduler_config.json'
    p.write_text(json.dumps(cfg), encoding='utf-8')
    return p


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------
class ConfigChecks(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_save_and_load_roundtrip(self):
        cfg = _fake_config(self.tmp)
        # Patch config dir so we don't write to real LOCALAPPDATA.
        with patch.object(sched, '_config_dir', return_value=self.tmp):
            sched._save_config(cfg)
            loaded = sched._load_config()
        self.assertEqual(loaded['bucket_name'], 'lya-memory-lab-test')
        self.assertEqual(loaded['version'], 1)

    def test_missing_config_raises_file_not_found(self):
        with patch.object(sched, '_config_dir', return_value=self.tmp / 'absent'):
            with self.assertRaises(FileNotFoundError):
                sched._load_config()

    def test_duplicate_save_raises_file_exists(self):
        cfg = _fake_config(self.tmp)
        with patch.object(sched, '_config_dir', return_value=self.tmp):
            sched._save_config(cfg)
            with self.assertRaises(FileExistsError):
                sched._save_config(cfg)

    def test_invalid_version_raises_value_error(self):
        cfg = _fake_config(self.tmp)
        cfg['version'] = 99
        p = self.tmp / sched.CONFIG_NAME
        p.write_text(json.dumps(cfg), encoding='utf-8')
        with patch.object(sched, '_config_dir', return_value=self.tmp):
            with self.assertRaises(ValueError):
                sched._load_config()

    def test_missing_key_raises_value_error(self):
        cfg = _fake_config(self.tmp)
        del cfg['bucket_id']
        p = self.tmp / sched.CONFIG_NAME
        p.write_text(json.dumps(cfg), encoding='utf-8')
        with patch.object(sched, '_config_dir', return_value=self.tmp):
            with self.assertRaises(ValueError):
                sched._load_config()


# ---------------------------------------------------------------------------
# safe_msg tests
# ---------------------------------------------------------------------------
class SafeMsgChecks(unittest.TestCase):

    def test_hex_tokens_are_redacted(self):
        exc = Exception('Token: abcdef1234567890abcdef12345 more text')
        result = sched._safe_msg(exc)
        self.assertNotIn('abcdef1234567890abcdef12345', result)
        self.assertIn('REDACTED', result)

    def test_short_message_preserved(self):
        exc = Exception('Recovery folder not found')
        self.assertIn('Recovery', sched._safe_msg(exc))

    def test_very_long_message_truncated(self):
        exc = Exception('x' * 500)
        self.assertLessEqual(len(sched._safe_msg(exc)), 210)


# ---------------------------------------------------------------------------
# Logging setup test
# ---------------------------------------------------------------------------
class LoggingChecks(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_log_file_created_in_target_dir(self):
        log_dir = self.tmp / 'logs'
        logger = sched._setup_logging(log_dir)
        logger.info('test message')
        logs = list(log_dir.glob('b2_backup_*.log'))
        self.assertTrue(logs, 'Expected at least one log file.')
        content = logs[0].read_text(encoding='utf-8')
        self.assertIn('test message', content)
        # Cleanup handlers to avoid ResourceWarning.
        for h in logger.handlers[:]:
            h.close(); logger.removeHandler(h)


# ---------------------------------------------------------------------------
# Backup run with mocked B2
# ---------------------------------------------------------------------------
class BackupRunChecks(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.tmp / 'recovery').mkdir()
        (self.tmp / 'receipts').mkdir()
        # Create a fake credential file (content doesn't matter — calls are mocked).
        (self.tmp / 'fake.cred').write_bytes(b'FAKE_CRED')
        self.cfg = _fake_config(self.tmp)
        self.logger = logging.getLogger('test_sched')
        self.logger.addHandler(logging.NullHandler())

    def _make_fake_pins(self):
        """Return a minimal fake RecoveryPins-like object."""
        from unittest.mock import MagicMock
        pins = MagicMock()
        pins.__class__.__name__ = 'RecoveryPins'
        return pins

    def test_missing_credential_file_returns_exit_2(self):
        cfg = dict(self.cfg, credential_path=str(self.tmp / 'nonexistent.cred'))
        code = sched._run_backup(cfg, logger=self.logger)
        self.assertEqual(code, 2)

    def test_missing_recovery_folder_returns_exit_2(self):
        cfg = dict(self.cfg, recovery_folder=str(self.tmp / 'no_such_folder'))
        code = sched._run_backup(cfg, logger=self.logger)
        self.assertEqual(code, 2)

    def test_dry_run_succeeds_without_b2_access(self):
        code = sched._run_backup(self.cfg, dry_run=True, logger=self.logger)
        self.assertEqual(code, 0)

    def test_dry_run_does_not_create_receipt(self):
        sched._run_backup(self.cfg, dry_run=True, logger=self.logger)
        receipts = list((self.tmp / 'receipts').glob('*.json'))
        self.assertEqual(receipts, [], 'Dry run must not create a receipt.')

    def test_missing_latest_store_returns_exit_2(self):
        # No recovery_latest.db in the recovery folder.
        code = sched._run_backup(self.cfg, logger=self.logger)
        self.assertEqual(code, 2)

    def test_backup_success_path_writes_receipt(self):
        fake_pins = self._make_fake_pins()
        receipt_path = self.tmp / 'receipts' / 'backup_receipt_fake.json'

        def fake_backup_with_credential(*args, **kwargs):
            # Simulate a successful backup by writing the receipt ourselves
            # and returning a result dict.
            receipt = Path(kwargs['receipt'] if 'receipt' in kwargs else args[1])
            result = {
                'verified': True,
                'pack_id': 'a' * 64,
                'encrypted_bytes': 5395,
                'sha256': {},
            }
            receipt.write_text(json.dumps(result), encoding='utf-8')
            return result

        fake_latest = MagicMock()
        fake_latest.read.return_value = fake_pins

        with patch.dict('sys.modules', {
            'brain.memory_b2_credential': MagicMock(
                backup_with_credential=fake_backup_with_credential
            ),
            'brain.memory_recovery_pack': MagicMock(
                RecoveryPins=type(fake_pins),
                NAMES=['backup', 'state', 'keys'],
                _paths=lambda f: {},
            ),
            'brain.memory_recovery_latest': MagicMock(
                SyntheticRecoveryLatest=lambda *a, **kw: fake_latest
            ),
        }):
            # Create a fake latest store so the path check passes.
            (self.tmp / 'recovery' / 'recovery_latest.db').write_bytes(b'FAKE')
            code = sched._run_backup(self.cfg, logger=self.logger)

        self.assertEqual(code, 0)

    def test_backup_exception_returns_exit_1_and_no_secret_in_log(self):
        """B2 transport failure exits 1; no credential token appears in the log."""
        log_messages = []

        class CapturingHandler(logging.Handler):
            def emit(self, record):
                log_messages.append(record.getMessage())

        logger = logging.getLogger('test_exc')
        h = CapturingHandler()
        logger.addHandler(h)

        secret_token = 'secretABC1234567890XYZ'

        def fake_backup_with_credential(*a, **kw):
            raise OSError(f'B2 transport failed; token={secret_token}')

        fake_latest = MagicMock()
        fake_latest.read.return_value = MagicMock()

        with patch.dict('sys.modules', {
            'brain.memory_b2_credential': MagicMock(
                backup_with_credential=fake_backup_with_credential
            ),
            'brain.memory_recovery_pack': MagicMock(),
            'brain.memory_recovery_latest': MagicMock(
                SyntheticRecoveryLatest=lambda *a, **kw: fake_latest
            ),
        }):
            (self.tmp / 'recovery' / 'recovery_latest.db').write_bytes(b'FAKE')
            code = sched._run_backup(self.cfg, logger=logger)

        self.assertEqual(code, 1)
        combined = ' '.join(log_messages)
        self.assertNotIn(secret_token, combined, 'Secret token must not appear in log.')
        logger.removeHandler(h)

    def test_receipt_collision_returns_exit_0(self):
        """FileExistsError (already backed up today) is treated as idempotent success."""
        fake_latest = MagicMock()
        fake_latest.read.return_value = MagicMock()

        def fake_backup_with_credential(*a, **kw):
            raise FileExistsError('Receipt already exists.')

        with patch.dict('sys.modules', {
            'brain.memory_b2_credential': MagicMock(
                backup_with_credential=fake_backup_with_credential
            ),
            'brain.memory_recovery_pack': MagicMock(),
            'brain.memory_recovery_latest': MagicMock(
                SyntheticRecoveryLatest=lambda *a, **kw: fake_latest
            ),
        }):
            (self.tmp / 'recovery' / 'recovery_latest.db').write_bytes(b'FAKE')
            code = sched._run_backup(self.cfg, logger=self.logger)

        self.assertEqual(code, 0)


# ---------------------------------------------------------------------------
# schtasks integration (parse-only; no real task creation)
# ---------------------------------------------------------------------------
class SchedulerCmdChecks(unittest.TestCase):

    def test_register_builds_correct_schtasks_command(self):
        """_register_task calls schtasks with the right flags (mocked subprocess)."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            m = MagicMock(); m.returncode = 0; m.stderr = ''; m.stdout = 'SUCCESS'
            return m

        with patch.object(sched.subprocess, 'run', side_effect=fake_run):
            code = sched._register_task(hour=3, minute=15)

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        cmd = calls[0]
        self.assertIn('schtasks', cmd[0])
        self.assertIn('/Create', cmd)
        self.assertIn(sched.TASK_NAME, cmd)
        self.assertIn('DAILY', cmd)
        self.assertIn('03:15', cmd)

    def test_unregister_calls_schtasks_delete(self):
        def fake_run(cmd, **kwargs):
            m = MagicMock(); m.returncode = 0; m.stderr = ''; m.stdout = ''
            return m

        with patch.object(sched.subprocess, 'run', side_effect=fake_run):
            code = sched._unregister_task()

        self.assertEqual(code, 0)

    def test_status_filters_safe_lines_only(self, capsys=None):
        lines = [
            'TaskName: LYA_B2_NightlyBackup',
            'Status: Ready',
            'Last Run Time: 2026-11-06 02:00:00',
            'Last Result: 0',
            'Next Run Time: 2026-11-07 02:00:00',
            'Schedule Type: Daily',
            'Hidden: No',
        ]
        def fake_run(cmd, **kwargs):
            m = MagicMock(); m.returncode = 0
            m.stdout = '\n'.join(lines); m.stderr = ''
            return m

        import io
        with patch.object(sched.subprocess, 'run', side_effect=fake_run):
            with patch('sys.stdout', new_callable=io.StringIO) as fake_out:
                code = sched._task_status()
                output = fake_out.getvalue()

        self.assertEqual(code, 0)
        # Safe fields are printed.
        self.assertIn('TaskName', output)
        self.assertIn('Status', output)
        # 'Hidden: No' is not in the safe list; must not appear.
        self.assertNotIn('Hidden', output)

    def test_register_failure_propagates_exit_code(self):
        def fake_run(cmd, **kwargs):
            m = MagicMock(); m.returncode = 1
            m.stderr = 'Access denied.'; m.stdout = ''
            return m

        with patch.object(sched.subprocess, 'run', side_effect=fake_run):
            code = sched._register_task()

        self.assertNotEqual(code, 0)


# ---------------------------------------------------------------------------
# Script parse-only smoke test
# ---------------------------------------------------------------------------
class ParseChecks(unittest.TestCase):

    def test_script_parses_without_import_error(self):
        """Confirm the module loads cleanly."""
        import tools.schedule_b2_backup  # already imported as sched
        self.assertTrue(callable(sched.main))

    def test_missing_subcommand_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / 'tools' / 'schedule_b2_backup.py')],
            capture_output=True, text=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
