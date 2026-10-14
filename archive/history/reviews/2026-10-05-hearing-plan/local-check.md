# Fresh offline hearing comparison — 2026-10-05

Outcome update: owner reported both fresh local transcriptions were incorrect.
Local acceptance FAILED. Owner subsequently selected online hearing with backups;
see [online-backups.md](online-backups.md). Earlier pending status below is historical.

Owner clarified that the next check must run fully offline on the laptop. This
does not authorize ongoing NVIDIA questions; that activation stays pending.

Implemented `tools/check_local_hearing.py`: manual Enter readiness, existing selected
input/VAD capture, three-second end pause, complete 30-second bound, one fresh WAV
kept in memory and passed sequentially to current local Vosk and experimental
Whistle. The owner is asked for a question under 20 seconds to allow capture margins.
No microphone opens before readiness, audio file is written, cloud route invoked
or transcript dispatched to LYA. Candidates are shown for owner comparison; Vosk
uncertainty stays explicitly marked. Whistle candidates are diagnostic, not
accepted commands. No recognizer/default or output-voice change.

Python networking denied through audit hook, Hugging Face offline mode and publisher
telemetry-off flags. Whistle uses the existing verified bounded worker (two CPU
slots, memory/time ceilings). This is not an OS network sandbox for native code.
The larger installed Whisper model is an optional `--include-whisper` check, not
loaded by the default test. No weights or new dependencies were downloaded.

Three isolated synthetic checks passed: same complete audio and local-only routing;
uncertain words remain marked and never dispatched; oversized input is rejected
before either decoder. `--help` passed without sensors/model loading. An existing
public generated-speech fixture was decoded by both actual local engines, recovering
all meaningful words (Whistle also produced a trailing quote). This only validates
the comparison setup; prior owner recordings failed local ASR, and the fresh
owner-local result remains pending.

A visible comparison window was launched. Launch success does not prove owner
visibility, microphone collection or accuracy. The owner controls Enter and can
stop with Ctrl+C. Close competing LYA voice listening, speak one ordinary question
naturally and wait for both output sections. Compare actual words, not simply
whether sound was detected. Keep screenshots/exact transcripts outside the ledger.

To reopen from the project directory:

```powershell
.\.venv-ui\Scripts\python.exe tools/check_local_hearing.py
```

Next: owner reports whether either local engine accurately transcribed this fresh
question. A failed result must remain failed. Do not substitute successful NVIDIA
recognition as proof of local hearing. Enrollment/weather remain deferred.
