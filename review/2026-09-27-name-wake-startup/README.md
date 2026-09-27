# Automatic startup and flexible name wake — 2026-09-27

Owner reported wake/claps still did nothing after opening the laptop and clarified that any LYA/Laya/Leya/Elya-like name inside a sentence should wake the assistant without manually launching it.

## Evidence and changes

- A normal-session process check found no running LYA desktop process at investigation time. No LYA entry was found in the user's Startup folder or user Run key. This explains why no listener could respond at that moment; it does not retroactively prove the cause of every prior failed attempt.
- Dormant recognition still required `hey` or `wake up` before the name. `audio/voice.py` now uses shared whole-word name matching, supported local-model phonetic spellings and grammar allowing surrounding unknown words. Wake does not require a prefix. `hey lya wake up` also routes to the wake greeting during a conversation.
- The real model initially missed generated `Elya` and a sentence containing `Laya`. Expanded acoustic aliases/context grammar fixed those fixture misses. `layer` is included because the model renders some Laya pronunciations that way; ordinary uses of that word can also wake LYA. No claim of arbitrary-pronunciation accuracy is made.
- `tools/set-startup.ps1` creates a per-user native Windows Startup shortcut to the existing interpreter and desktop with `--skip-setup`, microphone enabled. It was executed and verified: shortcut exists, target/arguments match, microphone is not disabled. It avoids registration/enrollment on startup. Use `tools/set-startup.ps1 -Disable` to remove only this owned shortcut.
- `desktop/app.py` uses Qt's existing `QLockFile` in the user's temporary directory to prevent duplicate desktop microphone readers. No new service/dependency was added.
- The updated app was launched in the normal desktop session. It remained running after three seconds; a second launch exited successfully rather than creating another instance. No previously running app was terminated.

## Checks

- Voice/transport: 28 tests, 27 passed and 1 intentional online skip.
- Offscreen base/compact desktop: 44 passed.
- `check_names.py`: installed Piper generates public samples, installed Vosk recognizes them using a fake input stream; no speaker or microphone. Seven positive phrases and four negatives, each with claps enabled/disabled: all 22 expected results; zero false clap events on those eleven speech samples. Results in `model-check.json`.
- User Startup shortcut verification and real duplicate-launch check passed. Future sign-in, sleep/resume recovery, the owner's accent and real claps remain unverified.
- Source whitespace check passed. Existing source/work and private stores preserved.

Startup configuration and starting the requested voice assistant were authorized by the owner's hands-free startup request. The app is now running normally, with the existing post-wake command transcription configuration. No developer test sent audio online; generated speech checks used only local models. No recorded audio, biometric material, credential or private runtime readings were put in this report.

## Current acceptance

Without opening anything, say `Laya` or `Leya`, or `hey LYA wake up`. Expect the spoken invitation; ask time after the greeting. While LYA is quiet, test two claps about half a second apart. Record each trigger independently. Do not call the step accepted until the owner confirms it.

Automatic startup means after Windows sign-in, not while powered off, asleep or before sign-in. Clap thresholds and owner pronunciation may need live calibration. The assistant still pauses recognition during its own speech. Broader name wake may produce false wakes; waking grants no identity/permission. Commands said in the same breath as the wake name are not guaranteed to be retained: wait for the invitation for this acceptance step.
