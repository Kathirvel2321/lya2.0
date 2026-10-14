# Local speech implementation and owner recording comparison — 2026-10-04

The owner requested recording, GitHub/internet research with Agent Reach, and a
free implementation that understands natural longer English questions. The owner
reports that the original playback is clear. This is useful audibility evidence,
not proof of recognition accuracy or a judgment of pronunciation. The agent had
no direct audio audition capability and used local recognition comparisons.

## Implemented and isolated-tested

- `audio/voice.py`: session input selection via `LYA_MICROPHONE`, native WASAPI
  preference and explicit failure when the selected input is unavailable;
  2.5-second quiet gap, 120-second bounded turns, rejection of incomplete turns;
  cancellation after a slow decoder prevents stale question dispatch.
- `audio/local_whisper.py`: optional English small-model CPU/int8 command adapter,
  warmed before readiness, cached once, all clauses retained, uncertain/repetitive
  questions rejected as a whole. It requires installed tokenizer/model files and
  uses `local_files_only=True`. Confidence is a rejection heuristic, not accuracy
  proof. No expected question is supplied as a prompt or hotword.
- `desktop/app.py`: microphone menu, asynchronous restart after the old reader
  exits, pending restart cancellation on manual stop; recognizer selection;
  remote audio is an explicit `--cloud-voice` opt-in instead of automatically
  enabled by a stored key. Whisper is experimental and **not the default**.
- `desktop/app.py`, `desktop/experience.py`: **Use Windows Voice Access input** /
  `--system-dictation` disables LYA's listener and prepares the existing editable
  chat composer. The owner dictates through Windows, then says **press Enter**.
  This is a text-input fallback, not an embedded Microsoft speech API or a claim
  that Windows dictation has passed on the owner. It has no automatic turn submit.
- `audio/local_asr.py`: standalone Zipformer streaming comparison adapter;
  deliberately not connected to production after the owner comparison failed.
- `tools/setup_local_asr.py`, `audio/requirements-local-asr.txt`: explicit public
  model setup and reproducible production dependency versions. Streaming setup
  is optional and requires sherpa-onnx 1.13.8; it is not a default dependency.
- `tools/record_voice_question.py`, `tools/compare_private_question.py`: explicitly
  owner-requested private recording and local comparisons. Recording copies stay
  in an owner-local temporary directory outside this project. No owner audio,
  exact transcript, device identity, fingerprint or signal measurements are
  stored in this report, source-control artifacts or project brain.

## Evidence and actual acceptance status

| Candidate / stage | Result |
| --- | --- |
| Current US Vosk and Indian small Vosk | Did not recover the owner question faithfully |
| Local streaming English Zipformer | Did not establish owner accuracy improvement |
| GTCRN-filtered streaming comparison | Did not establish improvement; no production filter added |
| Whisper base English | Repetition/unrelated recognition; not promoted |
| Whisper small English, original recording | Still incomplete/unrelated recognition; not promoted |
| Whisper small English, filtered recording | Repetition; no improvement established |
| Actual production Whisper adapter | An initial confidence-only check accepted a wrong candidate; added repeated-phrase rejection, rechecked the same authorized local sample and rejected it without forwarding a question |
| Real model with existing generated public speech and silence | Both expected smoke outcomes passed; does not establish owner accuracy |
| Windows Voice Access English–India | Owner agreed to test; actual setup, dictation text and answer acceptance remain pending |

Checks: `test_local_whisper`, `test_voice`, `test_voice_live_check`,
`test_setup_speech`: **56 passed, one intentional online skip**. Isolated desktop
checks: **52 passed**. Tests include slow internal pauses, complete-clause
rejection, confident repetitions, no cloud fallback after uncertainty, missing
tokenizer refusing runtime downloads, microphone restart cancellation and no
dispatch after decoder cancellation. `tools/check_local_voice_ui.py` patches live
microphone, playback, synthesis and model calls and uses temporary storage with
fake in-memory encryption keys. `git diff --check` and changed-tool syntax checks
passed. The real-model smoke evidence is `synthetic-whisper-check.json`.

Public weights live under ignored `models/speech/`. Provenance:
`whisper-model-source.json`, `streaming-model-source.json`. The downloaded Whisper
weight checksum matched the publisher's SHA-256 at the pinned revision. The model
download backend stalled; resumed standard HTTP download completed and was
verified before installation. No executable model download was run.

## Ready test and limitations

The owner confirmed readiness for the independent Windows check. LYA was launched
with `--system-dictation --skip-setup`, and Windows Voice Access was launched.
Process liveness was observed. Initial command-line-filtered checks missed the
processes; that mistake was corrected. Windows Computer Use initialization failed
twice with a sandbox helper setup error, so screen state and microphone setup
could not be verified through automation. The owner must handle any Windows
microphone/privacy consent screen. No Windows device/privacy setting was changed
by the agent. The pending owner question asks for recognized text before Enter,
or the current download/setup stage.

Whisper remains opt-in; larger-model comparison did not justify replacing the
default recognizer. Noise suppression cannot distinguish this owner's voice from
nearby speakers. Current Vosk wake/interruption and actual reply latency still
need owner acceptance. ASR is input, never identity or authorization; private
actions keep existing authentication/approval. Local audio recognition does not
change the configured text-brain route. No owner audio was uploaded; no new
recording was made during the Windows control test, no enrollment was performed,
and no paid speech service was enabled.

Next: compare English–India dictation text with the spoken question. If it succeeds,
test sending the clock question and cancelling playback through the existing
keyboard control. If it fails too, compare another existing input path before
buying equipment or downloading more models. The spoken clock/stop gate remains
failed/pending; weather and enrollment remain deferred.

### Later route audit and owner feedback

The owner requested a clear answer about the upgraded build instead of another
test loop; no Windows dictation result was supplied. Audited the current route:
normal launch uses Vosk, optional local Whisper is the tested small English model,
and the already-present Groq route requests `whisper-large-v3`. Upgrading the
text-brain model does not upgrade speech recognition. No reliable voice output
has been delivered or claimed.

Hardened the Groq opt-in: missing configuration, provider failure and empty results
fail explicitly. Removed the old implicit Google-audio fallback and the silent
local-guess fallback after Groq failure. Fake-key success/failure/empty-result
checks pass without network calls. Groq documentation lists a quota-limited Free
plan and separately billed Developer tier. Owner account tier was not inspected
or changed. A pending choice requests agreement for **fresh ordinary test audio
to Groq on a confirmed Free account**. Previously retained audio remains local;
no Groq audio request has been made. This is a candidate test, not an accuracy
or zero-cost guarantee on an unknown account. No further microphone test is
requested until that route/privacy/cost choice is resolved.

[Groq speech models](https://console.groq.com/docs/speech-to-text),
[Free-plan limits](https://console.groq.com/docs/rate-limits),
[Billing tiers](https://console.groq.com/docs/billing-faqs).

## Primary sources

Agent Reach's documented Jina repository-reader fallback was used because its CLI
and GitHub CLI were unavailable. Its update check was unavailable. Official
sources were also checked with web search/open; no owner recording was sent to
these sources.

- [Microsoft Voice Access setup: offline recognition, English–India and input selection](https://support.microsoft.com/en-us/accessibility/windows/voice-access/set-up-voice-access)
- [Microsoft Voice Access states](https://support.microsoft.com/en-us/accessibility/windows/voice-access/get-started-with-voice-access)
- [SYSTRAN faster-whisper: CPU int8 and local model usage](https://github.com/SYSTRAN/faster-whisper)
- [SYSTRAN English small model](https://huggingface.co/Systran/faster-whisper-small.en)
- [Sherpa streaming English models](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html)
- [Sherpa microphone and endpoint example](https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/speech-recognition-from-microphone-with-endpoint-detection.py)
- [Sherpa GTCRN example](https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/offline-speech-enhancement-gtcrn.py)
- [GTCRN authors](https://github.com/Xiaobin-Rong/gtcrn)
