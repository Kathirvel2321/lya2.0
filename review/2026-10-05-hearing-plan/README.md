# Hearing research and build plan — 2026-10-05

Latest: fresh local comparison failed by owner report; online hearing and bounded
NVIDIA model backups selected. [Current results and operating limits](online-backups.md).

Update: the owner confirmed the fresh NVIDIA transcription was exactly accurate.
The speech-only gate passed for that ordinary question. Connection, privacy checks
and remaining activation/acceptance limits: [nvidia-connection.md](nvidia-connection.md).
The pilot-stage status below is dated evidence preceding that owner result.

Hearing remains unaccepted. Earlier retry/UI fixes did not improve recognition.
Preserve the output voice the owner accepts. Evaluate one small candidate before
connecting or promoting it, rather than adding more failed defaults.

| Option | Verified facts | Decision |
| --- | --- | --- |
| Cactus Whistle | Publisher lists a 16.9 MB CPU model, English support, 30-second maximum per pass and Windows x64 runtime. Model/engine repositories label Apache-2.0. | Build one bounded local pilot. Publisher Apple M4 speed results do not establish Windows performance or owner accuracy. |
| NVIDIA hosted Parakeet TDT 0.6B v2 | Official catalog provides English ASR through Riva gRPC on NVIDIA infrastructure. | Optional independent cloud comparison; not enabled or called. Requires configured key and permission to send fresh ordinary speech. |
| NVIDIA local Speech NIM | GPU-oriented deployment, separate from calling the hosted API. | Do not install a GPU server stack for this small laptop pilot. |

Sources checked with Agent Reach's Jina Reader backend and primary-source web
verification. Agent Reach/Exa/GitHub CLIs were unavailable; no CLI research success
is claimed. The old Cactus engine project is distinct from Whistle in
`cactus-compute/needle`. Some indexed older documentation paths now return 404;
current package source and publisher guides take precedence.

- [Whistle model card](https://huggingface.co/Cactus-Compute/whistle)
- [Publisher repository](https://github.com/cactus-compute/needle)
- [Supported platforms](https://cactuscompute.com/blog/needle-supported-devices)
- [Python runtime and telemetry](https://cactuscompute.com/blog/needle-python-docs)
- [NVIDIA Parakeet API](https://build.nvidia.com/nvidia/parakeet-tdt-0_6b-v2/api)
- [NVIDIA free development access](https://developer.nvidia.com/nim)
- [NVIDIA staff explanation of rate limits and development/production use](https://forums.developer.nvidia.com/t/request-more-4-000-credits-option-on-build-nvidia-com/344567)

NVIDIA's official information describes free prototyping with account/model rate
limits; old credit-count advice is outdated. This does not establish this owner's
account eligibility, rate limit or a permanently free production service. An API
key for a chat model does not make that model a speech recognizer.

## Plan recorded before building

1. Download only pinned public Whistle weights, Python client and matching Windows
   engine. Verify publisher SHA-256 values. No training/GPU/microphone extras.
2. Run speech-only inference in a hidden worker: 512 MiB process memory ceiling,
   at most two CPU affinity slots, below-normal priority, 30-second timeout,
   explicit local paths, telemetry and Python networking disabled. The parent
   stops it on timeout/cancellation. This limits this worker; it does not certify
   that third-party software cannot have defects or measure whole-device impact.
3. Check public generated speech and silence, then compare the already-authorized
   private recording locally. No fresh recording, cloud upload or media playback.
   Private audio/transcripts remain outside project artifacts.
4. Connect an experimental recognizer choice only if the pilot demonstrates useful
   recognition. Keep permissions and complete-question rejection. A 30-second
   model needs separately tested long-turn handling; never silently truncate a
   longer question. No model-derived tool calls execute.
5. If owner accuracy is still not established, report that failure and keep the
   broader LYA work independent of voice using the existing text composer. A
   cloud speech comparison is a separate opt-in; no paid fallback.

## Implemented and checked

- `audio/local_whistle.py`, `tools/whistle_worker.py`, `tools/setup_whistle.py`:
  pinned assets and publisher license verified; isolated speech-only worker runs
  under the recorded limits. No pip installation into LYA, implicit download or
  microphone access. Python network calls are denied, publisher telemetry disabled;
  this is not an OS network sandbox for a native DLL.
- Public generated speech: all meaningful words recovered, with a trailing quote;
  about 1 second worker wall time and 56 MiB peak worker memory. Three-second
  silence and seeded steady noise returned no words. These public fixture results
  do not establish real microphone hearing or whole-device performance.
- Existing owner-authorized recording: recognition failed. Audio and exact words
  remain outside project artifacts. **Whistle is not connected to the production
  listener.** Its candidate-returning diagnostic has no command dispatch route.
- `audio/nvidia_asr.py`: fixed hosted Parakeet TLS endpoint, explicit audio opt-in,
  local key input, complete mono 16 kHz PCM16 validation (120-second bound), all
  result segments joined, 15-second RPC deadline, cancellation, channel cleanup,
  generic provider errors and no alternate-provider fallback.
- `tools/check_nvidia_hearing.py`: fresh capture only, no saved-file upload option,
  no audio file writing, no LYA answer generation or command execution. Manual
  readiness and three-second speech pause; existing VAD/input-selection code reused.
  This reuses the current capture path, so it cannot by itself fix a wrong input,
  weak signal, overflow or VAD failure. Ctrl+C stops the check.
- `requirements-nvidia-speech.txt` / ignored `.venv-asr/`: optional Riva 2.27.0
  installed separately. Pilot package precedence preserves its protobuf dependency;
  capture libraries reused from `.venv-ui`. No CUDA/GPU server stack or main
  desktop dependency change. Actual Riva request schema and capture imports passed
  without opening a channel or microphone.
- `test_hearing_pilots.py`: 14 isolated checks passed using fake secrets/client and
  synthetic audio, including resource-control failure, timeout, cancellation,
  permission gating, malformed/long audio rejection and full-result joining.
  Diagnostic `--help` passed without runtime collection.

## Owner acceptance and next step

Owner explicitly allowed one fresh ordinary speech-to-text request to NVIDIA.
The earlier private recording remains local-only. A visible interactive diagnostic
window was launched; it waits for hidden key entry and then Enter for recording.
The tool-panel attempt was stopped before key entry/microphone access because the
panel open was queued. Launch success is not proof the owner sees the window or
that NVIDIA recognition works. No hosted ASR result is available yet; **hearing
remains unresolved**, and production has not switched recognizers.

In the window, enter a free-development NVIDIA key locally, close competing LYA
voice listening, press Enter when ready, and speak one ordinary question naturally.
Read `RECOGNIZED WORDS` before any assistant integration. Compare exact words with
what was spoken; inaccurate output fails this gate. Do not type keys into chat.
Noisy-room performance and private/confidential use need separate decisions and
tests; this ordinary cloud check does not establish those capabilities.

To reopen the check from the project directory:

```powershell
.\.venv-asr\Scripts\python.exe tools/check_nvidia_hearing.py --allow-fresh-audio-to-nvidia
```

NVIDIA account access/rate limits and any later production terms still need to be
verified locally. No automatic paid fallback exists. Output voice unchanged;
enrollment, weather and interruption acceptance remain deferred.
