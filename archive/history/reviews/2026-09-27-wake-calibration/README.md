# Wake detector calibration — 2026-09-27

Owner authorized continuing after live sound input passed but both wake gestures failed. Two separately cued, ten-second local stages examined name and clap detection without saving audio/transcripts. Owner confirmed speaking and clapping during the cues. A further eight-second comparison examined current and native microphone capture formats. Both received weak input; no assertion is made that the microphone volume is the sole cause.

## Changes supported by evidence

- Every captured burst was below the old fixed clap threshold. `audio/voice.py` now defaults to 150 rather than 1500 RMS units in `DoubleClap` and both recorder callers. The existing `LYA_CLAP_THRESHOLD` override and 100–20000 validation remain. This is a more sensitive default, not proof of real clap recognition; quiet noises may false-trigger and still require room acceptance. No Windows volume setting changed.
- A real-model generated-speech rerun exposed a provisional false name match on an unrelated sentence. Standby wake now waits for a finalized local Vosk result before matching a name. This adds silence/endpoint latency but prevents that provisional match from waking LYA. It does not solve arbitrary pronunciation or low signal-to-noise ratio.
- `test_voice.py` adds quiet clap and background-noise cases, uses finalized recognizer results for the streaming fixture, and rejects a provisional name that disappears from the final result.

## Verification and state

- `python -B -m unittest test_voice test_voice_live_check test_setup_speech`: 31 tests, 30 passed and one intentional online skip.
- Real Piper/Vosk generated-speech checks: 22 expected results, zero clap events on the eleven public speech samples. Script: `review/2026-09-27-name-wake-startup/check_names.py`; current results: its `model-check.json`. The initial run failed an unrelated-sentence case before finalized-result gating; the corrected run passed. No claim of reliable real-user name recognition follows from these fixtures.
- Source whitespace check passed. Existing changes preserved. Current desktop process was not restarted, so the changes are on disk and used by new test processes; do not assume an older running app has reloaded them.
- Live calibration used transient audio and local recognizers only. No waveform, transcript, detailed private runtime measurements, hardware identifier or cloud request was retained in project evidence. Safe summaries only.
- Opened Windows Sound settings without changing any settings. Asked the owner for the microphone input-volume value and whether its level meter moves strongly. That response is needed to distinguish Windows input level from recognition failure before the next live trial.

Next: confirm the selected microphone's Windows level/meter; address input configuration if warranted, then restart only the intended LYA instance and test a real name and real clap pair separately. Greeting audibility and reliable owner recognition remain unaccepted. No higher feature work should proceed yet.
