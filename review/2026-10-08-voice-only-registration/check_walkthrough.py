"""Synthetic GUI/crypto checks; actual native dot previews, no owner enrollment."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
sys.path[:0] = [str(ROOT), str(ROOT / 'desktop')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def main():
    from cryptography.fernet import Fernet
    from security import vault
    from storage import store
    from desktop.owner_setup import OwnerSetupDialog
    from security.passkeys import PAGE
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory(prefix='lya-dot-check-') as temp:
        base = Path(temp)
        key = Fernet(Fernet.generate_key())
        with patch.object(vault, '_F', key), patch.object(vault, '_get_fernet', return_value=key), \
             patch.object(store, 'get_data_dir', return_value=base / 'defaults'), \
             patch.dict(os.environ, {'LYA_DATA_DIR': str(base / 'defaults')}):
            modules = ['test_passkeys', 'test_approval', 'desktop.check_experience']
            result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
            summary = dict(date='2026-10-08', tests=result.testsRun, failures=len(result.failures),
                errors=len(result.errors), success=result.wasSuccessful(), modules=modules,
                owner_store=False, owner_sensors=False, live_phone_enrollment=False)
            pending = SimpleNamespace(url='http://localhost/synthetic-never-opened', done=threading.Event(),
                                      deadline=time.monotonic()+180, close=lambda: None)
            with patch('desktop.setup_speech.SetupSpeech.say'):
                dialog = OwnerSetupDialog(db_path=base/'preview.enc', reduced_motion=False,
                    open_browser=lambda _: True, ceremony_factory=lambda **_: pending)
                dialog.show()
                QTest.qWait(250)
                dialog.grab().save(str(OUT/'walkthrough-arrival.png'))
                dialog._speaking(True)
                QTest.qWait(250)
                dialog.grab().save(str(OUT/'walkthrough-speaking.png'))
                dialog._speaking(False)
                dialog.advance()
                QTest.qWait(250)
                dialog.set_input_phase('listening')
                dialog.grab().save(str(OUT/'walkthrough-name.png'))
                dialog.advance()
                QTest.qWait(250)
                dialog.grab().save(str(OUT/'walkthrough-recovery.png'))
                dialog.advance()
                QTest.qWait(250)
                dialog.grab().save(str(OUT/'walkthrough-phone.png'))
                cpu, started = time.process_time(), time.monotonic()
                for _ in range(60):
                    QTest.qWait(50)
                summary['active_widget_process_cpu_percent_one_core'] = round(100*(time.process_time()-cpu)/(time.monotonic()-started), 3)
                dialog.reject()
            page = PAGE.replace('__NONCE__', 'synthetic-preview')
            (OUT/'phone-preview.html').write_text(page, encoding='utf-8')
            script = re.search(r'<script nonce="[^"]+">(.*?)</script>', PAGE, re.S).group(1)
            js = base/'passkeys.js'
            js.write_text(script, encoding='utf-8')
            node = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
            summary['browser_javascript_syntax'] = subprocess.run([str(node),'--check',str(js)],capture_output=True,timeout=10).returncode == 0
            summary['runtime_bitmap_assets'] = 0
            summary['visible_native_labels'] = 0
            summary['actual_phone_and_owner_voice'] = 'not tested'
            (OUT/'validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print(json.dumps(summary,indent=2))
            return 0 if result.wasSuccessful() and summary['browser_javascript_syntax'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
