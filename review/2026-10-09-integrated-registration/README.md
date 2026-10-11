# LYA registration — integrated native presentation

Implemented and isolated-tested on 2026-10-09. This builds on LYA's existing standard FIDO2/WebAuthn owner proof. It does not create a new iPhone application, invent cryptography, enroll the owner during development or claim live phone acceptance.

## What changed

- Registration uses the existing conversation panel's blue-black surface, cyan edge and muted amber corner accent. It has no diamond, bitmap artwork, blur, model, routine visible label or new dependency.
- The 144-dot sculpture now forms a sphere for arrival/listening, responsive deformation for hearing, three spoken waves, crossing purple thought paths and amber phone orbits. Existing actual voice states drive the drawing; decorative wave movement is not a measured audio waveform. Microphone profile mode still uses its existing actual input meter.
- Six small checkpoints show walkthrough stages, not authentication strength, estimated scan progress or biometric accuracy. A phone shape appears during phone verification. Local camera preview uses corner markers and scales within the small registration layout.
- Controls use quiet icon buttons, a single matte primary button, keyboard focus rings and existing accessible names. Voice guidance and its consent/name confirmation remain the same. The top strip supports native window dragging.
- The panel opens beside the existing orb within its monitor; first-run setup with a hidden orb is centred. It remains a native LYA surface. Browser/phone prompts required for passkey proof still appear separately and are not replaced by a simulated LYA prompt.
- The shared phone bridge has matching colours, shape and dotted phone orbits. Essential exact-operation text remains visible and scrollable before protected-action approval. JavaScript verification/transport and all server validation are unchanged. Native approval controls and window dimensions are preserved; their shared dot widget also uses the refreshed dot artwork.
- Spoken consent now says LYA never receives the private passkey, avoiding the inaccurate implication that a synced passkey can exist only on one phone.

## Registration walkthrough

1. Keep your iPhone nearby. Turn Bluetooth on for the laptop and phone. Use a current Chrome or Edge browser. Perform first registration on a trusted laptop under your control; LYA binds the first successfully verified owner credential.
2. Fully **Quit** LYA from its tray menu. Reopen your usual `launch-lya.cmd` launcher. Launching a second instance alone does not reload the existing running app.
3. Wake LYA if it is in standby, then say **register admin**. Ordinary setup words use the existing online hearing route. No enrollment camera or microphone opens merely from this command.
4. Listen to LYA and say **I agree**. At the name prompt say **my name is [your name]**, then **yes, that is my name** after the read-back. Say **try again** to correct it, or **use Owner** to use the default name.
5. Listen to the recovery reminder, then say **I understand**. This is guidance, not creation or verification of an independent backup. Passkey-provider recovery and encrypted LYA data recovery remain separate.
6. In the local browser, select the phone icon. Choose **Use another device** or **Phone/tablet** in the browser's trusted prompt. Scan its QR using your iPhone and approve on the phone. Names of browser options may vary. LYA cannot supply this approval or bypass the phone's verification prompt.
7. For a new credential, select the phone icon once more and verify the new passkey. LYA saves the owner credential only after that second signed assertion. If a credential already exists, LYA asks for sign-in instead of replacing it.
8. When LYA asks separately about local face/voice profiles, say **I agree** to collect them. It stops the ordinary online listener before starting local capture. Follow three face poses, then three spoken samples. The camera and profile microphone are not used continuously for sign-in. During this private phase, spoken commands are paused: use **Escape** or the close icon to cancel.
9. At the final spoken review, say **save my profiles**. Consistent vectors are encrypted locally; raw photos/recordings are not saved. The ordinary listener resumes after the capture worker exits. Successful owner access lasts five minutes; protected operations still need fresh approval of the exact request.

The repeat arrow repeats the current guidance; the central icon continues the current step; the close icon cancels. Before private capture, say **cancel** to exit. If cancelled after phone proof, the phone credential remains registered and missing profiles resume after a later signed sign-in. Do not clear the store or re-register to work around an error. If the profile step reports failure, keep its error wording for diagnosis.

For later access, say **sign in** or **unlock LYA**, then **continue with phone**. Once profiles are saved, returning sign-in does not recapture face/voice. A copied face/voice never unlocks the owner session.

## Validation and evidence

Run `.venv-ui/Scripts/python.exe review/2026-10-09-integrated-registration/check_registration.py`. The runner installs fake encryption keys and temporary default storage before loading older suites. It performs no real sensor, runtime-owner-store, external provider inference or actual owner enrollment operation.

`validation.json` records 86 passes, no failures/errors/skips, browser JavaScript syntax validation and a three-second native-widget CPU sample. Tests cover real synthetic signatures, native dispatch, required consent, cancellation/hiding/expiry, encrypted atomic profile save, exact protected-action approval, prior regression paths and the new screen-bounded placement/layout at 320x280, 460x390 and 600x500. Native screenshots were visually inspected: `registration-ready.png`, `registration-listening.png`, `registration-hearing.png`, `registration-speaking.png`, `registration-thinking.png`, `registration-phone.png`, `registration-small.png`.

The first sandboxed run failed because Windows restricted temporary-file ACLs; rerunning these isolated fixtures with normal host permissions passed without weakening product security. `phone-preview.html` is a synthetic static artifact; automated browser visual inspection was blocked by the browser's local-file URL policy, and no alternate route was attempted. Browser JavaScript syntax and existing HTTP/crypto tests passed; actual browser visual/phone acceptance remains unverified.

No dependency, hearing/voice model, microphone selection, general interface, launch default, camera policy, encryption, owner authority or credential changed. No real app restart, data collection, credential creation or deployment was performed.

## Remaining limits

Real owner speech, iPhone QR transport, sensor capture and full-app resource impact need owner acceptance. Face/voice spoof resistance is unqualified and the profiles grant no authority. WebAuthn user verification does not prove FaceID-only use. One owner credential remains supported; lost-credential rotation/revocation UI, multiple credentials and a live independent restore are not implemented by this presentation task. Malware controlling the host or an authorized passkey device remains outside this protection. Existing owner-security research is in `review/2026-10-09-owner-security-solution/README.md`.
