"""Workspace-only fake-data regression runner; no private stores or external services."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
if (HERE/'.drivers').exists():sys.path.insert(0,str(HERE/'.drivers'))
MODULES = ('test_conversation_contract','test_memory_prototype','test_memory_recovery',
           'test_memory_repository','test_memory_hardening','test_memory_encrypted')


def main():
    original = tempfile.tempdir
    if not sys.argv[1:]:
        from sqlcipher3 import dbapi2  # Qualification must run, not silently skip a missing engine.
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        if not Path(folder).resolve().is_relative_to(HERE):raise ValueError('Fixture escaped workspace.')
        tempfile.tempdir = folder
        try:
            suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or MODULES)
            log = io.StringIO()
            result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        finally:tempfile.tempdir = original
    (HERE/'tests.txt').write_text(log.getvalue(),encoding='utf-8')
    report = dict(date='2026-10-12',tests_run=result.testsRun,failures=len(result.failures),
                  errors=len(result.errors),skipped=len(result.skipped),passed=result.wasSuccessful(),fake_data_only=True,
                  external_service_called=False,production_paths_connected=False,deployed=False)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue() if not result.wasSuccessful() else f'{result.testsRun} fake-data checks passed.')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':raise SystemExit(main())
