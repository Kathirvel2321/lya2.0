"""Fake keys and temporary stores only. No real account, sensor or provider call."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
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
    files=['cloud/mobile.py','cloud/mobile_client.py','cloud/mobile_runtime.py','test_mobile.py',
           'brain/workflow.py','brain/capabilities.py','desktop/experience.py','security/policy.py',
           'tools/setup_mobile_connection.py','desktop/check_experience.py',
           'review/2026-10-10-mobile-connection/check_connection.py']
    for name in files:
        source=(ROOT/name).read_text(encoding='utf-8')
        ast.parse(source,filename=name)
        assert all(line==line.rstrip() for line in source.splitlines()),name
    from experience import OrbDesktop
    from tools.setup_mobile_connection import STAGE,NETWORK,ACTIVATE
    for program in (STAGE,NETWORK,ACTIVATE):compile(program,'remote-setup','exec')
    script=re.search(r'<script nonce="__NONCE__">(.*?)</script>',(ROOT/'cloud/mobile.html').read_text(encoding='utf-8'),re.S).group(1)
    subprocess.run(['node','--check','--input-type=commonjs'],input=script.encode(),check=True,capture_output=True)
    with tempfile.TemporaryDirectory(prefix='lya-mobile-check-') as temp:
        base=Path(temp);key=Fernet(Fernet.generate_key())
        with patch.object(vault,'_F',key),patch.object(vault,'_get_fernet',return_value=key), \
             patch.object(store,'get_data_dir',return_value=base/'defaults'), \
             patch.dict(os.environ,{'LYA_DATA_DIR':str(base/'defaults')}):
            modules=['test_passkeys','test_approval','test_visitors','test_owner_profiles',
                     'desktop.check_experience','test_legacy_retirement','test_brain_workflow','test_mobile']
            result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
            summary=dict(date='2026-10-10',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                skipped=len(result.skipped),success=result.wasSuccessful(),modules=modules,syntax=True,whitespace=True,
                usual_launcher_import=True,browser_javascript_syntax=True,installer_program_syntax=True,
                real_owner_data=False,real_sensors=False,real_phone=False,
                app_launch=False,provider_call=False,cloud_upload=False)
            (OUT/'validation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            print(json.dumps(summary,indent=2))
            return 0 if result.wasSuccessful() else 1


if __name__=='__main__':raise SystemExit(main())
