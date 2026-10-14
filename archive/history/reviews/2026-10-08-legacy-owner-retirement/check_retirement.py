"""Fake-key/temp-store legacy retirement checks; never starts live services."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'desktop')]
os.environ['QT_QPA_PLATFORM']='offscreen'
from cryptography.fernet import Fernet
from security import vault
from storage import store

def main():
    only='--http-retry' in sys.argv
    with tempfile.TemporaryDirectory(prefix='lya-retire-check-') as temp:
        base=Path(temp)
        key=Fernet(Fernet.generate_key())
        with patch.object(vault,'_F',key), patch.object(vault,'_get_fernet',return_value=key), \
             patch.object(store,'get_data_dir',return_value=base/'defaults'), \
             patch.dict(os.environ,{'LYA_DATA_DIR':str(base/'defaults')}):
            modules=(['test_legacy_retirement'] if '--retirement-only' in sys.argv else ['test_passkeys.PasskeyChecks.test_http_capability_origin_host_content_boundaries']
                     if only else ['test_legacy_retirement','desktop.check_experience','test_passkeys','test_approval'])
            result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
            data=dict(tests=result.testsRun, failures=len(result.failures),errors=len(result.errors),success=result.wasSuccessful(),
                      date='2026-10-08',modules=modules,real_owner_store=False,sensors=False,live_provider_calls=False)
            filename='retirement-validation.json' if '--retirement-only' in sys.argv else 'http-retry.json' if only else 'validation.json'
            (Path(__file__).parent/filename).write_text(json.dumps(data,indent=2),encoding='utf-8')
            print(json.dumps(data,indent=2))
            return 0 if result.wasSuccessful() else 1

if __name__=='__main__':
    raise SystemExit(main())
