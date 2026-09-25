# Whole-project offline check sweep — 2026-09-24

Owner request: review the current work-flow and report what works, what is in
progress, what does not work and what needs improvement.

This file records the checks actually run in this session. It is evidence for
this date only. Nothing here is a claim about live providers, real cameras,
microphones, biometrics, the owner vault or any device other than this laptop.

## Method

Every suite below ran against the existing `.venv-ui` interpreter (Python 3.12)
with `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=desktop;.` and fake/absent
credentials. No live provider, camera, microphone, enrollment, vault write or
off-device transmission was performed. The temporary sweep script and raw log
used for this run were deleted after the filtered log was saved as
`sweep-log.txt` in this folder.

Suites deliberately **not** run, with reasons:

- `security_test.py` — writes an audit fact into the real encrypted memory store
  and the real action log. Not isolated.
- `test_security_fixes.py` — corrupts and restores the real
  `security/escalation_attempts.lya` counter and calls module self-checks that
  touch real security stores.
- `crash_test.py`, `crash_test2.py` — unstaged ad-hoc scripts of unknown scope.
- Any provider/live check — no network or paid/free-quota provider call was made.

## Results

| Suite | Tests run | Result |
|---|---|---|
| `check-t01.cmd` (T01 baseline: router, oracle, provider setup, brain workflow, UI, experience) | 14 + 8 + 3 + 37 + 16 + 22 = 100 | PASS |
| `check-t02.cmd` adds `test_t02.py` | 15 | PASS |
| `check-t03.cmd` adds `test_answer_verification.py`, `test_research_adapter.py` | 8 + 7 | PASS |
| `check-t04.cmd` adds `test_approval.py`, `test_registration.py`, `test_registration_ui.py` | 3 + 12 + 16 | PASS |
| `check-storage-recovery.cmd` (`test_recovery`, `test_brain_workflow`, `test_approval`, `test_recovery_ui`) | 12 + 37 + 3 + 10 | PASS |
| `test_foundations.py` | 14 | PASS |
| `test_guardian_governor.py` | 12 | PASS |
| `test_skills.py` | 17 | PASS |
| `test_identity.py` | 5 | PASS (mock faces only) |
| `test_mind.py` | 6 | PASS |
| `test_storage.py` | 8 | PASS |
| `test_search_index.py` | 3 | PASS |
| `test_vision.py` | 5 | PASS (fake camera) |
| `test_camera_preview.py` | 4 | PASS |
| `test_voice.py` | 11 (1 skipped) | PASS |
| `test_setup_speech.py` | 6 | PASS |
| `test_vault_recovery.py` | 4 | PASS |
| `test_liveness.py` | 4 assertions | PASS (fail-closed) |
| `test_escalation.py` | 12 | PASS (temp-redirected stores) |
| `test_auth_wall.py` | 4 | PASS |
| `test_native_ui.py` | 1 script | PASS (28 event-loop ticks) |
| **`test_synthesis.py`** | **7** | **FAILED — 2 failures** |

Totals: 346 test executions, 344 passed, 2 failed. `test_brain_workflow.py`
(37) and `test_approval.py` (3) each ran twice because the T-chain and the
storage-recovery script both include them.

## The only failure: `test_synthesis.py`

Both failures are in the *test file*, not a crash in the product:

- `test_missing_english_model_uses_local_female_fallback` — patches
  `audio.synthesis.Renderer().audio` to raise `FileNotFoundError` and asserts
  `sapi()` is called. `speak()` now consumes `Renderer.utterances()` (which
  carries per-phrase captions) and no longer falls back to SAPI in the `neural`
  engine path.
- `test_partial_failure_never_repeats_audio` — same cause: it stubs `.audio`,
  so the generator is never reached and no `RuntimeError` is raised.

Why the mock never fires: `Renderer` is replaced by a `MagicMock`, and
`MagicMock.__iter__` yields an empty iterator, so `speak()` completes normally.

Two honest readings, and a decision is needed:

1. **Stale test** — the speech pipeline moved on (neural `utterances()` +
   bounded prefetch) and the test was not updated. Fix the tests.
2. **Lost resilience** — the earlier design fell back to the installed Windows
   SAPI female voice when the English model was missing. The current code raises
   `RuntimeError('Local voice failed')` instead. Decide whether that fallback is
   still required, then either restore it or record the removal as intended.

## Environment findings (this machine, this session)

Dependency probe of `.venv-ui`:

| Module | Present | Effect if absent |
|---|---|---|
| `PySide6`, `cryptography`, `numpy`, `pywin32` (`win32crypt`) | yes | new crystal desktop and encrypted stores run |
| `cv2` (opencv), `onnxruntime` | yes | camera capture and ONNX inference available |
| `sounddevice`, `pyttsx3`, `vosk` | yes | capture, local SAPI speech, offline ASR available |
| `requests` | yes | provider/research HTTP clients available |
| **`torch`** | **no** | anti-spoofing stack absent → `security/liveness.face_liveness()` returns *denied* |
| **`insightface`** | **no** | no ArcFace embedding → real owner face identification cannot run |
| **`speech_recognition`** | **no** | default cloud transcription in `audio/voice.py` cannot run |
| **`pyautogui`** | **no** | `skills/device.py` volume/screenshot fall back or fail |
| `resemblyzer`, `flask` | no | legacy voiceprint path off; the phone gateway uses `http.server`, not Flask, so approval is unaffected |

Assets present on disk: `models/vision/nanodet-int8.onnx`,
`models/vision/yunet-2026may.onnx`, `models/voice/` (Kokoro plus English and
Tamil Piper voices), `models/local/qwen2.5-1.5b…gguf` and `qwen3-4b…gguf`.

Local inference endpoints: `127.0.0.1:8080` (the loopback llama.cpp server that
`brain/workflow.LocalModel` requires) and `127.0.0.1:11434` (Ollama, used by
`brain/mind`) were both **closed**. Private/offline inference is therefore
unavailable right now.

Observed fails-closed chains (working as designed, but they are real blocks):

- Missing anti-spoof model → `test_liveness` prints
  `liveness model unavailable; verification denied` → every phone approval that
  requires an owner face check is denied → private memory, real folder browsing,
  private `using my memory` answers, reminders, screenshots and persisted theme
  changes stay unreachable end-to-end until enrollment is set up.
- Missing `insightface` → `test_identity` passes only with injected fake
  vectors; there is no real owner identity binding today.
- Closed loopback model server → `private mode` and verified-personal inference
  fail closed with no cloud fallback (intended).

## Secret and repository hygiene

- `git check-ignore` confirms `.env`, `.venv-ui/`, `oracle_known_hosts.local`,
  `*.key`, `security/.lya_key` and `brain/*.db.lya` are ignored.
- `git ls-files` matched no `.env`, `*.key`, `*.lya`, `*.wav`, `*.npy` or `*.db`
  path, so no credential, key or biometric artefact is tracked.
- `git status --porcelain` reports **144 changed/untracked paths** against the
  single commit `8671be1 "lya projectt"`. The working tree is effectively
  uncommitted, which is the largest practical risk to this work-flow: there is
  no usable rollback point for the last several days of changes.

## Limits of this evidence

- Offscreen Qt and fake sensors only; no on-screen visual approval.
- No live provider, model, camera, microphone, phone or biometric accuracy test.
- `test_native_ui.py` (Tk) passed here, which contradicts the older note that Tk
  QA is environment-blocked; that older note is now dated, not proof of failure.
- Timing figures inside the suites are smoke measurements, not battery or
  sustained-load budgets.

## Next steps

1. Decide the `audio/synthesis.py` fallback question, then fix the two tests or
   restore the fallback — whichever is the smaller correct change.
2. Restore a rollback point: commit the current working tree, or split it into
   reviewable commits.
3. Unblock the identity chain in the recorded order: owner-approved enrollment
   setup, then `insightface` plus anti-spoof dependencies, then a real phone
   approval rehearsal. Enrollment stays deferred until the owner asks for it.
4. Consolidate the three parallel speech stacks (`audio/voice.py` pyttsx3 for the
   Tk runtime, `audio/synthesis.py` Kokoro, `external-work/alya_voice` Piper for
   the Qt desktop) onto one documented owner.
5. Quarantine or wire the unused legacy `skills/` modules so the permission
   boundary matches the code that actually ships.

