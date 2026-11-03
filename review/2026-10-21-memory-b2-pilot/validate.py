"""Fake-only regression of B2 missing-object compatibility; no live credential."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pilot

HERE=Path(__file__).resolve().parent
ROOT=pilot.ROOT


def main():
    report=HERE/'compatibility-validation-2.json';log=HERE/'compatibility-validation-2.txt'
    if report.exists() or log.exists():raise SystemExit('Preserve existing evidence.')
    baseline=json.loads((HERE.parent/'2026-10-20-memory-b2-setup-diagnostics/input-source-manifest.json').read_text())['reviewed_normalized_sha256']
    paths={name:(ROOT/name if name!='test_qualification.py' else HERE.parent/'2026-10-13-memory-linux/test_qualification.py') for name in baseline}
    paths.update({str(path.relative_to(ROOT)).replace('\\','/'):path for path in (HERE/'pilot.py',HERE/'check.py',Path(__file__))})
    def hashes():return {name:hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name,path in paths.items()}
    before=hashes()
    changed=sorted(name for name,digest in baseline.items() if before[name]!=digest)
    assert changed==['brain/memory_b2_backup.py','test_memory_b2_backup.py'], 'Unexpected preceding source change.'
    suite=unittest.defaultTestLoader.loadTestsFromNames(('test_memory_b2_backup.B2BackupChecks',
        'test_memory_b2_credential.CredentialChecks'))
    spec=importlib.util.spec_from_file_location('reviewed_pilot_checks',HERE/'check.py')
    checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(checks.PilotChecks))
    old=tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.fake-compatibility-',dir=HERE) as home:
        tempfile.tempdir=home
        try:
            with log.open('x',encoding='utf-8') as stream:
                result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        finally:tempfile.tempdir=old
    after=hashes()
    data=dict(passed=result.wasSuccessful() and not result.skipped and before==after,
        tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        fake_data_only=True,b2_https_mocked=True,live_credential_loaded=False,
        changed_preceding_sources=changed,sources_match_before_after=before==after,source_normalized_sha256=before)
    with report.open('x',encoding='utf-8') as output:output.write(json.dumps(data,indent=2)+'\n')
    print(json.dumps({key:value for key,value in data.items() if key!='source_normalized_sha256'}))
    return 0 if data['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
