"""Eight isolated full-authority transfer cases; fake keys and no provider access."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(HERE.parent/'2026-10-13-memory-linux')]
if sys.platform=='win32':sys.path.insert(2,str(HERE.parent/'2026-10-12-memory-hardening/.drivers'))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',required=True)
    parser.add_argument('--case');args=parser.parse_args()
    if not args.name.replace('-','').isalnum():parser.error('Use a simple new evidence name.')
    report=HERE/(args.name+'.json');log=HERE/(args.name+'.txt')
    if report.exists() or log.exists():parser.error('Preserve existing evidence.')
    manifest=json.loads((HERE/'source-manifest-2.json').read_text())
    def hashes():
        for name,digest in manifest['reviewed_normalized_sha256'].items():
            path=ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            assert hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==digest,name
    hashes()
    from test_memory_authority_transfer import AuthorityTransferChecks
    names=[name for name in unittest.defaultTestLoader.getTestCaseNames(AuthorityTransferChecks) if name.startswith('test_transfer_')]
    assert len(names)==8
    if args.case:
        if args.case not in names:parser.error('Use one exact reviewed case name.')
        names=[args.case]
    suite=unittest.TestSuite(AuthorityTransferChecks(name) for name in names);old=tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.at-',dir=ROOT) as folder:
        tempfile.tempdir=folder
        try:
            with log.open('x',encoding='utf-8') as output:result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
        finally:tempfile.tempdir=old
    hashes()
    data=dict(passed=result.wasSuccessful() and not result.skipped and result.testsRun==len(names),tests_run=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),case_names=names,
        platform=sys.platform,source_hashes_match_before_after=True,reviewed_sources=len(manifest['reviewed_normalized_sha256']),
        fake_data_only=True,real_enrollment=False,production_connected=False,cloud_or_vault_access=False)
    with report.open('x') as output:json.dump(data,output,indent=2);output.write('\n')
    print(json.dumps(data));return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
