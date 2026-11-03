"""Isolated trust-record/pack checks with generated keys; no account access."""
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
    args=parser.parse_args()
    if not args.name.replace('-','').isalnum():parser.error('Simple new evidence name required.')
    report=HERE/(args.name+'.json');log=HERE/(args.name+'.txt')
    if report.exists() or log.exists():parser.error('Preserve existing evidence.')
    expected=json.loads((HERE/'source-manifest-2.json').read_text())['reviewed_normalized_sha256']
    def hashes():
        actual={}
        for name,digest in expected.items():
            path=ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            actual[name]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            assert actual[name]==digest,'Reviewed source differs: '+name
        return actual
    before=hashes();old=tempfile.tempdir;ids=[]
    class Result(unittest.TextTestResult):
        def startTest(self,test):ids.append(test.id());super().startTest(test)
    with tempfile.TemporaryDirectory(prefix='.fake-trust-check-',dir=HERE) as home:
        tempfile.tempdir=home
        try:
            with log.open('x',encoding='utf-8') as stream:
                result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(
                    unittest.defaultTestLoader.loadTestsFromNames(('test_memory_recovery_trust.RecoveryTrustChecks',
                        'test_memory_recovery_pack.RecoveryPackChecks')))
        finally:tempfile.tempdir=old
    after=hashes()
    from test_memory_recovery_trust import EVIDENCE
    data=dict(passed=result.wasSuccessful() and not result.skipped and result.testsRun==18 and len(set(ids))==18,
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        case_ids=ids,platform=sys.platform,fake_data_only=True,fresh_process=EVIDENCE,
        cloud_or_vault_access=False,live_credential_read=False,production_caller_connected=False,
        independent_physical_host_or_clean_machine=False,source_normalized_sha256=before,sources_match_before_after=before==after)
    with report.open('x',encoding='utf-8') as output:output.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps({key:value for key,value in data.items() if key not in ('case_ids','source_normalized_sha256')}))
    return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
