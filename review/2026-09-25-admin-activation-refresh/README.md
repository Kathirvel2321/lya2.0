# Admin activation refresh — 2026-09-25

The owner's `register admin` command now opens the six-act activation dialog
for first registration. Existing admin records still use `RegistrationDialog`
for sign-in. The activation emits the normal verified session after a successful
local profile write, so LYA can bind it without a second login.

The visual pass replaces dense grid and scanlines with a dark staged surface,
larger crystal, contextual connection list, concise guidance, and a camera
viewport in the hero position. Existing local speech now supplies live captions
and conversational step copy. The camera and microphone start only from their
respective buttons, stop when their act ends, and the preview is capped near
16 fps. Captured clips are measured then discarded; the dialog retains only
non-biometric audio measurements. The Windows proof is bound to the exact name
that was verified; editing that name invalidates the proof. Cancel kills any
pending helper process and grants no access. `activate-lya.cmd` now has a
working `sys` import and keeps the dialog alive through its event loop.

Connection badges say FOUND / NOT CONNECTED because installed code does not
prove a live device works. Face presence and microphone measurements remain
calibration only. This flow has no connected transcription, face embedding,
anti-spoofing, or biometric sign-in. It never claims that these are enrolled.
Admin creation still depends on an actual Windows verification and explicit
consent, writing only the device-only profile to the encrypted local store.
No enrollment or owner profile was performed in this task.

## Checks

- 64 focused offscreen tests passed: activation, earlier registration, and
  desktop handoff. Sensors and Windows proof in these tests are injected fakes;
  the store is temporary with a fake encryption key.
- Python syntax compilation passed for the changed desktop modules.
- Synthetic identity and optics previews were rendered with fake layers and
  frames: `identity-synthetic.png` and `optics-synthetic.png`. The sample owner
  name and fake face box are not a real person.
- Live, read-only device check in this session: OpenCV could not open camera
  index 0 through default/DirectShow/Media Foundation, nor indices 0–2 through
  DirectShow. Sounddevice listed the Realtek microphone, but short capture failed
  through MME, DirectSound, WASAPI, and WDM-KS. No image or audio was saved.
- `HelloVerifier.exe check` was blocked before execution by Windows Application
  Control. The file's presence is not evidence that verification works.

These initial device failures did not prove that the physical devices were
broken; the normal-session follow-up below resolves that uncertainty. A trusted
Windows verifier path accepted by Application Control is still required. Until
that proof succeeds, the registration gate stays closed. Phone approval and
biometric identity are separate future work.

## Follow-up: normal Windows session

The owner confirmed the Windows Camera and Sound Recorder apps work. A new
unsandboxed, no-save probe confirmed the exact LYA camera worker opened the
camera and received a frame. The LYA microphone worker recorded a short clip;
its low RMS reflects the quiet test, not a device-open failure. The local
`SetupSpeech` worker completed a short offline greeting without reporting
unavailability. These checks prove device access and speech-worker completion,
not face recognition accuracy, transcript verification, or subjective voice
quality. No frame, clip or transcript was saved.

`HelloVerifier.exe check` was retried unsandboxed and was still blocked by
Windows Application Control. `QProcess` reports the same policy block, which
the activation UI recognizes and keeps fail-closed. The helper is unsigned.
The earlier camera/microphone failures were specific to the restricted tool
session; the remaining registration blocker is the Windows verifier. No real
admin profile was created by these checks.

## Smart App Control approval finding

A later read-only Code Integrity event check identified Smart App Control's
enforced policy as the blocker for the unsigned helper. This is not a missing
LYA permission or a Windows Hello PIN prompt. Microsoft currently provides no
per-app approval for Smart App Control. The safe development path is a trusted
signed helper or a reviewed in-process implementation of the desktop Windows
consent API, not asking the owner to turn off protection for every app. No
security setting was changed. Microsoft references:
`https://learn.microsoft.com/en-us/windows/apps/develop/smart-app-control/test-your-app-with-smart-app-control`
and `https://support.microsoft.com/en-us/windows/security/threat-malware-protection/smart-app-control-frequently-asked-questions`.
