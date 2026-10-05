# Online hearing with model backups — 2026-10-05

Owner outcome update: Whisper fresh test was understandable and better than past
local candidates, but less precise than the accepted Parakeet result. Treat it as
a qualified backup, not equal accuracy or universal acceptance. Parakeet stays the
default. Integrated LYA question/reply and long/noisy/stop tests remain pending.

Owner confirmed both fresh local candidates were wrong and supplied the comparison
screenshot. **Fresh local hearing acceptance failed.** Exact words/screenshots are
not copied into project artifacts. The owner chose online recognition and asked
for model backups, superseding the earlier pending ongoing-cloud decision.
The accepted evidence remains one ordinary NVIDIA Parakeet question; other models,
full assistant replies, long/noisy speech and interruptions are not yet accepted.

## Research and plan before implementation

The official Vosk model page distinguishes small lightweight models from large
models intended for higher-accuracy server transcription. The tiny Whistle card
describes CPU use and a 30-second pass limit. Our comparisons establish inadequate
recognition by these installed candidates for this owner. Capacity/training/input
mismatch is a plausible explanation; the exact acoustic cause is not established.
Offline location alone does not cause inaccuracy. Do not blame pronunciation,
declare a faulty microphone, or claim a larger model guarantees accuracy.

Research used Agent Reach's Jina Reader backend and primary-source web verification.
NVIDIA API pages currently document these hosted models on the same TLS Riva endpoint:

| Role | Model | Function ID | Language |
| --- | --- | --- | --- |
| Accepted primary | Parakeet TDT 0.6B v2 | d3fe9151-442b-4204-a70d-5fcc597fd610 | en-US |
| Different architecture backup | NVIDIA-hosted Whisper Large v3 | b702f636-f60c-4a3d-a6f4-f3568c13bd7d | en |
| Selectable spare | Parakeet CTC 1.1B | 1598d209-5e27-4d3c-8079-4751568b1081 | en-US |

- [Vosk size/accuracy guidance](https://alphacephei.com/vosk/models)
- [Whistle card](https://huggingface.co/Cactus-Compute/whistle)
- [Primary API](https://build.nvidia.com/nvidia/parakeet-tdt-0_6b-v2/api)
- [Whisper API](https://build.nvidia.com/openai/whisper-large-v3/api)
- [CTC API](https://build.nvidia.com/nvidia/parakeet-ctc-1_1b-asr/api)
- [NVIDIA free development access](https://developer.nvidia.com/nim)

Canary's suggested page was not accessible in verification; it was not guessed or
added. Published model claims are not owner accuracy evidence. These endpoints are
free for developer prototyping subject to account/model rate limits, not guaranteed
permanent production access. No GPU/container install, paid endpoint or alternate
organization receives audio. NVIDIA-hosted Whisper does not call OpenAI's API.

## Implemented behavior

- `audio/nvidia_asr.py`: primary plus at most one model backup per question. Default
  Parakeet -> Whisper; explicitly selected Whisper -> CTC; explicitly selected CTC
  -> Whisper. Successful first recognition does not duplicate audio. Empty output,
  retired/unimplemented model, unavailable service, RPC deadline or internal service
  error may switch once. Authentication, permission, quota and invalid-input errors
  stop without trying to evade the failure. Each request has a 15-second deadline;
  backup may add delay (up to roughly 30 seconds of RPC deadlines across two attempts).
  No unlimited loop, hidden local guess, transcript rewriting or raw provider-error
  logging. Cancellation and current privacy policy checked before each attempt.
  Exhausted services, auth/quota or privacy blocking stop the online listener with
  text/restart guidance rather than repeatedly capturing a new question or blaming
  the microphone. Other microphone failures retain their existing bounded handling.
- `audio/voice.py` / `desktop/app.py`: selected model and backup status surface in
  LYA. In online-only mode private capture cannot dispatch to any local decoder;
  the owner is told to type. Larger local Whisper is not warmed. Local Vosk remains
  only for wake/standby/stop, with those live gates still unresolved. Cloud speech
  input grants no identity or protected-action authority. Current accepted output
  voice is preserved.
- `tools/start_nvidia_lya.py`: `--nvidia-model parakeet|whisper|parakeet-ctc`, hidden
  session-only key entry and existing isolated client environment. No credential
  file or key in command arguments. Private mode must be enabled BEFORE confidential
  speech; already-sent audio cannot be recalled. Private mode does not inspect
  incoming audio for secrets before recognition.
- `launch-lya.cmd`, `launch-lya.ps1`: normal launch now chooses online hearing.
  `tools/set-startup.ps1`: existing project-owned sign-in shortcut migrated to the
  online launcher and verified; `-OnlyIfExisting` preserves disabled/unrelated
  startup entries. Key entry remains visible at sign-in before microphone access.
  Raw `desktop/app.py` local flags remain legacy/explicit diagnostic paths.
- `tools/check_nvidia_hearing.py --model whisper`: fresh speech-only specific-model
  check, with fallback DISABLED so another model cannot masquerade as its result.
  No saved-recording input, audio-file writing or assistant/device action.

## Checks, pending result and operating limits

70 isolated voice/hearing checks passed plus one existing designed online skip;
58 offscreen desktop checks passed. Fake secrets/client, synthetic PCM, temporary
stores, disabled sensors/speech/network model requests. Checks cover model retirement,
correct IDs/language, bounded fallback, quota/auth stop, cancellation/privacy before
the backup, no local substitution, no heavy local warmup and explicit primary choice.
All three actual installed Riva request schemas passed without a network channel.
CLI help, affected tracked whitespace, PowerShell parsing and owned startup target
verification passed. Main desktop package dependencies unchanged.

An ordinary fresh Whisper backup check window was launched for hidden local key
entry followed by manual Enter. Launch is not proof of collection or recognition.
Owner could not identify the window/key step. The diagnostic now names the selected
model and explains using the same NVIDIA key, hidden paste and no file upload/chat
disclosure. A dedicated `LYA - NVIDIA Whisper Backup Test` window was launched;
owner visibility and actual backup result remain unconfirmed.
**At initial launch, backup owner accuracy was pending; the qualified owner result
above supersedes that status.** No new provider result or owner words were
collected by the agent while building. Earlier saved private recordings stay local.
The integrated online LYA desktop has not been restarted/accepted in this task.

Run the specific backup check, compare its displayed words with actual speech,
then close existing LYA normally and use `launch-lya.cmd` for the integrated gate.
If a primary is withdrawn, select `--nvidia-model whisper` or `parakeet-ctc` in the
session launcher. Model IDs need review against the official catalog if all retire.
These backups share NVIDIA infrastructure: they cannot guarantee operation through
a complete provider/internet outage or a shared key/quota failure. All failures
leave text input available; do not promote unverified audio to a device action.
No continuous availability monitoring or backup-quality guarantee is implemented.
Enrollment/weather remain deferred.
