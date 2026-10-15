"""Reviewed fake-data selection; Linux runs from the existing verified lab cwd."""
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
MODULES=(('test_memory_witness_cgroup','test_memory_witness_resources','test_memory_witness_admission',
          'test_memory_witness_process','test_memory_witness_tls','test_memory_receipt_retirement',
          'test_memory_witness_capacity','test_memory_witness_service','test_memory_network_authority') if LINUX else
         ('test_memory_witness_resources.BudgetContractChecks','test_memory_witness_admission',
          'test_memory_witness_process','test_memory_witness_tls'))


def sources():
    expected=json.loads((HERE/'lab-source-manifest.json').read_text())['current_workspace_sha256']
    actual={}
    for name,digest in expected.items():
        path=ROOT/name
        if not LINUX and name=='test_qualification.py':path=HERE.parent/'2026-10-13-memory-linux/test_qualification.py'
        actual[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual[name]!=digest:raise AssertionError('Reviewed source mismatch: '+name)
    return actual


def main():
    before=sources();prefix='wsl-' if LINUX else ''
    original=tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fixtures-cgroup-',dir=ROOT if LINUX else HERE) as folder:
        tempfile.tempdir=folder
        try:
            with (HERE/(prefix+'tests.txt')).open('w',encoding='utf-8') as log:
                result=unittest.TextTestRunner(stream=log,verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or MODULES))
        finally:tempfile.tempdir=original
    after=sources()
    import test_memory_witness_cgroup as cgroup
    report=dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        passed=result.wasSuccessful() and not result.skipped,fake_data_only=True,loopback_only=True,
        cgroup_enforcement_tested=LINUX,installed_services_changed=False,production_paths_connected=False,
        source_sha256=before,post_run_sources_match=before==after,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),metrics=cgroup.METRICS)
    (HERE/(prefix+'validation.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','runner_sha256')})
          if report['passed'] else (HERE/(prefix+'tests.txt')).read_text(encoding='utf-8'))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
