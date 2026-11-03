"""Explicit synthetic worker/custody/pack checks; no test discovery or network."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=Path.cwd() if sys.platform=='linux' else HERE.parents[1]
sys.path.insert(0,str(ROOT))
if sys.platform=='win32':sys.path[1:1]=[str(HERE.parent/'2026-10-13-memory-linux'),str(HERE.parent/'2026-10-12-memory-hardening/.drivers')]
MODULES=('test_memory_b2_backup.B2BackupChecks','test_memory_recovery_pack','test_memory_custody','test_qualification')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True);args=parser.parse_args()
    if not args.name.replace('-','').isalnum():parser.error('Simple evidence name required.')
    output=HERE/(args.name+'.json');log=HERE/(args.name+'.txt')
    if output.exists() or log.exists():parser.error('Preserve earlier evidence; choose a new name.')
    baseline=json.loads((HERE/'source-manifest.json').read_text())['reviewed_normalized_sha256']
    def hashes():
        values={}
        for name in baseline:
            p=ROOT/name
            if sys.platform=='win32' and name=='test_qualification.py':p=HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
            values[name]=hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        if values!=baseline:raise AssertionError('Reviewed source inventory differs.')
        return values
    before=hashes();ids=[];original=tempfile.tempdir
    class Result(unittest.TextTestResult):
        def startTest(self,test):ids.append(test.id());super().startTest(test)
    with tempfile.TemporaryDirectory(prefix='.fake-backup-worker-',dir=ROOT if sys.platform=='linux' else HERE) as home:
        tempfile.tempdir=home
        try:
            with log.open('w',encoding='utf-8') as stream:
                result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(
                    unittest.defaultTestLoader.loadTestsFromNames(MODULES))
        finally:tempfile.tempdir=original
    after=hashes()
    assert result.testsRun==47 and len(set(ids))==47,'Expected exactly 47 distinct checks.'
    report=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        passed=result.wasSuccessful() and not result.skipped,case_ids=ids,fake_data_only=True,
        b2_https_mocked=True,live_credentials_used=False,live_upload_performed=False,
        source_normalized_sha256=before,post_run_sources_match=before==after,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('case_ids','source_normalized_sha256','runner_sha256')}))
    if not report['passed']:print(log.read_text(encoding='utf-8'))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
