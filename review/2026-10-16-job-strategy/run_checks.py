"""Reviewed fake-data regression selection; never an owner-device/live-model test.

Run with the project's test dependencies. On non-Windows hosts, the import-only
DPAPI shim refuses every operation; fixtures must supply disposable Fernet keys.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
SELECTION = ['test_job_engine', 'test_tech_news', 'test_web_research', 'test_answer_verification', 'test_research_adapter', 'test_answering_context',
             'test_brain_workflow', 'test_mobile.MobileChecks', 'test_mobile_voice.PhoneChecks',
             'test_mobile_conversation.ConversationChecks', 'test_mobile_timing']
SOURCES = ['tools/job_policy_lab.py','cloud/job_policy.py','cloud/job_store.py','cloud/job_runner.py','cloud/job_adapters.py','test_job_engine.py','cloud/news_sources.py','cloud/tech_news.py','desktop/news.py','desktop/app.py','desktop/experience.py','test_tech_news.py','cloud/evidence.py', 'cloud/public_search.py', 'cloud/web_reader.py', 'cloud/web_research.py',
           'brain/research.py', 'cloud/mobile_runtime.py', 'test_web_research.py', 'test_research_adapter.py', 'cloud/answering.py', 'cloud/mobile.py', 'brain/workflow.py', 'brain/verification.py',
           'test_answering_context.py', 'test_mobile.py', 'tools/setup_mobile_connection.py',
           'tools/update_mobile_conversation.py', 'tools/update_mobile_voice.py']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deps', type=Path, help='Optional test-only dependency directory')
    parser.add_argument('--qt-deps', type=Path, help='Isolated PySide6 test dependencies')
    parser.add_argument('--name', default='validation', help='New evidence filename stem')
    args = parser.parse_args()
    if not args.name.replace('-', '').replace('_', '').isalnum():
        parser.error('Use a simple evidence filename stem.')
    destination = Path(__file__).parent
    report_path, log_path = destination / (args.name + '.json'), destination / (args.name + '.txt')
    if report_path.exists() or log_path.exists():
        parser.error('Preserve existing evidence; select a new --name.')
    sys.path.insert(0, str(ROOT))
    if args.deps:
        sys.path.insert(0, str(args.deps.resolve()))
    if args.qt_deps:
        sys.path.insert(0, str(args.qt_deps.resolve()))
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    if os.name != 'nt':
        shim = types.ModuleType('win32crypt')
        def forbidden(*args, **kwargs):
            raise AssertionError('DPAPI is forbidden in this synthetic Linux selection.')
        shim.CryptProtectData = shim.CryptUnprotectData = forbidden
        sys.modules['win32crypt'] = shim
    class RecordedResult(unittest.TextTestResult):
        def startTest(self, test):
            case_ids.append(test.id())
            super().startTest(test)
    case_ids, stream = [], io.StringIO()
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in SELECTION)
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=RecordedResult).run(suite)
    log_path.write_text(stream.getvalue(), encoding='utf-8')
    report = {
        'date': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(),
        'platform': platform.system(), 'dpapi_shim': os.name != 'nt',
        'data': 'synthetic_only', 'live_model_calls': 0, 'real_device_acceptance': 'not_run',
        'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'success': result.wasSuccessful(), 'case_ids': case_ids,
        'source_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES},
    }
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('tests', 'failures', 'errors', 'skipped', 'success')}))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
