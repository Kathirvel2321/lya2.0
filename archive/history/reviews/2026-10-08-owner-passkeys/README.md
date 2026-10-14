# LYA voice-guided owner access — 2026-10-08

The owner selected voice-guided LYA setup with an iPhone passkey instead of a Windows identity prompt. This implementation replaces the native `register admin` / `sign in` entry screen with a scoped owner-access dialog and connects returning passkey owners to the existing exact-operation approval gate. Existing voice, hearing, provider keys, camera detection, ordinary crystal/interface and startup defaults are preserved.

## What is implemented

Say **register admin** or **sign in**, or select the existing tray menu item. Setup speaks through the accepted local Piper/Amy path and receives ordinary spoken answers through the accepted listener. There are no text-entry fields. Buttons provide an accessible fallback and explicit consent; they grant no identity proof.

For a new, empty identity store: consent to ordinary setup speech, say `my name is …` (or `use Owner`), confirm the spoken read-back name, acknowledge the separate phone/data recovery requirements, then continue with the phone. The browser creates a passkey and requests a second signed verification before the owner profile is committed. The ordinary spoken display name is a label, never an authentication factor. Existing online hearing may receive those ordinary words; no face/voice biometric or recovery secret is requested.

For a returning passkey owner: the enrolled credential verifies a new five-minute session. Camera access reuses its existing active-owner/expiry checks. Every existing owner-tier request still requires a fresh assertion for the exact pending action and parameters. The operation is shown in the laptop browser for explicit review before signing; it is not narrated into the active cloud listener. A voice approval or a Boolean callback alone cannot grant access.

The browser is a temporary authenticator bridge, not a new dashboard. Choose a phone/tablet or “Use another device” in a compatible browser, scan its QR with the iPhone and keep the devices nearby with Bluetooth available. The private credential key stays with the authenticator/password manager. LYA stores only the public credential, user handle, counter and backup eligibility inside the existing encrypted SQLite identity file. The existing DPAPI encryption-key protection remains; it is distinct from a Windows verification prompt.

## Research and decisions

| Question | Evidence and resulting choice |
|---|---|
| Can this ordinary webcam reproduce iPhone Face ID? | No qualified secure depth/IR chain was identified. Apple documents TrueDepth depth and infrared capture, so a webcam animation must not be presented as equivalent identity proof. [Apple Face ID](https://support.apple.com/en-us/102381) |
| Should a laptop face/voice sample be the owner authenticator? | Avoid this unqualified path. NIST treats biometrics as part of a physical-authenticator flow, requires face presentation-attack detection, and excludes voice biometric comparison in its authentication guidance. This is design guidance, not a claim of NIST certification. [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) |
| Why use the iPhone passkey? | Apple supports passkey use across devices and retains private key material within the credential ecosystem. LYA requests user verification, which can be Face ID, Touch ID or a device passcode; it does not prove Face ID specifically or enforce Apple-only hardware. [Apple passkeys](https://developer.apple.com/passkeys/), [supporting passkeys](https://developer.apple.com/documentation/authenticationservices/supporting-passkeys) |
| What must the verifier check? | Challenge, exact origin, relying-party ID, user presence/verification and signature, plus credential/user binding, expiry and replay consumption. [WebAuthn specification](https://www.w3.org/TR/webauthn-3/) |
| Which library and transport? | Pin maintained `fido2==2.2.1` in the UI requirements; cryptography was already installed. Use its `Fido2Server` and a standard-library loopback HTTP server. Yubico's localhost example supports the development origin approach; its demo defaults/in-memory credentials were not copied as production policy. [python-fido2](https://github.com/Yubico/python-fido2), [official server example](https://github.com/Yubico/python-fido2/blob/main/examples/server/server/server.py) |

Research used the Agent Reach public-web/Jina route plus official primary sources. Its CLI/backends were unavailable in this environment; no platform login/cookies were used or installed. Installed Yubico package includes its BSD redistribution notice. The public research requests contained no owner identity, audio, image, key or project private corpus.

## Security boundaries

- The bridge binds **127.0.0.1 only**, on an ephemeral port, with a `localhost` RP ID and that ceremony's exact origin. No LAN/public/Oracle server or firewall opening is created.
- A random capability travels in the browser URL fragment, is removed from history after loading, and is required as a request header. Exact Host and Origin checks, JSON/content limits, two-second socket timeouts, no CORS grant, no-store/referrer/CSP/frame policies and disabled request logs bound the local interface. Header-only GET cannot mutate identity.
- Enrollment and sign-in require UV and UP and use ES256 only. New credential data must match the returned ID and offered algorithm; cross-origin requests are rejected. Enrollment is not saved until a fresh possession assertion. Backup flags must be consistent; nonzero counters must advance, while normal zero-counter synced passkeys rely on fresh single-use challenges.
- Registration cannot overwrite an existing active administrator. Legacy profiles without passkeys, ambiguous owners and unreadable protected stores remain locked. No legacy profile, face/voice template, key or private memory was inspected, migrated or deleted during development.
- Approval assertions are bound to the pending nonce, action, parameters and session. Cancellation, invalidation, changed session, expiry or revoked/changed owner records deny access. The native UI closes invalidated requests rather than leaving a stale approval screen. Hidden/minimized/cancelled setup stops its ceremony; browser cancellation informs LYA promptly.
- Only public credential material is retained. No laptop camera/microphone capture, laptop biometric model or private credential key is added by the ceremony. There is no voiceprint or “secret phrase” shortcut, blanket Windows administrator grant, OS policy bypass or unbounded action permission.

First enrollment is trust-on-first-use on the owner's physically controlled, uncompromised laptop. Ordinary `localhost` credentials and this application cannot defend against malware already running as the same unlocked Windows user. Attestation is deliberately `none`: no Apple hardware/Face ID certification is claimed. Browser/phone passkey prompts are required; setup cannot be entirely hands-free because the owner must operate their phone and browser authenticator controls.

## Native screen design

The owner later requested a plain, voice-led registration surface with no diamond, glossy artwork or routine visible text, then specified many coloured dots forming expressive shapes. The current screen uses native particles driven by speaking/listening/thinking state, with accessible repeat/continue/cancel symbols. Exact protected actions remain scrollable in the browser before signing. Particle motion indicates interaction state, not biometric progress or measured audio amplitude. Timers stop when hidden/closed; reduced motion stays static. Other accepted screens and animations are unchanged. [Current report and previews](../2026-10-08-voice-particle-registration/README.md).

Historical offscreen Qt captures: [arrival](owner-arrive.png), [name](owner-name.png), [recovery](owner-recovery.png), [one exact action](owner-one-action.png), [legacy lock](owner-legacy-locked.png). They contain synthetic material only and show the earlier presentation. [Browser-page preview](phone-page-preview.html) is also historical; it cannot enroll an owner by itself.

## Validation and acceptance

Run `.venv-ui/Scripts/python.exe review/2026-10-08-owner-passkeys/check_owner_setup.py`. This forces fake encryption keys and temporary default storage before loading existing tests. [validation.json](validation.json) records the final run, covered modules, synthetic native-screen CPU sample and live limitations. The small runnable security journey is [test_passkeys.py](../../test_passkeys.py).

Checks cover real synthetic EC signatures, enrollment/confirmation/sign-in, wrong signature/origin/RP/challenge/UV/UP/handle, expiry/replay/cancel, encrypted public storage, legacy/duplicate owner protection, revocation and counters, loopback HTTP boundaries, voice name confirmation and no form fields, native session handoff, worker-to-Qt approval, actual protected memory save and invalidated read, and the existing camera authorization guard without opening a camera. Existing storage, memory/project/archive, legacy registration, brain, approval and recovery UI regressions are also run in isolation.

Not yet live-verified: actual iPhone/browser QR transport, successful phone enrollment or existing-owner migration, real owner speech within the new wizard, sustained full-app resources, and phone loss/recovery. The UI explains phone credential recovery separately from LYA encrypted-data backup; no reset bypass or automatic backup export was added. Owner registration data is not created during development.

Next: reopen the existing LYA launcher and say `register admin`. If it shows an existing-owner lock, stop there and choose a separate, explicit trusted migration plan. Do not delete the current encrypted identity store or key to get past the lock. On an empty store, accept the ready check and perform create → confirm → sign in with the phone, then one synthetic private save/recall and cancellation. No live acceptance is inferred from synthetic checks.

Source wiring: [security/passkeys.py](../../security/passkeys.py), [desktop/owner_setup.py](../../desktop/owner_setup.py), [desktop/experience.py](../../desktop/experience.py), [storage/store.py](../../storage/store.py), [security/approval.py](../../security/approval.py), [desktop/requirements.txt](../../desktop/requirements.txt), [approval-flow.mmd](approval-flow.mmd).
