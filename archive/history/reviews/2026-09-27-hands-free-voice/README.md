# First acceptance step: hands-free wake and reply

2026-09-27. Owner clarified that speech is the primary interface; typing is a public-place fallback. This supersedes the typed-only acceptance step in the foundation-ladder report. Continue one confirmed step at a time.

## Root causes and changes

- `desktop/experience.py::wake` prewarmed speech before `start_intro`, which called `close_panel` and killed that worker. Every command also killed even an idle worker. `SetupSpeech.stop(keep_warm=True)` now preserves only idle/warming workers; active speech is still cancelled. Navigation/commands use it; mute, shutdown and the existing 45-second idle expiry still unload the worker. Intro starts before prewarming.
- The cached wake response now says "I'm here. What can I help you with?" using the already installed English Piper model. Its 2.02-second WAV replaces the previous greeting intentionally. The former WAV is preserved at `previous-wake-greeting.wav` (local ignored audio artifact). The microphone speaking guard now uses the WAV's actual duration plus 100 ms instead of a hardcoded 1200 ms. A cancellable timer and shared greeting stop path prevent old timers or playback surviving command/close/quit.
- `audio/voice.py` ends the local wake recording after 0.4 seconds of silence instead of 0.8; command recordings retain 0.8 to accommodate natural pauses. Existing threshold calibration remains. The conversation window refreshes while LYA speaks, leaving time for a follow-up after a long answer.
- Clock/date/help/status routes previously returned text without speech. The compact desktop now speaks their displayed answer, respecting mute and a quiet turn. Reduced-motion output uses displayed text; animated output uses its complete target text.

## Checks and evidence

- `python -B -m unittest test_setup_speech test_voice`: 22 tests, 21 passed and 1 intentional online skip. Covers idle-worker reuse, active cancellation, prewarm preservation, shutdown, local-only wake, shorter wake endpoint, and follow-up after a simulated long reply.
- Offscreen `python -B -m unittest desktop.check_experience.ExperienceChecks`: 27 passed. New cases cover spoken clock/quiet turn, wake worker preservation, actual WAV duration, and greeting cancellation. The first run of the added spoken-clock check caught empty text in reduced-motion mode; the implementation was corrected before the passing rerun.
- Commands used `.venv-ui/Scripts/python.exe`; Qt used `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=<project>/desktop;<project>`. Existing scripts were reviewed before execution. No screenshot-writing entry point was run.
- `synthesis-timing.json`: one cold/warm local synthesis pair for the same public prompt, **4313.1 ms cold / 229.1 ms warm**. This includes model loading in the cold case, excludes interpreter/process startup, microphone, ASR, model answer generation and playback. It is supporting evidence, not a general latency benchmark or live acceptance result.
- `git diff --check` passed on changed source/tests. Pre-existing working-tree changes were preserved.

No microphone capture, real protected-store access, enrollment, cloud request or live speaker playback occurred. Cached public prompt generation stayed local; no dependencies or services were added.

## Owner acceptance, this step only

Quit the previous LYA instance. Start `launch-lya.cmd --skip-setup` (microphone listener enabled; skips the unrelated owner-setup gate). Say "wake up LYA". Expect the cached greeting asking for input. After it finishes, say "what time is it?" and expect a spoken answer without typing. After the answer, say "what date is it?" without another wake phrase. Repeat wake once after sleeping/letting the conversation expire.

Record whether the delay is before the greeting, after finishing the question, or before follow-up recognition. Do not declare this step complete until the owner confirms it on the actual microphone/speaker path. Post-wake transcription follows the existing configuration and may use the configured remote path; ambient pre-wake audio remains local.

Open limitations: the recorder pauses during playback to avoid recognizing LYA itself, so spoken interruption during an answer is not implemented by this fix. Streaming wake detection, live noise calibration, live cloud latency and voice naturalness remain unaccepted. The 0.4-second wake endpoint needs real-device acceptance. This is the first wake/listen/reply step, not a claim of a complete hands-free assistant.
