# NVIDIA hearing connection — 2026-10-05

Update: after the failed fresh offline comparison, owner authorized ongoing online
hearing and model backups. Normal launch/sign-in now choose online mode; private
questions use text. See [online-backups.md](online-backups.md), which supersedes the
earlier pending permission and no-fallback policy below.

The owner reported the fresh NVIDIA speech-to-text check was exactly accurate and
provided a screenshot showing the diagnostic completed and displayed recognized
words. **That ordinary question's hearing gate passed by owner confirmation.**
The exact transcript and screenshot are not copied into project artifacts.
This is not a noisy-room, long-question, interruption or full LYA reply test.
No microphone fault or pronunciation defect is established.

## Implemented connection

- `audio/voice.py`: optional explicit NVIDIA command route. Local wake/standby and
  stop reader retained. Complete questions use the existing capture/VAD, allowing
  three seconds of pause for the NVIDIA route, matching the accepted diagnostic;
  the 120-second bound rejects clipped turns. Reader cancellation reaches NVIDIA.
  Provider failure never substitutes Groq or a local guess.
- `desktop/app.py`: `--cloud-asr nvidia` selects the provider, but still requires
  `--cloud-voice`. Default launches remain local. The listener checks current
  `brain.private_mode` after capture before choosing a remote route; private mode
  uses local recognition. The status names the selected provider. No answer voice,
  command authorization, profile, model or enrollment changes.
- `tools/start_nvidia_lya.py`: session launcher for the separate `.venv-asr`
  environment. Explicit `--allow-nvidia-questions` and hidden local key input;
  key retained only in this process's environment, never a file or command line.
  The ignored pilot environment reuses existing desktop libraries, including
  their Windows path setup, for both the desktop and its child tools. Main
  environment dependencies are unchanged. Existing single-instance lock retained.

Turn private mode on **before** confidential speech, using the text composer.
A spoken privacy request itself is transcribed under the previous mode. Once
audio has left the device it cannot be recalled. This gate does not detect private
content before recognition. Private local recognition remains less accurate and
must not be described as owner-accepted. Correct transcription grants no identity
or authority; existing protected-action gates remain necessary.

## Validation and limits

Speech/integration suite: 59 passed, one existing designed online skip. New checks
cover provider selection/no fallback, cancellation, local-only behavior, privacy
changes during capture, local wake followed by a complete NVIDIA question.
Offscreen desktop checks include provider status, dynamic private-mode policy and
selection without cloud permission. All 57 offscreen desktop checks passed in the
separate NVIDIA environment after the dependency bridge fix.

The first separate-environment desktop test found missing Windows package path
setup; loading existing site-package setup fixed that. A child demo then exposed
that children lacked the parent's library path. The ignored environment bridge
was added so child tools inherit the same dependency setup. These were dependency
failures, not new hearing evidence. Tests use synthetic temporary stores/fake
secrets; microphone, speech playback and network model calls are disabled.

Launcher help passed. NVIDIA key from the successful diagnostic was not recovered
or saved. No new live audio request or desktop restart was performed while building
this connection. The previous permission covered **one diagnostic question**;
using NVIDIA for ongoing ordinary LYA questions awaits explicit session permission.
The integrated wake -> question -> accepted voice reply remains untested.

After activation is authorized, close existing LYA normally and launch:

```powershell
.\.venv-asr\Scripts\python.exe tools/start_nvidia_lya.py --allow-nvidia-questions
```

Enter the key only in the local hidden prompt. Say LYA or clap twice, then ask one
ordinary question. Check LYA's displayed `You asked` words and spoken reply before
testing a longer question and interruptions. Do not enable enrollment or advance
weather/device actions to compensate for a failed gate. NVIDIA development access
remains subject to account/model rate limits; no paid fallback is implemented.
