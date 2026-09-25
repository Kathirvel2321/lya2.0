# T04 primary-admin registration foundation

Status: **isolated-tested; real device integration pending**.

## Implemented

- Fail-closed registration coordinator with explicit local-biometric consent.
- Exact, expiring trusted-device bootstrap challenge. A boolean success value is rejected.
- Three randomized active face challenges and three fresh spoken-code challenges.
- Finite, normalized, dimension-stable embeddings and pairwise consistency checks.
- Atomic creation of one primary admin, three encrypted face templates, three encrypted
  voice templates, a recovery-code hash and a privacy-safe audit event.
- Five-minute admin session and a concise personalized greeting after registration.
- Legacy enrollment that uploaded raw face and voice media to Supabase is disabled.

## Verification

`check-t04.cmd` passes the full offline chain, including seven registration tests.
Tests use synthetic vectors, fake captures, fake liveness and a temporary DPAPI key/store.
They do not access the camera, microphone, cloud, live identity store or real biometrics.

## Security boundary

Recognition can select a profile and greeting. It does not approve private or dangerous
operations. Those remain protected by an exact fresh approval challenge and session
recheck. Registration refuses to run without a trusted-device verifier.

## Pending before real enrollment

- Connect the native desktop window to the Windows Hello desktop interop API.
- Add visible camera/microphone capture with cancel, timeout and device-release behavior.
- Validate active liveness and tune thresholds on the actual camera/microphone.
- Add verified removal, recovery and key-loss instructions.

Microsoft documents Windows Hello as device-bound authentication with biometric or PIN
user verification. For native desktop applications, Microsoft directs apps to the
window-bound `UserConsentVerifierInterop.RequestVerificationForWindowAsync` API. LYA
will use that platform proof instead of treating its own camera classifier as authority.
