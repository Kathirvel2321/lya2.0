# Voice timing repair — 2026-10-03

Owner reports broken voice and replies arriving late. The audible defect is not yet classified (distortion, cut words, or robotic delivery). No live microphone, speaker, cloud, enrollment, or protected store was exercised in this task.

## Findings and changes

- `audio/voice.py`: the command recorder previously ended only after 0.8 seconds below a fixed peak gate, or after its 12-second ceiling. Sustained noise above that gate can delay submission until the ceiling. The hands-free loop now passes its already-loaded local Vosk model into the recorder. A finalized nonempty speech result provides an additional endpoint; empty results do not end capture. The existing silence fallback, ceiling, clap path, cancellation and full captured WAV remain. This is endpoint detection, not noise suppression or speaker isolation. Vosk may still miss speech, and long pauses can delimit turns.
- `external-work/alya_voice/runtime.py`: playback no longer adds the planned sentence pause after the last chunk. It still drains the final words, keeps pauses between chunks, and preserves export padding. This removes an avoidable delay before the desktop receives completion and releases its microphone guard; it does not establish an audible quality repair.
- Regressions in `test_voice.py` and `external-work/tests/test_runtime.py`: nonempty endpoints amid above-gate synthetic noise, ignored empty endpoints, silence fallback, local-only capture, model handoff, and no added final playback pause.

## Checks

Inspected the existing tests before execution. All capture/output devices in new tests are mocked. Existing playback tests use fake engines and temporary files. Online integration remains skipped.

```powershell
.\.venv-ui\Scripts\python.exe -m unittest test_voice test_setup_speech
# 36 tests: 35 passed, one intentional online skip
# From external-work:
..\.venv-ui\Scripts\python.exe -m unittest tests.test_runtime
# 18 passed
```

Existing cancellation, output drain, device-error cleanup, wake/clap, offline privacy, and warm-worker checks passed. These are isolated checks, not a measured live improvement. Pre-existing working-tree changes were preserved. No dependency, model, device setting or runtime process was changed.

## Next gate

Quit and relaunch LYA to load the changes. In a quiet local trial, wake her, wait for the invitation, ask “what time is it?”, and report the visible “You asked” text, approximate wait after finishing the question, and whether the output is crackling, cut off, or robotic. Then compare background noise after the quiet trial passes. Keep live weather and enrollment deferred. Bluetooth hands-free quality and other-speaker rejection remain unresolved; no hardware cause is claimed from this task.
