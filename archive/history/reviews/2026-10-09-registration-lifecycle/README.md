# Registration lifecycle review and fix — 2026-10-09

What this change does: LYA's new owner registration uses its existing native visual language and standard phone passkey proof. This follow-up checks that leaving setup stops its guidance and pending activity, and that returning owners do not repeat biometric enrollment.

Assumed load: one owner using the native desktop application. Review was limited to registration's callers, voice worker integration, local capture bridge/lease, UI cleanup and stored-profile sign-in. This is not a whole-product security audit, anti-spoof qualification or live owner enrollment.

## Must fix — resolved

1. **Hidden setup could continue guidance before phone verification** (`desktop/owner_setup.py`, `OwnerSetupDialog.hideEvent`).
   - What this is: hiding registration should stop that registration attempt and its spoken guidance.
   - Problem: cleanup was conditional on a phone ceremony or a profile session already existing. Hiding arrival, name or recovery guidance left the dialog open internally, its expiry timer running, and its queued initial speech able to start after the screen disappeared.
   - Fix: call the existing idempotent cleanup for every hide event. This stops registration speech, fades, polling and expiry timers; existing phone/capture cleanup and successful authentication behavior remain intact.
   - If skipped: LYA could speak registration instructions from an invisible setup screen and retain unnecessary pending work. This reproduction did not demonstrate an owner-authentication bypass or any data leak.

The new synthetic regression failed in all three pre-phone stages before the fix, then passed afterward. Existing signed-success, phone cancellation, expiry, minimize/hide, private capture cleanup and encrypted profile persistence checks also pass.

## Additional check

A new synthetic returning-owner journey enrolls a fake phone credential and saves fake face/voice vectors in a temporary encrypted store. A fresh signed assertion then completes native sign-in with the same owner identity and a new session ID. It does not construct a capture worker, stop the ordinary listener or recapture/change stored profiles. This verifies code integration with synthetic credentials, not actual iPhone transport or recognition accuracy.

## Evidence

- `validation.json`: 88 passing tests, zero failures/errors/skips across owner profiles, phone passkeys, approval, compact desktop experience and legacy retirement fixtures.
- `check_lifecycle.py`: reproducible runner forces fake encryption keys and temporary default storage before loading the existing suites.
- Four source syntax/whitespace checks and normal launcher-interpreter registration import passed.
- No real owner store, credentials, biometrics, camera, microphone, speech output, external provider inference, configuration, app restart or deployment was used.
- Source change: `desktop/owner_setup.py`. Regression additions: `test_passkeys.py`, `test_owner_profiles.py`.

Verdict: Ship the narrow cleanup fix for owner acceptance. Real phone/browser transport, voice/sensors, recovery and sustained full-app resource behavior remain unverified. The existing registration walkthrough remains in `review/2026-10-09-integrated-registration/README.md`; no step changed.

No model replacement, new dependency, general interface redesign, hearing/voice change, credential reset, security-policy relaxation or speculative upgrade was added.
