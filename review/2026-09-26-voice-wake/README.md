# Voice wake, speech pre-warm and first-run polish — 2026-09-26 (independent review)

Owner asked for a full review and re-test of the 2026-09-26 change set. This is an
independent re-run of the offline suites plus a code read of every file touched that
day. No project file was modified except this README and the dated ledger entry in
`lya-project-brain.md`.

## Change set reviewed

| File                               | Change                                                                                                                                                                                                                                                                            |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `audio/voice.py`                   | wake loop now records locally, transcribes only after a local wake; Groq Whisper Large v3 path behind an explicit opt-in; legacy `speak()` re-routed through the reviewed `desktop/setup_speech.py` worker (no implicit online TTS); `stop_speaking()` kills the playback process |
| `desktop/setup_speech.py`          | `prewarm()` — worker process starts at launch with `--warm-piper`, model loads before the first request; warm/idle state kept 45 s                                                                                                                                                |
| `desktop/activation.py`            | six-act initialization walkthrough: real probes (no faked SECURE states), camera presence-only, mic meter with measured RMS/clip checks, window-bound Hello nonce, consent-gated admin commit                                                                                     |
| `desktop/app.py`                   | voice-first launch, `allow_cloud` decided by configured key, on-screen mode disclosure                                                                                                                                                                                            |
| `desktop/experience.py`            | wake greeting playback and dock behaviour                                                                                                                                                                                                                                         |
| `desktop/assets/wake-greeting.wav` | new wake sound                                                                                                                                                                                                                                                                    |

## Test results (re-run 2026-09-26, offscreen, offline)

| Suite                                           | Result                                               |
| ----------------------------------------------- | ---------------------------------------------------- |
| `test_setup_speech` + `test_voice`              | 20 passed, 1 skipped (explicit online Edge-TTS test) |
| `test_activation`                               | 22 passed                                            |
| `desktop/check_experience` + `desktop/check_ui` | 41 passed                                            |
| `test_registration_ui`                          | 22 passed                                            |
| `external-work` voice lab suite                 | 141 passed, 1 skipped                                |
| `test_foundations`                              | 14 passed                                            |

Total: 260 checks, all green, on `.venv-ui`. One skip per suite is by design (live
network tests are excluded from offline runs).

## What is good

1. **Wake stays local.** The 5-second pre-wake window is matched against a Vosk
   grammar on-device; audio is never streamed to a provider before the wake word.
   Commands after wake go remote only when the caller passes `allow_cloud=True`,
   and the live mode is shown on screen — never hidden.
2. **No implicit online TTS.** The legacy `speak()` now sends text to the same
   local Piper worker the desktop uses, capped at 1,000 characters, no shell.
3. **Prewarm is real.** The worker process loads the English Piper model at launch
   (`--warm-piper`), so the first answer no longer pays the ~4–6 s cold model load;
   the economy (SAPI) path correctly skips the Piper warm-up (regression-tested).
4. **Activation stays honest.** Biometric readiness always reports "not enrolled";
   camera/mic samples are measured, not scored by vibes; the Windows proof is a
   per-run nonce checked against the helper's literal output; consent is an
   explicit checkbox and the admin commit re-checks freshness, name match and
   one-admin enforcement.
5. **Cancellation paths hold.** `_SPEAKING` keeps the wake recorder from opening
   the mic while LYA talks (tested), and stop/cancel still route as R04 requires.

## Findings (review priorities, not exploitable vulnerabilities)

- **F1 — P2, legacy `speak()` blocks its caller.** `audio/voice.py::speak` runs
  `process.communicate(timeout=120)` on the calling thread, so a legacy caller
  waits for the whole synthesis. The desktop path (`SetupSpeech`) is unaffected;
  this only touches legacy callers. Fix target: post the payload and return, or
  document the blocking contract.
- **F2 — P3, one voice subprocess per legacy utterance.** Each legacy `speak()`
  spawns a fresh `setup_speech.py` process, reloading models (~200 MB) each time.
  The warm worker exists but is not reused by this path.
- **F3 — P3, review folder had no README.** The 2026-09-26 review directory held
  only an image; this file now records the work.
- **F4 — P3, minor tone mapping drift.** `set_rate()` maps rates to legacy tone
  names while `speak()` maps tones to alya-voice styles; harmless but two tables
  to keep in sync.
- **F5 — known-open, Windows proof.** The unsigned `HelloVerifier.exe` is still
  subject to Windows Application Control; the activation gate correctly fails
  closed. Nothing in this change set resolves it (by design — path choice is the
  owner's).

## Limits

- No microphone, camera, real Windows prompt, enrollment or cloud call was
  performed by this review. All suites ran offscreen with injected sensors.
- The pre-warm latency claim is structural; no fresh timed measurement of a real
  spoken first answer was taken.
- Wake-word accuracy with the local grammar (liya/leah/leia variants) is untested
  against a real microphone.
