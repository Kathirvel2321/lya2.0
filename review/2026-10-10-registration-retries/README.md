# Registration sample retries — 2026-10-10

The owner reports repeated registration restarts, poor face capture and repeated phone connections. Source tracing found that every sample-quality failure terminated the child, cleared completed samples and routed Retry to phone verification. The previous repair retained progress only for proof expiry. No live sensor trace was collected, so the precise physical cause of this owner's failed face sample remains unproven.

## Repair

- Recoverable face alignment/lighting/sharpness/missing-face/multiple-face and voice silence/loudness/clipping/short-speech/overflow failures now close the current sensor acquisition, keep validated samples in the same worker's RAM, speak corrective guidance and retry only the unfinished sample. The five-minute signed phone proof must still be valid. No model reload or new phone ceremony occurs for these retries.
- The parent now acknowledges each validated, consistent sample. The child cannot advance to the next step or finish before that acknowledgement. A face/voice consistency mismatch rejects only the new vector, then retakes the same sample against the retained references. Even the last sample must pass before final review. Thresholds were not lowered.
- During active face acquisition, fixed, local hints report the actual failing quality gate or ask the owner to hold still. The existing camera panel, detector observations, 640×480 preview and up-to-ten-FPS work budget are retained. The quality labels do not claim liveness, depth or identity authority.
- A failed attempt releases the camera/voice stream before corrective narration. Online hearing stays stopped through private capture and retries. Cancellation, lease loss, expiry, invalid packets/vectors, device failure, processing timeout and model failure retain their existing stop/deny behavior. No raw media is saved or sent to cloud ASR.
- Proof expiry still stops capture and uses the previous three-minute RAM pause plus a fresh same-owner/exact-credential phone proof. A partial face group restarts on that renewal because its turn state is not restored; completed three-view face groups and completed voice samples resume. Closing setup or quitting loses unfinished RAM samples. Nothing is saved until explicit final confirmation and the existing atomic encrypted-store checks.

## Load and use

1. Fully **Quit LYA from its tray**, then reopen the usual launcher once to load the repair. Development did not stop or restart the running app. Already-discarded samples cannot be recovered.
2. Say **register admin** and verify using the **existing** phone passkey. Do not create or reset the administrator.
3. Consent to the local profiles. Face views proceed front, slightly to either side, then the other side. Follow the live quality hint, with one face visible and light from the front. Each acquisition remains bounded to 15 seconds; a recoverable failure repeats only that view after guidance.
4. For each voice sample, wait until the guidance ends, speak naturally, then pause. Quality rejection repeats only that voice sample; previous samples remain in RAM.
5. If phone proof expires, keep setup open and say **continue with phone** within three minutes. Verify the same phone credential to resume retained progress.
6. At final review say **save my profiles**. Live completion is established only after that encrypted save succeeds.

## Checks and limits

- `validation.json`: final 169 isolated regressions pass, zero failures/errors/skips. Fake keys and temporary encrypted stores; no real enrollment. Covers retry UI, unchanged proof deadline, cancellation, quality gate hints/rejections, encrypted atomic save and existing private-action authority.
- `validation-host-abort.json`: a preceding run passed the registration checks but one unchanged local HTTP-boundary test ended with Windows error 10053. The complete unchanged suite passed on retry; the earlier failure summary is retained rather than hidden. Earlier 168/169-test batches also passed before the final-sample mismatch check was expanded.
- A real QProcess using the production child command loop with a synthetic capture class exercises quality retries and inconsistent middle/final face and voice samples. It keeps the same child, rejects the bad vectors, accepts all six in order and finishes only after the parent's validation. Voice-only expiry continuation remains covered.
- `model-check.json`: installed models, a public OpenCV image and existing synthetic greeting through fake devices produced 128d/256d vectors, released the camera and closed the stream. Cold model load 15.109 s; total 18.016 s; peak 445.2 MiB; 94.881% of one CPU core during this short fixture run. It overlapped isolated testing and is not a controlled benchmark, live owner accuracy, full-app pressure or smoothness qualification. The fixture script's date is historical; this execution occurred on 2026-10-10.
- `source-check.json`: eight-source syntax/whitespace and usual-launcher imports pass. No new dependency. The first check command used the sensor-worker environment, which lacks the Windows store dependency; the suite was then run with the usual launcher environment. Sandbox temp ACL checks failed; normal-host fake-store checks passed without changing production permissions.
- Real phone/camera/microphone registration, live frame rate and final owner save remain unverified. Fatal device/protocol/process failures still discard unfinished profiles. No real owner key/store/profile was inspected or changed; no sensors, real phone proof, browser, provider inference/upload, app restart or deployment occurred. Ordinary hearing, Amy voice, main interface, permissions, keys, memory and archive behavior were not changed.

Sources: `desktop/owner_setup.py`, `desktop/owner_biometrics.py`, `desktop/owner_scan.py`, `security/owner_capture.py`, `security/owner_profiles.py`, `test_owner_profiles.py`.
Runnable checks: `check_retries.py` with `.venv-asr/Scripts/python.exe` (normal Windows permissions for temporary ACL checks); `check_sources.py` with that same interpreter. Earlier task artifacts remain preserved. This note supersedes earlier instructions only for recoverable quality/mismatch failures.
