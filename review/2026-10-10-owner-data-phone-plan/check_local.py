"""Fake identities/keys and temporary encrypted stores; no sensors or real phone."""
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
sys.path[:0]=[str(ROOT),str(ROOT/'desktop')]
os.environ['QT_QPA_PLATFORM']='offscreen'


def main():
    from cryptography.fernet import Fernet
    from security import vault
    from storage import store
    files=['brain/capabilities.py','brain/workflow.py','storage/store.py',
           'desktop/experience.py','test_visitors.py',
           'review/2026-10-10-owner-data-phone-plan/check_local.py']
    for name in files:
        source=(ROOT/name).read_text(encoding='utf-8')
        ast.parse(source,filename=name)
        assert all(line==line.rstrip() for line in source.splitlines()),name
    from experience import OrbDesktop
    with tempfile.TemporaryDirectory(prefix='lya-owner-data-check-') as temp:
        base=Path(temp)
        key=Fernet(Fernet.generate_key())
        with patch.object(vault,'_F',key),patch.object(vault,'_get_fernet',return_value=key), \
             patch.object(store,'get_data_dir',return_value=base/'defaults'), \
             patch.dict(os.environ,{'LYA_DATA_DIR':str(base/'defaults')}):
            modules=['test_visitors','test_owner_profiles','test_passkeys','test_approval',
                     'desktop.check_experience','test_legacy_retirement','test_brain_workflow']
            result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
            summary=dict(date='2026-10-10',tests=result.testsRun,failures=len(result.failures),
                errors=len(result.errors),skipped=len(result.skipped),success=result.wasSuccessful(),modules=modules,
                syntax=True,whitespace=True,usual_launcher_import=True,files=files,
                real_owner_data=False,real_sensors=False,real_phone=False,real_app_launch=False,
                provider_inference=False,cloud_upload=False,mobile_pairing_tested=False)
            (OUT/'validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print(json.dumps(summary,indent=2))
            return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
