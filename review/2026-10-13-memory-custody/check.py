"""Workspace-only custody and portable-storage qualification with generated fake keys."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT),str(HERE.parent/'2026-10-13-memory-linux'),
               str(HERE.parent/'2026-10-12-memory-hardening/.drivers')]


def main():
    from sqlcipher3 import dbapi2
    original = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        tempfile.tempdir = folder
        try:
            suite = unittest.defaultTestLoader.loadTestsFromNames(['test_memory_custody','test_qualification'])
            log = io.StringIO();result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        finally:tempfile.tempdir = original
    (HERE/'tests.txt').write_text(log.getvalue(),encoding='utf-8')
    report = dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
                  passed=result.wasSuccessful() and not result.skipped,fake_data_only=True,password_manager_connected=False,
                  witness_independently_hosted=False,production_paths_connected=False,real_keys_created=False)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report) if report['passed'] else log.getvalue())
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
