# Owner security recommendation — 2026-10-09

Research and source inspection only. No authentication behavior, enrollment, device setting, protected runtime store, sensor or provider configuration changed.

## Recommendation

Retain the existing phone-passkey authority and exact-operation approval. Keep webcam/voice profiles outside the authentication decision. A stronger recognition model does not establish trusted capture or stop injected recordings. NIST SP 800-63B requires presentation-attack detection for facial authentication and excludes voice comparison from authentication. This project has not demonstrated those biometric security properties.

The phone performs its own local user verification; LYA verifies a fresh signed WebAuthn assertion. This is not a guarantee that Face ID alone was used or that the credential is Apple hardware-bound. Synced passkeys may exist on other authorized devices. Face ID uses depth/infrared capture and protected processing that a normal laptop webcam does not reproduce.

## Work order

1. On a trusted laptop controlled by the owner, live-check the existing phone flow when the owner is ready. Check first registration, returning sign-in, cancellation, expiry and one exact protected action. First registration binds the first verified credential; it does not independently know the human's prior identity. Keep the unregistered laptop under the owner's control.
2. On the iPhone, recommend Stolen Device Protection with the Always setting, Apple Account two-factor authentication and Find My. Apple documents biometric-only use of Keychain passkeys under this protection. This requires a user-controlled phone setting; LYA's generic WebAuthn user-verification flag cannot enforce or attest that setting. Check the actual hybrid flow and selected passkey provider before claiming this protection applies to LYA.
3. Verify passkey-provider recovery separately from encrypted LYA data recovery. Existing project recovery tooling is not a completed live owner restore. Test with synthetic data on an independent staging destination before relying on a backup. Current LYA registration supports one owner credential; do not claim a second hardware credential, owner passkey rotation/revocation UI or lost-phone recovery journey is implemented. No photo/voice-only reset.
4. Before sensitive production use, commission a scoped security review of bootstrap, loopback relying-party/origin design, session lifecycle and recovery. This research is not that audit and demonstrates no exploit. The localhost relying-party identity is not unique to LYA among local programs; malware or a hostile same-user local service remains outside the current boundary.
5. A future hardware security key can reduce dependence on phone/sync recovery and provide a device-bound credential. No purchase is required now. Supporting replacement or multiple credentials requires an explicitly scoped implementation and tests, not merely buying a key.

## Current source evidence and limits

- `security/passkeys.py`: requires user verification and presence through FIDO2 verification, ES256, exact origin/client binding, fresh challenges, second signed assertion before first-owner commit; owner sessions are five minutes.
- `security/approval.py`: exact challenge/action/parameters and live owner session; cancellation or timeout denies approval.
- `security/policy.py`: listed protected operations require phone approval. Camera access currently requires a verified owner session, not separate phone approval for every frame or every camera command.
- `storage/store.py`: refuses owner overwrite; encrypted local templates are separate from the public passkey credential.
- `desktop/owner_setup.py`: profile collection follows separate consent and signed phone proof. Returning sign-in does not perform face/voice authentication. No background continuous biometric identity monitoring is implemented.
- Existing model-only evidence in `review/2026-10-08-owner-face-voice/model-check.json` recorded approximately 441 MiB peak and about eight seconds to load. The worker is bounded and exits; full-app sustained load remains unmeasured. Do not turn enrollment models into continuous authentication by default.
- File encryption/ACLs protect data at rest but cannot make decrypted data safe from malware controlling the same account or host. Windows security and full-disk encryption remain relevant even though LYA sign-in uses phone proof instead of Windows identity verification. No host settings were inspected or changed.

## Primary sources

- NIST biometric limitations and authenticator requirements: https://pages.nist.gov/800-63-4/sp800-63b/authenticators/
- Apple Face ID hardware, Secure Enclave and fallback: https://support.apple.com/en-us/102381
- Apple Stolen Device Protection, Keychain passkeys and Always setting: https://support.apple.com/en-us/120340
- FIDO passkeys, sync and device-bound credentials: https://fidoalliance.org/passkeys/
- Microsoft full-disk encryption scope: https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/index
- W3C WebAuthn protocol: https://www.w3.org/TR/webauthn-3/

Agent Reach web workflow used. The installed skill was read; Agent Reach CLI and mcporter were unavailable and the Jina fetch could not resolve its host. Official pages were retrieved with the available web tool. CLI update check was unavailable. No social-media claims used.

Next recommended task: live acceptance of the existing owner proof, followed by a separately scoped owner credential-loss/recovery design and synthetic restore check. Owner previously deferred enrollment; this research does not resume collection.
