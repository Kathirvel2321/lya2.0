"""Focused synthetic shared-client integration and six existing client regressions."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(HERE.parent / '2026-10-13-memory-linux'),
                str(HERE.parent / '2026-10-12-memory-hardening/.drivers')]
SOURCES = ['brain/shared_memory.py', 'cloud/shared_memory.py', 'brain/workflow.py', 'cloud/mobile.py',
           'cloud/mobile_runtime.py', 'cloud/mobile.html', 'tools/prepare_shared_memory.py', 'test_shared_memory.py',
           'brain/conversation.py', 'brain/memory_prototype.py', 'brain/memory_authority.py',
           'brain/memory_publication_authority.py', 'brain/memory_authority_transfer.py', 'brain/memory_recovery.py',
           'brain/memory_repository.py', 'brain/memory_custody.py', 'brain/memory_recovery_pack.py',
           'brain/memory_recovery_trust.py', 'brain/memory_recovery_latest.py', 'security/policy.py',
           'security/approval.py', 'security/passkeys.py', 'security/vault.py', 'storage/store.py',
           'test_conversation_contract.py', 'test_passkeys.py', 'test_mobile.py', 'test_mobile_voice.py',
           'test_mobile_conversation.py', 'test_brain_workflow.py', str(Path(__file__).relative_to(ROOT)).replace('\\', '/')]
REGRESSIONS = [
    'test_mobile.MobileChecks.test_public_chat_context_is_bounded_ram_only_and_retries_do_not_repeat',
    'test_mobile.MobileChecks.test_stop_before_arrival_and_during_inference_and_no_stale_answer',
    'test_mobile_voice.PhoneChecks.test_bounded_transcription_is_review_only_and_not_stored',
    'test_mobile_conversation.ConversationChecks.test_same_voice_is_bounded_and_private_state_not_exposed',
    'test_brain_workflow.BrainChecks.test_verified_personal_context_never_reaches_cloud_callable',
    'test_brain_workflow.BrainChecks.test_saved_fact_answers_without_model_and_missing_fact_abstains',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--case', help='One exact case ID from the focused selection.')
    args = parser.parse_args()
    if not args.name.replace('-', '').isalnum(): parser.error('Use a simple new evidence name.')
    report = HERE / (args.name + '.json'); log = HERE / (args.name + '.txt')
    if report.exists() or log.exists(): parser.error('Preserve preceding evidence.')
    def hashes():
        return {name: hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in SOURCES}
    before = hashes()
    from test_shared_memory import SharedMemoryChecks
    loader = unittest.defaultTestLoader
    names = [f'test_shared_memory.SharedMemoryChecks.{name}' for name in loader.getTestCaseNames(SharedMemoryChecks)] + REGRESSIONS
    assert len(names) == len(set(names)) == 14
    if args.case:
        if args.case not in names: parser.error('Select one exact reviewed case ID.')
        names = [args.case]
    old = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix='.sm-', dir=ROOT) as home:
        tempfile.tempdir = home
        try:
            with log.open('x', encoding='utf-8') as stream:
                result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                    unittest.TestSuite(loader.loadTestsFromName(name) for name in names))
        finally: tempfile.tempdir = old
    after = hashes(); assert before == after, 'Reviewed sources changed during checks.'
    data = dict(passed=result.wasSuccessful() and not result.skipped and result.testsRun == len(names),
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
        case_ids=names, platform=sys.platform, fake_data_only=True, injected_exact_native_approval=True,
        signed_fake_native_and_phone_sessions=True, sources_match_before_after=True, source_sha256=before,
        live_network_or_provider=False, real_owner_enrollment=False, private_memory_enabled=False,
        remote_deployment=False, real_device_or_laptop_off_acceptance=False)
    with report.open('x', encoding='utf-8') as stream: stream.write(json.dumps(data, indent=2) + '\n')
    print(json.dumps({key: value for key, value in data.items() if key not in ('case_ids', 'source_sha256')}))
    return 0 if data['passed'] else 1


if __name__ == '__main__': raise SystemExit(main())
