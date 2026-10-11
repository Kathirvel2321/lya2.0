# Registration expiry: stop, reverify, resume — 2026-10-09

The owner clarified that setup stopped after face verification with a phone-proof-expired message. Code confirms owner proof lasts five minutes and that the previous expiry path stopped capture and discarded the in-progress biometric profiles. A synthetic test reproduced that exact destructive restart path. This follow-up changes expiry handling only; it does not extend owner authority or lower recognition checks.

## Updated behavior

1. Expired phone proof stops the local capture child and its camera/microphone. No private action, profile save or further biometric capture is permitted under the expired proof.
2. Already validated completed samples can remain **only in RAM for three minutes** in the same open setup. No partial profile is written to disk. A complete three-view face group is retained; an incomplete face group restarts because the worker's turn-direction state cannot be restored safely. Individually completed voice samples are retained only with a complete face group.
3. LYA says that proof expired and asks **“continue with phone.”** The existing phone passkey signs a fresh challenge. This does not create another administrator or replace the passkey. The original owner ID and exact public credential must both match; the temporary resume deadline must still be valid.
4. The protected store rechecks that the signed owner is still current and that profiles were not separately saved/changed. The new five-minute session replaces the expired proof only after valid signed verification.
5. Capture resumes at the first missing voice sample after completed face views, without reopening the camera. If all six samples were already complete, fresh phone proof returns directly to final review with no worker/model/sensor startup. A partial face group begins its three views again.
6. Final **“save my profiles”** still requires current phone proof and the existing atomic three-face/three-voice, consent, consistency and encrypted-store checks. Nothing is committed automatically by re-verifying.

Closing/hiding/cancelling setup, exceeding the three-minute pause deadline, a mismatched owner/credential or another capture failure discards the temporary samples. This is recovery from **proof expiry**, not recovery of samples from a crashed app or an earlier discarded attempt. Reopening LYA cannot recover RAM that was already lost.

Old capture children must finish exiting before a replacement starts. Late stopped signals from an old child cannot restart online hearing during the new private capture. Online hearing remains stopped while biometric acquisition is active. During the phone-only pause, ordinary hearing can resume for the public “continue with phone” command, after the sensor worker closes. The worker's renewed capture lease is bounded by the newly signed proof; there is no bypass or unsigned extension of the old proof.

## What to do now

- Load the repair once by fully **Quit LYA from its tray**, then reopen the usual launcher. Development did not stop or restart your registration window. The previous attempt's already-discarded samples cannot be restored.
- Say **“register admin,”** continue with the **existing** phone passkey and follow the local profile guidance.
- If LYA reports expiry during this new attempt, keep the setup open and say **“continue with phone.”** Verify within three minutes. Completed face capture will then continue with voice, rather than repeating all enrollment steps.
- When all samples are complete, say **“save my profiles.”** If another specific error appears, report those exact words; do not assume it is still expiry.

Only this enrollment expiry path changed. Accepted camera presentation/preview rate, ordinary hearing, speaking voice, startup behavior, person permissions, models, API keys, private memory and sensitive-operation approval remain unchanged. Existing biometric consistency thresholds were not weakened. No new dependency was installed, and no registration account/store was reset.

## Evidence and limits

- `validation.json`: **165 isolated tests passed**, zero failures/errors/skips across visitor, profile, passkey, approval, desktop, legacy-retirement and brain suites. The reported after-face expiry regression failed before the repair and passed afterward.
- New UI tests cover signed same-owner renewal, changed owner or exact credential refusal, pause deadline/cancellation, partial voice continuation, final-review renewal without capture, incomplete face-group restart, old-worker exit barrier and ignored stale signals. Existing failure/no-partial-save/private-authority checks remain.
- An actual QProcess test uses the production six-step command loop with a synthetic capture class. It resumes at step three, completes three voice-only packets and never calls the camera branch. No real sensor/model/person is used in that test.
- `resumed-worker.json` / `check_resumed_worker.py`: the actual installed capture worker and existing models successfully loaded with synthetic completed-face vectors and `initial_step=3`, then cancelled. No capture command was sent. Ready/cancel took 11.266 s including model startup; this is not active-capture cancel latency. Resuming an unfinished voice stage reloads the existing worker/models; live wait time is not qualified.
- `source-check.json`: six-source syntax/whitespace and usual-launcher import pass; scoped `git diff --check` passed. `check_expiry.py` reuses the established fake-key/temp-store harness and writes only this new review directory. Normal host was needed for temporary-directory/Windows ACL checks; a sandbox-only fake child temp-file permission denial passed on the normal-host suite without weakening protections.
- No real owner data, protected runtime key/store, phone ceremony, camera/microphone recording, provider inference, upload, deployment or app restart was performed. Earlier capture/preview artifacts remain preserved; their generic expiry-discard behavior is superseded by this note.

Sources: `desktop/owner_setup.py`, `desktop/owner_biometrics.py`, `security/owner_capture.py`, `test_owner_profiles.py`.

Implemented and isolated-tested. The owner's actual iPhone renewal, camera/voice capture and final save still need live acceptance; these tests do not prove the entire real registration is complete.
