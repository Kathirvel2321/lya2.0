# Voice conversation and orb states — 2026-10-03

Owner requested accurate hearing/answers, a more natural female voice, complete questions, obvious listening/thinking animation inside the circle, and spoken stop. Changes are implemented and isolated-tested. **Live command and interruption acceptance failed**, including a retry where the owner confirmed speaking both commands with the headset microphone close.

## Implemented

- audio/voice.py: one-second pre-roll; 1.2 seconds without speech ends a turn; 30-second ceiling declines an unfinished fragment. Streaming local Silero VAD uses the already-installed optional faster-whisper 1.2.1 package. Missing/incompatible VAD falls back to local Vosk speech gating and endpoint continuation. Speech detection separates speech from non-speech noise, not the owner from other speakers. No package was installed for this change.
- Local Vosk retains finalized segments and requests word confidence. Empty text, any word below 0.45, or mean below 0.75 requests a repeat. Confidence is a rejection heuristic; confidently wrong words can still pass. Existing optional remote recognition configuration remains unchanged. Production ASR was not replaced.
- While thinking/speaking, the single microphone reader uses unrestricted local recognition for exact stop/cancel/stop-speaking matches. Stable partial/final commands use existing Qt cancellation. There is no acoustic echo canceller or owner speaker isolation. A narrow grammar experiment falsely stopped on unrelated speech and was removed.
- desktop/app.py and desktop/experience.py: cyan listening/hearing microdots, violet thought orbits/diamond, green speaking dots, standby and uncertain states inside the existing circle. Hearing responds to aggregate transient level. Visible active states animate continuously; hidden/reduced-motion states stop timers. Tooltip/accessibility text names the state. Normal voice requests hide the thinking panel and show the answer upon completion. Wake stays in the compact circle.
- desktop/setup_speech.py chooses installed Amy English Piper, falling back to the previous English model when absent; Tamil stays native. desktop/assets/wake-greeting.wav now uses Amy. The old greeting is preserved locally here. Naturalness remains owner-unaccepted.
- tools/check_conversation_live.py and tools/check_asr_comparison_live.py provide bounded local diagnostics with audible cues/countdown. Owner audio stays in memory and is discarded. No recording/transcript file or provider request.

## Verification and artifacts

Read older tests before execution. Tests use fake secrets, temporary storage, fake devices or generated public audio. Existing unrelated changes preserved. No protected store, enrollment or device setting changed, and no production desktop restart. Live microphone/speaker trials were explicitly owner-authorized.

- test_voice + test_setup_speech: 43 checks, 42 passed and one intentional online skip. Coverage includes VAD despite sustained synthetic noise, speech-gated starts, continuation, uncertain/truncated input rejection, retries, interruption, cleanup and privacy routing.
- test_voice_live_check: 2 passed.
- Class-only desktop/check_experience.py: 30 passed; desktop/check_ui.py: 19 passed. Actual phase wiring, cancellation, panel visibility, visible active animation and reduced motion tested.
- external-work/tests/test_runtime.py: 18 passed with fake engines/temporary storage. Total: **111 passed, one intentional online skip**.
- check_vad_model.py / vad-model-check.json: real streaming inference detected generated Amy speech, rejected silence and a synthetic noise fixture, and released a quiet tail. Four expected outcomes passed; no crowded-room accuracy claim.
- check_stop_model.py / stop-model-check.json: final five generated-public-speech fixtures passed with two seconds of trailing silence. Stop/cancel detected; three unrelated phrases rejected. One-second tail missed stop; endpoint delay remains a limitation. Narrow grammar falsely stopped on “Please continue answering” and was rejected. Fixture success does not establish human barge-in.
- git diff --check passed.
- render_orb_preview.py / orb-states.png: visually inspected actual Qt renders on synthetic light/dark backgrounds, not owner desktop screenshots.
- Generated public WAVs (ignored local artifacts): amy-public-preview.wav, current-public-preview.wav, bella-public-preview.wav, amy-wake-greeting.wav, previous-wake-greeting.wav.

## Voice/model decisions

amy-timing.json: cold synthesis first audio 3766.5 ms; warm first audio 104.5 ms, total synthesis 500.3 ms for about 4.05 seconds of audio. These measure synthesis only, not answer latency or perceived naturalness. Existing prewarm reuses the worker.

check_voice_choices.py / voice-choice-timing.json: installed Kokoro Bella required a comparison-only speed-input dtype adapter, then took 28.3 and 30.0 seconds for about 2.9 seconds of generated audio. Rejected for production because of delay. No engine or dependency added to production.

The [official Vosk model catalog](https://alphacephei.com/vosk/models) lists the lightweight Indian English model and Apache 2.0 license. Downloaded models/speech/vosk-model-small-en-in-0.4 as an ignored candidate only; checked archive integrity and extraction confinement. command-model-candidate.json records public source, bytes and a locally computed checksum; no publisher checksum match is claimed. Agent-reach CLI was unavailable, so its documented web-reader fallback and the official page were used. Neither that candidate nor installed local Whisper base was connected to production.

## Live results and next gate

1. Initial local diagnostic detected wake, rejected uncertain clock recognition and missed spoken stop. Owner confirmed hearing output and speaking both commands. Acceptance failed.
2. Indian candidate wake trial timed out before command capture. A wake-bypassed candidate diagnostic remained uncertain and missed stop; participation timing was not confirmed.
3. Eight-second recognizer comparison is INVALID for owner accuracy: owner subsequently said there was no opportunity to speak and asked to retry. Ambient recognition is not owner accuracy evidence.
4. Repeated comparison used five low beeps, a high cue and a 20-second window. Both Vosk candidates included clock words mixed with extras and were uncertain. Local Whisper produced repetition/hallucination. No production model switch justified.
5. Final US-model retry with streaming VAD used the countdown, a bounded speech turn and microphone-open-before-output interruption. Clock words were recovered with a repeated word, but confidence rejection prevented forwarding. Stop was not detected; output worker ended without reported error. Owner explicitly confirmed saying the question and stop with the mic close. Live acceptance FAILED.

No owner transcript, audio or private device facts are retained in this report. These diagnostics did not exercise the desktop brain end to end. Changes require a desktop restart to load.

Workflow remains at wake -> full clock question -> correct transcript/answer -> stop. Next: isolate quiet close-mic capture and ASR before another model change; retain transcript/repeat guards and the existing manual stop control. Crowded-room owner isolation, whisper recognition, realistic voice acceptance, reliable acoustic interruption and answer latency remain unresolved. Enrollment and live weather stay deferred.
