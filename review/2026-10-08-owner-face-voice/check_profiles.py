"""Synthetic safety/regression checks and actual native previews without sensors."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'desktop')]
os.environ['QT_QPA_PLATFORM'] = 'offscreen'


def main():
    from cryptography.fernet import Fernet
    from security import vault
    from storage import store
    from PySide6.QtWidgets import QApplication
    from desktop.owner_setup import OwnerSetupDialog
    out = Path(__file__).parent
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    with tempfile.TemporaryDirectory(prefix='lya-profile-tests-') as temp:
        base = Path(temp)
        key = Fernet(Fernet.generate_key())
        with patch.object(vault,'_F',key), patch.object(vault,'_get_fernet',return_value=key), \
             patch.object(store,'get_data_dir',return_value=base/'defaults'), \
             patch.dict(os.environ,{'LYA_DATA_DIR':str(base/'defaults')}):
            modules = ['test_owner_profiles','test_passkeys','test_approval','desktop.check_experience','test_legacy_retirement']
            if '--http-retry' in sys.argv:
                modules = ['test_passkeys.PasskeyChecks.test_http_capability_origin_host_content_boundaries']
            result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
            with patch('desktop.setup_speech.SetupSpeech.say'):
                dialog = OwnerSetupDialog(db_path=base/'preview.enc', profile_setup=True, reduced_motion=False)
                dialog.show()
                app.processEvents()
                dialog.grab().save(str(out/'registration-controls.png'))
                dialog.stage = 'profile_review'
                dialog.set_step('REVIEW','','','Synthetic profile review. No owner data.', 'Save my profiles')
                dialog._speaking(True)
                app.processEvents()
                dialog.grab().save(str(out/'registration-review.png'))
                dialog.reject()
            summary = dict(date='2026-10-09', tests=result.testsRun, failures=len(result.failures),
                errors=len(result.errors), skipped=len(result.skipped), success=result.wasSuccessful(),
                modules=modules, real_owner_data=False, real_sensors=False, live_provider_calls=False)
            filename = 'http-retry.json' if '--http-retry' in sys.argv else 'validation.json'
            (out/filename).write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print(json.dumps(summary,indent=2))
            return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
