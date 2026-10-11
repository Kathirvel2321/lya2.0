"""Reviewed fake-data regressions plus unsigned private HTTPS checks; no deployment."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TESTS = [
    'test_mobile_timing', 'test_mobile', 'test_mobile_voice', 'test_mobile_conversation',
    'test_conversation_contract', 'test_memory_prototype', 'test_memory_recovery',
    'test_visitors.VisitorChecks.test_owner_tone_is_personal_without_sending_identity_or_private_data',
    'test_visitors.VisitorChecks.test_public_owner_question_needs_no_approval_and_private_context_never_leaks',
]
SOURCES = [
    'brain/conversation.py', 'brain/memory_prototype.py', 'brain/memory_recovery.py',
    'brain/workflow.py', 'cloud/mobile.py', 'cloud/mobile.html', 'cloud/mobile_runtime.py',
    'cloud/mobile_speech.py', 'cloud/mobile_tts.py', 'cloud/ssh_session.py',
    'desktop/experience.py', 'security/passkeys.py', 'storage/store.py', 'storage/recovery.py',
]


def hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}


def run(name, command, timeout=90):
    started = time.perf_counter()
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', errors='replace', timeout=timeout)
    output = process.stdout + process.stderr
    (HERE/(name+'.log')).write_text(output, encoding='utf-8')
    result = dict(passed=process.returncode == 0, exit_code=process.returncode,
                  duration_s=round(time.perf_counter()-started,3))
    if name == 'unittest':
        count = re.search(r'Ran (\d+) tests?', output)
        result['tests_run'] = int(count[1]) if count else 0
        result['passed'] &= result['tests_run'] >= 82
    print(json.dumps({name:result}), flush=True)
    return result


def fixture(source, *, callable_main=False):
    # Preserve prior evidence: run the reviewed source with outputs in this folder.
    code = "from pathlib import Path; import sys; sys.path.insert(0,str(Path.cwd())); "
    code += f"p=Path({source!r}); scope={{'__name__':'checkpoint_fixture','__file__':str(p.resolve())}}; "
    if not callable_main:
        code += f"scope['__file__']={str(HERE/Path(source).name)!r}; "
    code += "exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),scope); "
    if callable_main:
        code += f"scope['__file__']={str(HERE/Path(source).name)!r}; scope['main']()"
    return [sys.executable, '-c', code]


def main():
    before = hashes()
    results = {}
    results['unittest'] = run('unittest',[sys.executable,'-m','unittest',*TESTS,'-v'])
    results['client'] = run('client',['node','review/2026-10-10-mobile-conversation/check_client.js'])
    results['http_baseline'] = run('http_baseline',fixture('review/2026-10-11-foundation/baseline.py',callable_main=True))
    results['layout'] = run('layout',fixture('review/2026-10-11-one-lya/check_layout.py'))
    # This probe reads the private page and posts only an unsigned empty session request.
    # Suppress network exception text: an error may contain the configured private hostname.
    network = fixture('review/2026-10-11-foundation/check_network.py')
    code = network[-1]
    network[-1] = "try:\n " + code + "\nexcept Exception as error:\n print(type(error).__name__); raise SystemExit(1)"
    results['private_https'] = run('private_https',network)
    after = hashes()
    report = dict(date='2026-10-11',scope='four_recent_slices_and_selected_existing_regressions',
                  checks=results,success=all(item['passed'] for item in results.values()) and before == after,
                  checked_source_hashes_unchanged=before == after,source_sha256=after,
                  real_owner_stores_or_credentials_used=False,real_enrollment=False,
                  human_audio_or_sensors_used=False,provider_called=False,
                  deployed_or_runtime_changed=False,paid_resources_added=False,
                  live_shared_memory_connected=False,real_phone_acceptance=False,
                  full_repository_suite=False)
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'success':report['success'],'tests_run':results['unittest']['tests_run']}))
    return 0 if report['success'] else 1


if __name__ == '__main__':raise SystemExit(main())
