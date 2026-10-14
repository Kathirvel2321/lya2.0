"""Workspace-only fake-data authority qualification; the SQLCipher driver is required."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(HERE.parent/'2026-10-12-memory-hardening/.drivers'))
MODULES = ('test_conversation_contract','test_memory_prototype','test_memory_recovery',
           'test_memory_repository','test_memory_hardening','test_memory_encrypted','test_memory_authority')


def main():
    from sqlcipher3 import dbapi2
    original = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        tempfile.tempdir = folder
        try:
            suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or MODULES)
            log = io.StringIO();result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        finally:tempfile.tempdir = original
    (HERE/'tests.txt').write_text(log.getvalue(),encoding='utf-8')
    passed = result.wasSuccessful() and not result.skipped
    report = dict(date='2026-10-12',tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                  skipped=len(result.skipped),passed=passed,fake_data_only=True,independent_off_host=False,
                  production_paths_connected=False,external_service_called=False,deployed=False)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'{result.testsRun} fake-data checks passed.' if passed else log.getvalue())
    return 0 if passed else 1


if __name__ == '__main__':raise SystemExit(main())
