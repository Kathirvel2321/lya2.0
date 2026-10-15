"""Workspace-only fake-data TLS process lifecycle and preceding TLS checks."""
import hashlib
import json
from pathlib import Path
import ssl
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(HERE.parent/'2026-10-13-memory-linux'),str(HERE.parent/'2026-10-12-memory-hardening/.drivers')]
MODULES=('test_memory_witness_process','test_memory_witness_tls')


def main():
    from sqlcipher3 import dbapi2
    original=tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fixtures-',dir=HERE) as folder:
        tempfile.tempdir=folder
        try:
            with (HERE/'tests.txt').open('w',encoding='utf-8') as log:
                result=unittest.TextTestRunner(stream=log,verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or MODULES))
        finally:tempfile.tempdir=original
    sources=('brain/memory_witness_service.py','brain/memory_network_authority.py','brain/memory_custody.py',
             'test_memory_witness_process.py','test_memory_witness_tls.py',
             'review/2026-10-15-memory-witness-process/check.py')
    report=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        passed=result.wasSuccessful() and not result.skipped,fake_data_only=True,loopback_only=True,
        tls_server_separate_process=True,production_paths_connected=False,witness_independently_hosted=False,
        production_keys_created=False,openssl=ssl.OPENSSL_VERSION,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report) if report['passed'] else (HERE/'tests.txt').read_text(encoding='utf-8'))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
