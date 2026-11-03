"""Recovery-pack and preceding fake-data checks; verified Ubuntu lab cwd on Linux."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
LINUX=sys.platform=='linux'
ROOT=Path.cwd() if LINUX else HERE.parents[1]
sys.path.insert(0,str(ROOT))
if not LINUX:
    sys.path[1:1]=[str(HERE.parent/'2026-10-13-memory-linux'),str(HERE.parent/'2026-10-12-memory-hardening/.drivers')]
MODULES=(('test_memory_recovery_pack','test_memory_custody','test_qualification','test_memory_witness_disk','test_memory_witness_cgroup','test_memory_witness_resources',
          'test_memory_witness_admission','test_memory_witness_process','test_memory_witness_tls',
          'test_memory_receipt_retirement','test_memory_witness_capacity','test_memory_witness_service',
          'test_memory_network_authority') if LINUX else
         ('test_memory_recovery_pack','test_memory_custody','test_qualification','test_memory_witness_disk.DiskContractChecks','test_memory_witness_resources.BudgetContractChecks',
          'test_memory_witness_admission','test_memory_witness_process','test_memory_witness_tls'))


def sources():
    expected=json.loads((HERE/'lab-source-manifest.json').read_text(encoding='utf-8'))['reviewed_normalized_sha256']
    actual={}
    for name,digest in expected.items():
        path=ROOT/name
        if not LINUX and name=='test_qualification.py':path=HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
        actual[name]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        if actual[name]!=digest:raise AssertionError('Reviewed source mismatch: '+name)
    return actual


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',default='wsl-validation' if LINUX else 'windows-validation')
    parser.add_argument('modules',nargs='*');args=parser.parse_args()
    if not args.name.replace('-','').isalnum():parser.error('Use a simple evidence name.')
    report_path=HERE/(args.name+'.json');log_path=HERE/(args.name+'.txt')
    if report_path.exists() or log_path.exists():parser.error('Preserve evidence; choose a new name.')
    before=sources();original=tempfile.tempdir;case_ids=[]
    class RecordedResult(unittest.TextTestResult):
        def startTest(self,test):case_ids.append(test.id());super().startTest(test)
    with tempfile.TemporaryDirectory(prefix='.fixtures-pack-run-',dir=ROOT if LINUX else HERE) as folder:
        tempfile.tempdir=folder
        try:
            with log_path.open('w',encoding='utf-8') as log:
                result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(
                    unittest.defaultTestLoader.loadTestsFromNames(args.modules or MODULES))
        finally:tempfile.tempdir=original
    after=sources()
    import test_memory_witness_disk as disk
    import test_memory_recovery_pack as packs
    report=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        passed=result.wasSuccessful() and not result.skipped,fake_data_only=True,loopback_only=True,
        actual_namespace_quota_tested=bool(disk.METRICS),fresh_process_restore=packs.EVIDENCE,
        production_paths_connected=False,host_mounts_changed=False,
        source_normalized_sha256=before,post_run_sources_match=before==after,case_ids=case_ids,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),metrics=disk.METRICS)
    report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_normalized_sha256','runner_sha256','case_ids')})
          if report['passed'] else log_path.read_text(encoding='utf-8'))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
