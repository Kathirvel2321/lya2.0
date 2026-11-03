"""Review-pinned cold-host plus latest/trust/pack fake tests; no account access."""
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
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    def hashes():
        actual={}
        for name,digest in manifest['reviewed_normalized_sha256'].items():
            path=ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            actual[name]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            assert actual[name]==digest,'Reviewed source differs: '+name
        assert hashlib.sha256((HERE/'recovery-code.zip').read_bytes()).hexdigest()==manifest['code_archive_sha256']
        return actual
    before=hashes();old=tempfile.tempdir;ids=[]
    import test_memory_recovery_host as host
    host.CODE_ARCHIVE=HERE/'recovery-code.zip'
    class Result(unittest.TextTestResult):
        def startTest(self,test):ids.append(test.id());super().startTest(test)
    with tempfile.TemporaryDirectory(prefix='.fake-host-check-',dir=HERE) as home:
        tempfile.tempdir=home
        try:
            with log.open('x',encoding='utf-8') as stream:
                result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(
                    unittest.defaultTestLoader.loadTestsFromNames(('test_memory_recovery_host.RecoveryHostChecks',
                        'test_memory_recovery_latest.LatestRecoveryChecks','test_memory_recovery_trust.RecoveryTrustChecks',
                        'test_memory_recovery_pack.RecoveryPackChecks')))
        finally:tempfile.tempdir=old
    after=hashes()
    data=dict(passed=result.wasSuccessful() and not result.skipped and result.testsRun==32 and len(set(ids))==32,
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        case_ids=ids,platform=sys.platform,fake_data_only=True,cold_archive_restore=host.EVIDENCE,
        code_archive_sha256=manifest['code_archive_sha256'],same_archive_bytes_before_after=True,
        cloud_or_vault_access=False,live_credential_read=False,production_caller_connected=False,
        independent_physical_host_or_whole_latest_store_rollback_qualified=False,
        source_normalized_sha256=before,sources_match_before_after=before==after)
    with report.open('x',encoding='utf-8') as output:output.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps({key:value for key,value in data.items() if key not in ('case_ids','source_normalized_sha256')}))
    return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
