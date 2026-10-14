"""Reproducible fake-key/temp-store checks and sensorless native UI previews."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'desktop')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
OUT = Path(__file__).parent


def main():
    from cryptography.fernet import Fernet
    from security import vault
    from storage import store
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    from desktop.owner_setup import OwnerSetupDialog
    from security.approval import Challenge
    from security.policy import Session
    from security.passkeys import PAGE
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory(prefix='lya-owner-check-') as temp:
        base = Path(temp)
        key = Fernet(Fernet.generate_key())
        with patch.object(vault, '_F', key), patch.object(vault, '_get_fernet', return_value=key), \
             patch.object(store, 'get_data_dir', return_value=base / 'defaults'), \
             patch.dict(os.environ, {'LYA_DATA_DIR': str(base / 'defaults')}):
            modules = ['test_passkeys', 'test_approval', 'test_storage', 'test_registration',
                       'test_registration_ui', 'test_brain_workflow', 'desktop.check_experience',
                       'test_recovery_ui', 'test_project_memory', 'test_public_archive']
            suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
            result = unittest.TextTestRunner(verbosity=1).run(suite)
            summary = dict(date='2026-10-08', tests=result.testsRun, failures=len(result.failures),
                           errors=len(result.errors), skipped=len(result.skipped),
                           successful=result.wasSuccessful(), modules=modules,
                           live_enrollment=False, owner_sensors=False, owner_store=False,
                           note='Synthetic cryptographic/native integration only; actual phone/browser transport unverified.')
            with patch('desktop.setup_speech.SetupSpeech.say'):
                dialog = OwnerSetupDialog(db_path=base / 'preview.enc', reduced_motion=False,
                                          open_browser=lambda _: False)
                dialog.show()
                app.processEvents()
                dialog.grab().save(str(OUT / 'owner-arrive.png'))
                dialog.advance()
                app.processEvents()
                dialog.grab().save(str(OUT / 'owner-name.png'))
                dialog.advance()
                app.processEvents()
                dialog.grab().save(str(OUT / 'owner-recovery.png'))
                # Measure only this actual widget with its native decoration active.
                dialog.mark.active = True
                started_cpu, started = time.process_time(), time.monotonic()
                for _ in range(60):
                    QTest.qWait(50)
                summary['widget_cpu_percent_one_core'] = round(100*(time.process_time()-started_cpu)/(time.monotonic()-started), 3)
                dialog.reject()
                approval = Challenge('synthetic-preview', Session('admin', 'Synthetic', 'fake-session', 'fake-person', time.time()+300),
                                     'memory_write', 'remember short Study plan = Review chapter one', time.monotonic()+120)
                pending = OwnerSetupDialog(db_path=base / 'preview.enc', reduced_motion=True, approval=approval)
                pending.show()
                app.processEvents()
                pending.grab().save(str(OUT / 'owner-one-action.png'))
                pending.reject()
                store.register_device_admin('Synthetic legacy', base / 'legacy.enc')
                locked = OwnerSetupDialog(db_path=base / 'legacy.enc', reduced_motion=True)
                locked.show()
                app.processEvents()
                locked.grab().save(str(OUT / 'owner-legacy-locked.png'))
                locked.reject()
            # Standalone static synthetic browser preview; no token/server/sensor/proof.
            (OUT / 'phone-page-preview.html').write_text(PAGE.replace('__NONCE__', 'synthetic-preview'), encoding='utf-8')
            script = re.search(r'<script nonce="[^"]+">(.*?)</script>', PAGE, re.S).group(1)
            node = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
            script_file = base / 'passkeys.js'
            script_file.write_text(script, encoding='utf-8')
            summary['browser_javascript_syntax'] = (subprocess.run([str(node), '--check', str(script_file)],
                capture_output=True, timeout=10).returncode == 0) if node.is_file() else None
            (OUT / 'validation.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
            print(json.dumps(summary, indent=2))
            return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
