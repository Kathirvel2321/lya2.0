"""Ten fake-owner/DPAPI/offscreen checks; never run the real owner setup window."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',required=True)
    parser.add_argument('--case');args=parser.parse_args()
    if sys.platform!='win32':parser.error('Native Windows DPAPI checks required; no simulated production protection.')
    if not args.name.replace('-','').isalnum():parser.error('Use a simple new evidence name.')
    report=HERE/(args.name+'.json');log=HERE/(args.name+'.txt')
    if report.exists() or log.exists():parser.error('Preserve previous evidence.')
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    def check():
        for name,digest in manifest['reviewed_normalized_sha256'].items():
            path=ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            assert hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
    check();os.environ['QT_QPA_PLATFORM']='offscreen'
    from test_memory_owner_keys import OwnerKeysChecks
    names=unittest.defaultTestLoader.getTestCaseNames(OwnerKeysChecks);assert len(names)==10
    if args.case:
        if args.case not in names:parser.error('Use one exact reviewed case name.')
        names=[args.case]
    old=tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.ok-',dir=ROOT) as folder:
        tempfile.tempdir=folder
        try:
            with log.open('x',encoding='utf-8') as output:
                result=unittest.TextTestRunner(stream=output,verbosity=2).run(unittest.TestSuite(OwnerKeysChecks(n) for n in names))
        finally:tempfile.tempdir=old
    check()
    data=dict(passed=result.wasSuccessful() and not result.skipped and result.testsRun==len(names),tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),case_names=names,
        native_windows_dpapi=True,signed_fake_passkeys=True,qt_offscreen=True,
        reviewed_sources=len(manifest['reviewed_normalized_sha256']),source_hashes_match_before_after=True,
        real_key_enrollment_executed=False,real_owner_store_or_vault_read=False,production_connected=False,network_provider_access=False)
    with report.open('x') as output:json.dump(data,output,indent=2);output.write('\n')
    print(json.dumps(data));return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
