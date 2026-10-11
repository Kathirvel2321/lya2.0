# Voice-led particle registration — 2026-10-08

Implemented presentation for LYA's owner registration/sign-in and exact-action walkthrough. The owner rejected glossy crystal artwork, requested a plain screen without routine text, then clarified that many coloured dots should form expressive shapes like LYA's speaking animation. This supersedes the single-dot intermediate version.

The native screen renders 144 small antialiased dots without a diamond, bitmap, video, shader, model download or new dependency. Three muted cyan/violet/mint strands form speaking waves; listening/hearing use rounded rings, transcription uses crossing paths, and phone waiting uses a warm ring palette. These indicate actual interaction state via existing speech/listener events; movement is not audio-amplitude measurement or biometric progress. Reduced motion is static and hidden/closed timers stop. Animation updates are bounded to 12.5 frames/s. The existing ordinary LYA interface, hearing, voice, startup, API keys and camera controls are preserved.

Routine guidance is spoken, including a one-time reminder to verify the newly created passkey before committing a profile. Native buttons show only repeat/continue/cancel symbols, with keyboard focus and screen-reader names; hidden state labels do not render. Dialog descriptions expose guidance to assistive technology. The plain browser bridge retains the phone symbol, accessible status and standard browser/phone verification prompt. Protected action details are shown there before a separate explicit click opens the authenticator; private parameters are not narrated into the existing cloud listener. No authenticator call is triggered from page load. The old artwork-serving endpoint was removed.

## Preview

Actual offscreen native captures using synthetic state only:

- [Speaking waves](walkthrough-speaking.png)
- [Listening rings](walkthrough-name.png)
- [Thinking paths](walkthrough-thinking.png)
- [Arrival](walkthrough-arrival.png), [recovery](walkthrough-recovery.png), [phone waiting](walkthrough-phone.png)
- [Static browser preview](phone-preview.html); does not enroll an owner.

## Checks and limits

[validation.json](validation.json): 66 isolated checks passed across test_passkeys, test_approval and desktop.check_experience. Tests cover signed synthetic WebAuthn enrollment/confirmation/approval, HTTP boundaries, cancellation/expiry/revocation, native worker handoff, existing camera authorization without capture, voice name read-back, no visible native labels/forms, icon accessibility, distinct state rendering, minimum-size controls, reduced motion and hidden cleanup. New-passkey confirmation guidance is spoken only once and cannot save the profile before signed verification. Browser JavaScript syntax, four Python compilations and scoped whitespace passed; native captures visually reviewed.

A short synthetic widget-only process CPU sample measured 2.305% of one core. This is not a full-app, sustained battery or speech-latency measurement. No real owner data, keys, microphone, camera, provider inference, actual browser ceremony, real enrollment or application restart was used. The initial sandbox test could not reopen app-protected temporary files; the fake-key/temp-store check passed with normal host file permissions. No store-security behavior was changed to make tests pass.

Run `.venv-ui/Scripts/python.exe review/2026-10-08-voice-particle-registration/check_walkthrough.py` for synthetic reproduction. The helper protects default storage and uses fake encryption before loading suites.

Older glossy artwork and single-dot intermediate captures remain as dated review evidence in the adjacent registration-artwork and voice-only-registration folders; the PNG is not loaded by the current runtime. Actual iPhone/browser transport, owner speech acceptance, existing-owner trusted migration/recovery and full-app resource qualification remain pending. Reopen the existing launcher and say register admin to load the presentation; legacy profiles remain locked and must not be reset to bypass owner proof.
