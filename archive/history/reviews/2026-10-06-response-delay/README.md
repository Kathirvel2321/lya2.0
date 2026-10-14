# Spoken response delay check — 2026-10-06

**Current status:** the owner subsequently explicitly requested a listening-delay
fix. The implementation below supersedes the original diagnostic's fixed
three-second NVIDIA endpoint. The original findings remain a dated snapshot.

Owner reports the longest wait after finishing speech, before the question
appears. This task checks the cause; the owner rule requires a specific request
before changing accepted pause, hearing, voice or interface behavior.

## Findings established by source and isolated checks

1. NVIDIA question capture uses **3.0 seconds of consecutive non-speech** before
   submission (`audio/voice.py:833`). The counter resets on detected speech
   (`audio/voice.py:469–471`). This deliberately permits slow speech/internal
   pauses. Background speech classified as speech can extend the wait; that
   condition was not measured in the owner's room.
2. Transcription is a **complete-question request**: capture ends before NVIDIA
   is called (`audio/voice.py:848–854`, `audio/nvidia_asr.py:97`). No live partial
   transcription is displayed. Each attempt creates/closes a TLS gRPC channel.
   Successful calls add their connection/upload/recognition time after capture.
   Each attempt has a 15-second deadline; one backup is conditional, not always
   called. Deadlines are failure bounds, not measured normal latency.
3. The spoken-question panel is **hidden while the brain prepares the answer**
   (`desktop/experience.py:772–788`). Recognized text is already forwarded to
   the brain at this point. The panel reopens in `on_brain` (`:833–863`) and
   adds the question prefix after the answer arrives. Thus time until the
   question becomes visible can include complete brain inference, not only
   microphone/recognition time. The existing UI test reproduces this behavior.
4. Public ordinary model answers are requested as complete responses, not
   token streams (`cloud/inference.py:93`). The Oracle bridge starts an SSH
   exchange per invocation (`brain/oracle.py`, `cloud/ssh_session.py`). No live
   remote timing, current route health or actual provider speed was checked.
   Protected/local requests have their existing separate policy.

For an ordinary non-chat spoken model request, the visible-question wait is:

`speech endpoint wait + complete transcription + complete brain response + UI delivery`

The three-second endpoint is a configured delay. Other stage durations and total
owner-perceived seconds are **unmeasured**. It would be incorrect to claim a
measured network bottleneck, slow CPU, faulty headset or fixed ten-second total.

## Validation

Five existing isolated checks passed:

- Slow complete question survives internal pause and ends at final pause.
- VAD ends a question despite synthetic loud non-speech room noise.
- NVIDIA complete-question request/TLS/deadline/cleanup with fake client/key.
- NVIDIA capture uses three-second pause while checking privacy before routing.
- Complete recognized question is forwarded through wake/command route.

One existing offscreen desktop check passed:
`ExperienceChecks.test_voice_thinking_uses_orb_without_status_box_then_displays_answer`.
Executed under `tools/check_local_voice_ui.py` isolation with its loader selecting
only that case. Temporary stores, generated fake encryption key, mocked brain,
microphone/playback disabled. Total **6 passed**. These are functional checks,
not measured owner speech/network/answer latency.

No production behavior, model, capture pause, output voice, UI appearance,
credential, startup or protected store changed. No owner recording/transcript,
microphone/camera collection, provider request, key access or desktop restart.

## Next step

The smallest useful feedback improvement is to show the recognized sentence
when transcription finishes, before brain inference. This would make hearing
completion visible but would not itself reduce recognition/model time. It
changes existing interaction/UI behavior and remains a proposal until requested.

Before shortening the three-second pause or changing connection behavior,
measure the live stages separately using transient duration-only diagnostics.
Prematurely reducing the pause risks cutting the owner's slow longer sentences.
Current hearing/output acceptance is preserved; no model switch is justified by
this source-only diagnosis. Enrollment/weather remain deferred.

## Authorized timing fix — 2026-10-06

Changed `audio/voice.py`, with checks in `test_voice.py` and
`test_hearing_pilots.py`:

- NVIDIA short questions finish after **2.0 seconds** of consecutive detected
  non-speech instead of 3.0. After 8 seconds of detected speech, or speech
  resumes after at least a 0.8-second pause, the rest of that turn retains the
  **3.0-second** finishing allowance. Other capture callers keep their existing
  defaults; all captured clauses are forwarded together. This is an audio-only
  heuristic: a first pause of 2 seconds can still end a short turn, and other
  people's speech can still prolong capture. It cannot understand unfinished
  sentence meaning before recognition.
- The existing lightweight VAD initializes before NVIDIA wake readiness.
  `faster_whisper` already caches its session, so each question then creates only
  fresh streaming state. Missing/incompatible VAD keeps the existing local Vosk
  fallback. No new model, dependency, service, gain filter or hardware change.
- The 120-second rejection bound, privacy recheck, stop/cancellation, primary
  Parakeet and conditional Whisper backup, output Amy voice, panel appearance,
  credential handling and startup choices are preserved.

Validation: the new synthetic endpoint check first failed before implementation.
After implementation, `python -m unittest test_voice test_hearing_pilots` ran
77 cases: **76 passed, one intentional online skip**. Cases include a short
question, continuous 8-second speech, a 1.8-second internal pause followed by a
2.8-second continuation pause, and exact retention of the complete PCM. A new
readiness check covers both successful VAD warmup and unavailable-VAD fallback.
Existing privacy, cancellation, capture-limit rejection, noisy non-speech and
fake NVIDIA backup/client checks pass. One isolated offscreen desktop check
preserves the existing thinking/panel behavior: **77 total passes, one skip**.
Python compilation and scoped `git diff --check` also passed.

Actual installed VAD schema validated without opening a microphone. Initial
load measured about 1.22 seconds in the first inspection; a separate saved
check measured 575.28ms initially and 0.03ms cached. These are startup-only
measurements and show variability; see [vad-initialization.json](vad-initialization.json).
Moving initialization before readiness removes that first-question setup wait;
it does not reduce total startup cost or establish live response latency.

No live owner speech, recording, provider request, key read, sensor activation
or running-session restart was performed. The exact yesterday-to-today cause
remains unproven. The known endpoint saves one configured second on eligible
short questions; network recognition and complete brain response still add
unmeasured time, and the existing panel waits for the answer before showing the
question. Next: reopen LYA and compare one short question with a natural longer
question containing pauses. Live speed and turn-completeness acceptance remain
pending; enrollment/weather remain deferred.
