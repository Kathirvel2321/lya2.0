"""Synthetic crypto/native tests and UI captures; no owner store, sensors or enrollment."""
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
OUT = Path(__file__).parent
sys.path[:0] = [str(ROOT), str(ROOT/'desktop')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def main():
    from cryptography.fernet import Fernet
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from security import vault
    from security.passkeys import PAGE
    from storage import store
    from desktop.owner_setup import OwnerSetupDialog
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory(prefix='lya-registration-design-') as temp:
        base = Path(temp)
        key = Fernet(Fernet.generate_key())
        with patch.object(vault, '_F', key), patch.object(vault, '_get_fernet', return_value=key), \
             patch.object(store, 'get_data_dir', return_value=base/'defaults'), \
             patch.dict(os.environ, {'LYA_DATA_DIR': str(base/'defaults')}):
            modules = ['test_owner_profiles', 'test_passkeys', 'test_approval', 'desktop.check_experience', 'test_legacy_retirement']
            result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
            with patch('desktop.setup_speech.SetupSpeech.say'):
                dialog = OwnerSetupDialog(db_path=base/'preview.enc', profile_setup=True)
                dialog.show()
                app.processEvents()
                for mode in ('ready', 'listening', 'hearing', 'speaking', 'thinking', 'phone'):
                    dialog.mark.mode = mode
                    dialog.mark.active = mode != 'ready'
                    dialog.mark.phase = 1.4
                    dialog.mark.checkpoint = 3 if mode == 'phone' else 1 if mode in ('listening', 'hearing') else 0
                    dialog.next.draw_icon('phone' if mode == 'phone' else 'continue')
                    dialog.mark.update()
                    app.processEvents()
                    dialog.grab().save(str(OUT/f'registration-{mode}.png'))
                dialog.mark.mode, dialog.mark.active = 'speaking', True
                cpu, started = time.process_time(), time.monotonic()
                for _ in range(60):
                    QTest.qWait(50)
                widget_cpu = round(100*(time.process_time()-cpu)/(time.monotonic()-started), 3)
                dialog.resize(320, 280)
                app.processEvents()
                dialog.grab().save(str(OUT/'registration-small.png'))
                dialog.reject()
            script = re.search(r'<script nonce="[^"]+">(.*?)</script>', PAGE, re.S).group(1)
            js = base/'passkeys.js'
            js.write_text(script, encoding='utf-8')
            node = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
            syntax = subprocess.run([str(node), '--check', str(js)], capture_output=True, timeout=10).returncode == 0
            (OUT/'phone-preview.html').write_text(PAGE.replace('__NONCE__', 'synthetic-preview'), encoding='utf-8')
            summary = dict(date='2026-10-09', tests=result.testsRun, failures=len(result.failures),
                errors=len(result.errors), skipped=len(result.skipped), success=result.wasSuccessful() and syntax,
                modules=modules, browser_javascript_syntax=syntax, active_widget_cpu_percent_one_core=widget_cpu,
                owner_store=False, owner_sensors=False, live_enrollment=False, provider_inference=False,
                note='Synthetic signed owner/profile/action checks and native widget only; live phone/voice and full-app load unverified.')
            (OUT/'validation.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
            print(json.dumps(summary, indent=2))
            return 0 if summary['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
