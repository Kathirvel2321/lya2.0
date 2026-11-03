"""Seven new fake owner/publication cases plus ten acknowledgement regressions."""
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
    parser.add_argument('--case',help='One exact reviewed case name; otherwise run all seventeen.')
    args=parser.parse_args()
    if not args.name.replace('-','').isalnum():parser.error('Simple new evidence name required.')
    report=HERE/(args.name+'.json');log=HERE/(args.name+'.txt')
    if report.exists() or log.exists():parser.error('Preserve existing evidence.')
    manifest=json.loads((HERE/'source-manifest-2.json').read_text())
    def hashes():
        actual={}
        for name,digest in manifest['reviewed_normalized_sha256'].items():
            path=ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            actual[name]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            assert actual[name]==digest,'Reviewed source differs: '+name
        for name,digest in manifest['preserved_artifact_sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'Prior evidence differs: '+name
        return actual
    before=hashes();old=tempfile.tempdir;ids=[]
    import test_memory_recovery_host as host
    host.CODE_ARCHIVE=HERE.parent/'2026-10-21-memory-recovery-host/recovery-code.zip'
    from test_memory_publication_authority import PublicationAuthorityChecks
    from test_memory_publication_reactivation import PublicationReactivationChecks
    loader=unittest.defaultTestLoader
    suite=loader.loadTestsFromTestCase(PublicationAuthorityChecks)
    names=[name for name in loader.getTestCaseNames(PublicationReactivationChecks) if name.startswith('test_reactivation_')]
    assert len(names)==7
    suite.addTests(PublicationReactivationChecks(name) for name in names)
    if args.case:
        selected=[test for test in suite if test._testMethodName==args.case]
        if len(selected)!=1:parser.error('Select exactly one of the seventeen reviewed cases.')
        suite=unittest.TestSuite(selected)
    expected=suite.countTestCases()
    class Result(unittest.TextTestResult):
        def startTest(self,test):ids.append(test.id());super().startTest(test)
    with tempfile.TemporaryDirectory(prefix='.own-',dir=ROOT) as home:
        tempfile.tempdir=home
        try:
            with log.open('x',encoding='utf-8') as stream:
                result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
        finally:tempfile.tempdir=old
    after=hashes()
    new_count=sum(case.startswith('test_memory_publication_reactivation.') for case in ids)
    data=dict(passed=result.wasSuccessful() and not result.skipped and result.testsRun==expected and len(set(ids))==expected,
        tests_run=result.testsRun,new_cases=new_count,regression_cases=len(ids)-new_count,failures=len(result.failures),errors=len(result.errors),
        skipped=len(result.skipped),case_ids=ids,platform=sys.platform,fake_data_only=True,
        source_normalized_sha256=before,sources_match_before_after=before==after,
        preserved_artifacts_checked=len(manifest['preserved_artifact_sha256']),
        cloud_or_vault_access=False,live_credential_read=False,production_caller_connected=False,
        real_owner_enrollment=False,physical_independent_custody_qualified=False)
    with report.open('x',encoding='utf-8') as output:output.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps({key:value for key,value in data.items() if key not in ('case_ids','source_normalized_sha256')}))
    return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
