"""Record safe aggregate development evidence; preserve legacy brain bytes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
MARKER = b'Voice-guided phone-passkey owner access (2026-10-08):'


def main():
    validation_path = OUT / 'validation.json'
    result = json.loads(validation_path.read_text(encoding='utf-8'))
    assert result['successful'] and result['tests'] == 181 and not result['live_enrollment']
    result.update(final_focused_tests=21, final_focused_failures=0, final_focused_errors=0,
                  diagram_syntax=True, compiled_files=8, scoped_whitespace=True,
                  visual_review=True,
                  final_changes='After the full regression run: non-ASCII capability rejection, plain-text title, and long-action/minimize checks passed the final focused suite.')
    validation_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    summary = (
        'Voice-guided phone-passkey owner access (2026-10-08): owner explicitly selected LYA voice-guided setup with iPhone passkey instead of Windows identity verification. '
        'Added native consent/name/read-back/recovery guidance and returning-owner dialog without text-entry forms; accepted local speech and ordinary hearing routes reused. '
        'Temporary loopback-only browser bridge with exact Host/Origin/capability, CSP/no-store/bounded JSON/socket limits; maintained fido2==2.2.1 verifier requires ES256, UV/UP, fresh origin/RP/challenge/signature and credential/user/counter/backup binding. '
        'New credential needs a second signed assertion before atomic first-owner/public-credential commit to existing encrypted identity store; phone private key never retained. '
        'Five-minute identified session and worker-to-Qt exact-operation approval connected to existing ApprovalGate; cancelled/invalidated/hidden/minimized/expired/revoked requests deny, browser cancellation prompt. '
        'Legacy, ambiguous or unavailable owner records remain locked for separate trusted migration; no owner profile/key/private memory inspected, altered or enrolled in development. '
        'No camera/microphone collection, laptop biometric model/template, provider key/ASR/voice/ordinary crystal/camera/startup/default change or remote deployment; DPAPI encryption protection retained separately from identity prompts. '
        '181 isolated fake-key/temp-store regressions passed; final21 focused crypto/native checks passed after last token/plain-label/long-action changes. Eight-file compilation, scoped whitespace, browser JavaScript and one Mermaid diagram syntax checks passed; actual native synthetic captures visually reviewed. '
        'Short synthetic active-widget process CPU sample2.703% of one core, not sustained full-app pressure/latency. '
        'Research via Agent Reach public-web/Jina and primary Apple/NIST/W3C/Yubico docs; CLI unavailable. '
        'Artifacts: review/2026-10-08-owner-passkeys/README.md, validation.json, approval-flow.mmd, five owner-*.png captures, phone-page-preview.html, check_owner_setup.py and record_continuity.py. '
        'Source: security/passkeys.py, desktop/owner_setup.py, scoped desktop/experience.py, security/approval.py, storage/store.py/requirements/docs/test route additions and test_passkeys.py. '
        'Implemented and synthetic native integration tested; actual iPhone/browser hybrid QR enrollment, owner speech, migration, recovery and full-app resource acceptance remain unverified. '
        'Passkey UV may use device passcode/Touch ID/Face ID and anonymous attestation does not certify Apple hardware; webcam is not claimed as Face ID. '
        'Next: reopen LYA and inspect register admin; locked existing owners need an explicitly approved independently trusted migration, never deletion/reset of the protected store/key. Empty-store phone create/confirm/sign-in followed by synthetic exact-action/cancel owner acceptance pending.'
    )
    brain = ROOT / 'lya-project-brain.md'
    original = brain.read_bytes()
    if MARKER in original:
        raise RuntimeError('Continuity entry already recorded; do not duplicate it.')
    first_newline = original.index(b'\n') + 1
    status = (summary + '\r\n').encode('utf-8')
    ledger = ('\r\n\r\n### 2026-10-08 — Voice-guided owner passkeys\r\n\r\n' + summary + '\r\n').encode('utf-8')
    brain.write_bytes(original[:first_newline] + status + original[first_newline:] + ledger)
    print('Safe aggregate status and ledger recorded; historical bytes preserved.')


if __name__ == '__main__':
    main()
