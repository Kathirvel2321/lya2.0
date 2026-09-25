# LYA initialization / admin registration — 2026-09-25

Owner request: register as admin, verify the connection chain, and replace the
"boring and simple" owner walk-through with a voice-led, futuristic one that
greets, teaches and scans.

## What was built

`desktop/activation.py` — a six-act initialization run-through, launched with
`activate-lya.cmd`.

| Act | What actually happens |
|---|---|
| BOOT | Eleven subsystems are probed for real and revealed one line at a time, with a status LED each. Skippable; reduced motion jumps to the end. |
| IDENTITY | Salutation (default **boss**) plus display name. LYA says the greeting through the reviewed Piper path. |
| OPTICS | The owner's camera opens **only on request**. YuNet detects a face; three samples are captured through the real prompts (look at lens / turn left / turn right). Frames stay in RAM. |
| VOCAL | The microphone opens **only on request**. A fresh six-digit code is displayed, three clips are recorded, and the real duration/RMS/peak/clipping plus a voiceprint-stability verdict are reported. |
| VAULT | Windows Hello proof through `security\HelloVerifier.exe`, explicit consent, then one encrypted person-scoped profile row. |
| ONLINE | LYA addresses the owner by the chosen salutation and states what is live and what is still locked. |

Visual language: dark gradient, grid, scanlines, a rotating iris and radar
sweep around the crystal core, a left act rail with per-act state, a right
subsystem ledger with real ONLINE/LOCKED LEDs, a live camera viewport with real
face boxes, and a live microphone waveform. The animation timer **stops** when
the window is idle, hidden, or in reduced motion.

## What it deliberately does not do

- It does not claim a biometric identity. The optics act checks face *presence*
  and says so on screen (`NOT AN IDENTITY MATCH`).
- It does not write a biometric template while the contract is incomplete.
  `biometric_readiness()` requires optics, camera, mic, speech recognition, face
  embedding and anti-spoofing before enrolment is treated as possible.
- It never writes a frame or a clip to disk, and never sends anything to a
  network.
- It does not invent telemetry: every number on screen is measured.

## Real connection report on this machine (2026-09-25)

```
ONLINE  NEURAL CORE            brain + encrypted store importable
ONLINE  ENCRYPTION VAULT       DPAPI-protected key present
ONLINE  SECURE STORE           %LOCALAPPDATA%\LYA - person-scoped SQLite
ONLINE  OPTIC ARRAY            YuNet + NanoDet present and hash-verified
ONLINE  CAMERA RUNTIME         OpenCV available
ONLINE  MICROPHONE             sounddevice available
ONLINE  VOICE OUTPUT           native English + Tamil Piper voices
LOCKED  SPEECH RECOGNITION     no transcription engine - a spoken code cannot be verified
LOCKED  FACE EMBEDDING         insightface missing - no face template can be built
LOCKED  ANTI-SPOOF LAYER       torch / Silent-Face-Anti-Spoofing missing
ONLINE  WINDOWS CHECKPOINT     HelloVerifier.exe present

BIOMETRIC ENROLMENT: locked - missing SPEECH RECOGNITION, FACE EMBEDDING, ANTI-SPOOF LAYER
```

## Checks

`test_activation.py`: 18 passed.

- probe layers are real and open no sensor;
- readiness mirrors the actual missing layers;
- anti-spoof is reported missing rather than faked;
- WAV measurements are real, and silence is reported as unusable;
- the HUD paints offscreen in all six acts;
- reduced motion leaves the animation timer stopped;
- three face samples are captured from injected frames;
- a six-digit code is generated and real clip measurements are reported;
- the vault refuses without a fresh Windows proof, without consent, and with an
  expired proof, and writes nothing in any of those cases;
- exactly one admin is created in a temporary encrypted store, and a second
  attempt is refused;
- the default camera and microphone objects open nothing on construction.

Two real defects were found and fixed while writing these checks: an
out-of-range index in the face-prompt sequence, and a QPainter/QImage lifetime
error in the paint test. The gate suites were re-run afterwards.

## What is still blocked, and what it needs

Admin registration itself works today through the **Windows-device-only** path
(`register_device_admin`), which is the sanctioned fallback: verified identity,
no biometric template, audit outcome recorded as such. To unlock true biometric
enrolment and phone approval, three things must be installed, in this order:

```powershell
.\.venv-ui\Scripts\python.exe -m pip install insightface
.\.venv-ui\Scripts\python.exe -m pip install torch
git clone https://github.com/minivision-ai/Silent-Face-Anti-Spoofing security\Silent-Face-Anti-Spoofing
# plus its resources/anti_spoof_models/ weights, and a transcription engine
.\.venv-ui\Scripts\python.exe -m pip install SpeechRecognition
```

Nothing above was installed by this task. Those are large downloads and a real
environment change, so they are left for the owner to approve explicitly.

## Limits

- Offscreen Qt and injected sensors only: no real camera, microphone, Windows
  prompt or on-screen visual approval was performed.
- The face and voice acts were exercised with fakes, so real-device framing,
  lighting and microphone behaviour are unmeasured.
- Enrollment was not performed: it needs the owner physically present, the
  Windows Hello prompt, and a human decision about the biometric stack.
