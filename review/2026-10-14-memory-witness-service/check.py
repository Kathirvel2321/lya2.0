"""Workspace-only fake-key loopback protocol checks; does not deploy a service."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))


def main():
    original=tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        tempfile.tempdir=folder
        try:
            log=io.StringIO()
            result=unittest.TextTestRunner(stream=log,verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromName('test_memory_witness_service'))
        finally:tempfile.tempdir=original
    (HERE/'tests.txt').write_text(log.getvalue(),encoding='utf-8')
    report=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        passed=result.wasSuccessful() and not result.skipped,fake_data_only=True,loopback_only=True,
        authority_network_adapter_connected=False,witness_independently_hosted=False,real_keys_created=False)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report) if report['passed'] else log.getvalue())
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
