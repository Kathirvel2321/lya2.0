# Wake failure investigation and two-clap wake

2026-09-27. Owner reports repeated "wake up LYA" produced no response and requests two-clap wake. This is the current first acceptance gate; prior isolated voice passes did not establish live wake success.

## Findings and changes

- Local Vosk model loads, and the required grammar aliases are in its vocabulary. The literal spelling `lya` is absent, so the recognizer continues using supported phonetic alternatives. No model download was needed.
- Previous standby capture opened short recording windows, waited for silence and then recognized a complete buffered clip. This could split a phrase across recording windows or delay recognition in noise. `_wait_for_wake` now holds a local input stream open and feeds 20-ms blocks to Vosk, matching complete wake phrases in partial or final results. It closes the stream before the command recorder starts. This removes a concrete reliability weakness; it does not prove that this was the sole cause of the owner's observed failure.
- `clap_enabled` previously had no effect. The desktop now explicitly enables it. `DoubleClap` accepts two short broadband impulses 0.18-0.8 seconds apart, rejecting sustained sound, one clap and out-of-window pairs. The same detector is used during standby and active command listening. Clap samples are not transcribed or uploaded. Clap wake uses the same guest wake/greeting path and grants no identity or permissions.
- An early amplitude/crest-only detector mistook parts of synthetic speech for claps. A high-frequency energy check was added; the final seven generated speech samples produce no clap events. This is still a heuristic, not a trained clap classifier.
- Input errors are no longer silently retried forever. Three consecutive failures stop the listener, errors appear in the status, and terminal failure opens a visible message. Ready is reported only after the microphone stream opens. The orb/tray tooltip shows listener status. Stream stop/cancellation and overflow handling are explicit.

Changed production files: `audio/voice.py`, `desktop/app.py`. Regressions: `test_voice.py`, `desktop/check_ui.py`. No dependencies, credentials, enrollment or authorization logic changed. Existing work preserved.

## Verification

- `python -B -m unittest test_voice test_setup_speech`: 28 tests, 27 passed, 1 intentional online skip. Includes short separated impulses, rejected single/fast/slow/sustained/tonal sounds, command-listening clap detection, local-only streaming, readiness after opening, bounded failures, and cancellation without late wake.
- Offscreen `python -B -m unittest desktop.check_ui.InterfaceChecks desktop.check_experience.ExperienceChecks`: 44 passed. Includes desktop clap opt-in, readiness/error presentation and existing speech/guest/cancellation regressions.
- `check_model.py` runs generated public speech through the actual installed Piper and Vosk models with fake microphone input. Seven phrases, clap detection on/off: 14 expected results. Three wake phrases recognized; four unrelated phrases ignored; no false clap events. Output: `model-check.json`. The consumed audio durations are not wall-clock response latency or proof of accuracy with the owner's accent.
- Restricted-session microphone open failed; the same 0.2-second read outside that restriction succeeded. A subsequent three-second run of the updated local listener outside the restriction opened the microphone and stopped cleanly with no errors. Audio remained transient; no recordings, transcripts or private runtime readings were saved. This proves startup/stop only, not successful human wake/clap recognition or spoken output.
- Process metadata inspection was access-denied, so no claim is made about which code version or microphone flags the owner's existing app instance is using. No running process was terminated.
- `git diff --check` passed on changed source/tests.

All commands used `.venv-ui/Scripts/python.exe`; Qt checks used `QT_QPA_PLATFORM=offscreen` and project/desktop on `PYTHONPATH`. Existing tests were inspected first.

## Acceptance and calibration

Quit existing LYA instances, then run `launch-lya.cmd --skip-setup` so this test uses updated code and stays outside enrollment. Say "wake up LYA" once. Expect the existing spoken invitation. While LYA is quiet, clap twice roughly half a second apart. Expect the same invitation. After it finishes, ask the time and expect speech. Report voice wake and clap wake separately.

`LYA_CLAP_THRESHOLD` controls RMS sensitivity in 16-bit PCM units, default 1500, accepted 100-20000. Lower is more sensitive and may produce more false wakes. Real room calibration is pending; do not lower it speculatively. Loud knocks can still resemble claps. Detection pauses during LYA's own speech; barge-in remains incomplete. Command transcription retains its existing local/opted-in remote policy. No live provider calls or human input recognition were validated here.

Status: implemented, isolated-tested, real microphone startup/stop tested; owner voice/clap acceptance pending. Next: resolve the first failed live trigger before adding higher capabilities.
