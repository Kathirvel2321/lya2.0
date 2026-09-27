# Live voice failure isolation — 2026-09-27

Owner continues to report no hearing/response after previous setup. The voice system is not owner-accepted. Prior microphone-open and generated-speech passes do not establish the real voice journey.

Added `tools/check_voice_live.py` and `check-voice-live.cmd`. This is a diagnostic, not another assistant or a replacement listener. It exercises the existing `audio.voice.wake_loop` locally and reports these independent stages in the terminal:

- Microphone opened.
- Sound received above a modest diagnostic floor (not a speech/identity classifier).
- Name detected or two claps detected.
- Local cached greeting playback call succeeded, or an error type.

It stops after the first wake or a 20-second listening window. The stop event is set before greeting playback so no command transcription occurs. No audio, transcript, model result text, private store, credential, or runtime report is saved; no network is used. A successful playback API call still requires the owner to confirm audibility. The existing app may also be listening; this probe cannot by itself establish the state of that app's UI or audio worker.

Usage: double-click `check-voice-live.cmd`, or run `.venv-ui/Scripts/python.exe -B tools/check_voice_live.py` in the normal Windows session. Wait for `LISTENING NOW`, say a wake name, and if no response clap twice. Read the resulting stage booleans. The script does not automatically change microphones, thresholds, volume, permissions or startup.

Verification: `python -B -m unittest test_voice_live_check test_voice test_setup_speech` ran 30 tests: 29 passed, one intentional online skip. New tests use fake microphone data, fake recognition and fake playback to distinguish silence, sound-only, name, clap and failure. The initial check caught use of an unavailable `winsound.SND_SYNC` constant; corrected to the native synchronous default, then reran successfully. No real microphone or speaker was exercised this turn.

An asynchronous readiness question was sent to the owner for a short live trial; no response was received before this handoff. Live failure diagnosis remains pending. Next: run the bounded check with the owner present, interpret the failing stage, and repair that stage before promoting any new feature. Do not describe this diagnostic's isolated tests as a fix to the owner's reported failure.

## Owner-ready live follow-up

The owner replied ready. Ran the bounded diagnostic in the normal Windows session: input opened, but the first run did not detect sound above its diagnostic floor, a wake name or two claps. No greeting playback was attempted.

A separate bounded input-channel comparison, cued with beeps, then confirmed sound reached both the selected microphone path and its WASAPI path. A second 20-second run of the actual wake diagnostic, also preceded by a cue, confirmed microphone input and sound activity but detected neither a wake name nor a double clap. No greeting was played and no input error was reported. No audio or recognized transcript was saved or transmitted; device identifiers and detailed input measurements are deliberately omitted here.

Conclusion: at least one live attempt reaches the sound-input stage but not wake detection. Opening a microphone is not the same as recognizing the intended utterance. Timing, level, acoustic conditions and detector sensitivity remain possible contributors; this check does not establish which one. Greeting audibility is still untested because no wake event reached playback. No production code, threshold, device setting or startup configuration was changed during these checks.

Next gate: separately cue and test name pronunciation and two-clap detection while measuring only the detector criteria in memory. Do not declare success or broaden features before an actual owner-triggered greeting. Owner-reported voice failure remains unresolved.
