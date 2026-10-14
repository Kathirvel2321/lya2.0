"""Run fake-data memory checks with all temporary files inside this workspace."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
MODULES = ('test_conversation_contract','test_memory_prototype','test_memory_recovery','test_memory_repository')


def main():
    original = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        if not Path(folder).resolve().is_relative_to(HERE):raise ValueError('Fixture escaped workspace.')
        tempfile.tempdir = folder
        try:
            suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
            log = io.StringIO()
            result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
        finally:tempfile.tempdir = original
    (HERE/'tests.txt').write_text(log.getvalue(),encoding='utf-8')
    report = dict(date='2026-10-12',phase='synthetic_recovery_acknowledgement',
                  tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                  passed=result.wasSuccessful(),fake_data_only=True,production_paths_connected=False,
                  live_storage_encrypted=False,independent_destination_configured=False,
                  key_custody_configured=False,old_writer_fencing_implemented=False,
                  catalogue_rollback_resistance_qualified=False,power_loss_durability_qualified=False,
                  provider_or_external_storage_called=False,deployed=False,dependencies_added=False)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(log.getvalue() if not result.wasSuccessful() else f'{result.testsRun} fake-data checks passed.')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':raise SystemExit(main())
