"""Explicit fake-only Windows DPAPI/worker/pack checks; no live account."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(HERE.parent/'2026-10-13-memory-linux'),
              str(HERE.parent/'2026-10-12-memory-hardening/.drivers')]
MODULES=('test_memory_b2_credential.CredentialChecks',)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',required=True)
    args=parser.parse_args()
    if sys.platform!='win32':parser.error('This qualification exercises real Windows DPAPI.')
    if not args.name.replace('-','').isalnum():parser.error('Simple evidence name required.')
    report=HERE/(args.name+'.json');log=HERE/(args.name+'.txt')
    if report.exists() or log.exists():parser.error('Preserve existing evidence; use a new name.')
    expected=json.loads((HERE/'input-source-manifest.json').read_text())['reviewed_normalized_sha256']
    def hashes():
        result={}
        for name in expected:
            path=ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            result[name]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        assert result==expected,'Reviewed source differs.'
        return result
    before=hashes();ids=[];old=tempfile.tempdir
    class Result(unittest.TextTestResult):
        def startTest(self,test):ids.append(test.id());super().startTest(test)
    with tempfile.TemporaryDirectory(prefix='.fake-credential-check-',dir=HERE) as home:
        tempfile.tempdir=home
        try:
            with log.open('w',encoding='utf-8') as stream:
                result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(
                    unittest.defaultTestLoader.loadTestsFromNames(MODULES))
        finally:tempfile.tempdir=old
    after=hashes()
    passed=result.wasSuccessful() and not result.skipped and result.testsRun==19 and len(set(ids))==19
    data=dict(passed=passed,tests_run=result.testsRun,distinct_cases=len(set(ids)),failures=len(result.failures),
        errors=len(result.errors),skipped=len(result.skipped),case_ids=ids,fake_data_only=True,
        real_windows_dpapi=True,b2_https_mocked=True,live_access_created=False,live_upload=False,
        sources_match_before_after=before==after,source_normalized_sha256=before,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    report.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in data.items() if key not in ('case_ids','source_normalized_sha256','runner_sha256')}))
    if not passed:print(log.read_text(encoding='utf-8'))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
