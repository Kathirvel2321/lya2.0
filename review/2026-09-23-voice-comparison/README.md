# Voice implementation comparison — 2026-09-23

## Decision

`external work/` is the canonical LYA voice runtime. `lya-external-work/lya-voice/`
is retained as an isolated quality research bench and optional remote comparison.

## Evidence

| Area | `lya-external-work/lya-voice` | `external work/` | Decision |
|---|---|---|---|
| Primary synthesis | Microsoft Edge TTS over the network; Sarvam adapter | Local Piper ONNX, Windows SAPI fallback, remote adapter gated | Keep local runtime |
| Tamil + English | One multilingual voice candidate; remote text leaves device | Offline Tamil works; unified Piper English is known to be weak | Listening gate remains open |
| Conversation playback | Builds temporary files and starts one player after rendering | Streams chunks through one reusable output device stream | Keep production stream path |
| Resource control | ffmpeg subprocesses and cloud latency; no hard local model budget | Two ONNX threads, spinning disabled, bounded queue, cancellable worker | Keep production controls |
| Security | Keys/env and remote path are present; quality engine is cloud-first | `auto` is local-only; private text cannot use remote; text-free audit | Keep production policy |
| Prosody | Ten moods, ffmpeg realism and pitch/rate post-processing | 22 emotions, 7 styles, bounded prosody and clean everyday delivery | Merge ideas only where they preserve clarity |
| Test evidence | Smoke test blocked here because `ffmpeg` is unavailable; no owner listening acceptance | 139 isolated tests pass; real Piper English/Tamil render checks pass | Trust the verified pipeline, not an unrun smoke test |

## Change made

The canonical runtime now keeps one `sounddevice.OutputStream` open for all PCM
chunks in a reply, writes small bounded blocks, drains the final words, and aborts
and closes the stream on cancellation, device failure, `stop()` or `close()`. This
removes phrase-by-phrase device reopening, which was a likely source of audible
gaps, without adding a model or a background worker.

## Explicit limits

No test can prove that a voice sounds like a particular age or person. The owner
has rejected the current unified Piper voice for English naturalness, so this is a
runtime reliability improvement, not an acceptance of the voice identity. A true
cross-lingual local model remains a future evaluation only if it fits the laptop's
memory budget and licensing requirements.

## Reproduction

```powershell
& .\\.venv-ui\\Scripts\\python.exe -m unittest discover -s 'external work/tests' -t 'external work'
```

Expected result on 2026-09-23: `139 tests`, `OK`, with one ffmpeg-dependent test
skipped when ffmpeg is absent.

## 2026-09-23 continuation: bounded quality and resource check

The same invented everyday English and Tamil lines used in the existing local
samples were rendered with Edge's `en-US-AvaMultilingualNeural`. Only those public
lines were transmitted. No owner conversation, key, microphone input or biometric
data was used. The script is `generate_public_edge_samples.py`; the resulting
files are [English](samples/edge-ava-english.mp3) (31,536 bytes) and
[Tamil](samples/edge-ava-tamil.mp3) (33,984 bytes). Generation took 8.67 seconds
and 5.55 seconds respectively on this run. Compare with the older local
[English](../2026-09-22-external-voice-integration/samples-clean/english-everyday.wav)
and [Tamil](../2026-09-22-external-voice-integration/samples-clean/tamil-everyday.wav)
files. These files are for listening; their existence does not establish naturalness.

Two short public lines were also synthesized locally without speaker playback or
file output. A fresh process took 4.42 seconds total / 3.80 seconds to first
audio for English, then 0.35 seconds total / 0.11 seconds to first audio for a
warm Tamil turn. The process peak working set was about 190 MB. An earlier fresh
run varied up to 8.34 seconds for its first turn, so cold latency is sensitive to
current laptop load. No large model was installed. The CLI memory helper initially
returned zero because its Windows handle lacked a pointer-sized return type; it
now reports a real value and has a regression check.

The playback stream's open/write/close operations now share a lock, closing the
race where cancellation could close a stream during a write. A concurrent-stop
test passed. Focused runtime and CLI checks: 30 passed. Live output device
smoothness and owner listening are still unverified. Remote speech remains disabled
in production by policy; the public samples do not change that decision.
