# B2 fake-data upload, readback and recovery — 2026-10-17

Status: **approved B2 upload, actual remote readback and fresh-process record recovery passed**. The owner completed browser reauthentication. Exactly the three prepared ciphertext artifacts were uploaded to the private lab destination and downloaded using the object's browser download controls. All SHA-256 hashes and byte lengths match the preparation evidence. The original synthetic source/catalogue/witness fixture remains absent. No application key, real memory, real recovery credential or Google Drive content was used. Object Lock remains disabled; this is a transfer drill, not retention qualification. Account identifiers and live metadata are not copied into this report.

## Prepared evidence

[prepare.py](prepare.py) reuses the reviewed `RecoveryPackChecks` fixture and existing recovery-pack APIs. It has no network client or account credentials and does not read real LYA stores. It creates generated fake keys and synthetic memories, stages exactly `backup.enc`, `checkpoint.enc` and `keys.enc`, and destroys the original source/catalogue/witness fixture before a fresh child restores the pack locally.

[prepared.json](prepared.json) records the three ciphertext hashes and sizes, total **5,395 bytes**, source digests and the successful fresh-process assertions. Correction revision survives; forgotten and expired data are suppressed; the old binding is denied; the restored database is encrypted/quarantined, with zero active bindings and zero resumed jobs. Explicit synthetic/approval flags and the existing eight-MiB limit remain in force. Raw keys and record bodies are not printed or included in the report.

Disposable local files live under this folder's ignored `.fake-local/` directory. Only the three files inside the reported `upload_folder` are proposed for upload. `local-only.json`, the locally restored database and independent fake trust/unlock inputs stay outside that folder. This is a convenience for a disposable fake-data drill, not protected production key custody. The prepared JSON contains local fixture paths, not keys. `prepare.py` refuses to replace an existing preparation report.

The initial Windows sandbox run could not open SQLCipher storage in its temporary path. A workspace-local retry then hit a blocked hard-link publication. The scoped reviewed run outside that sandbox succeeded, without network/account access. The earlier blocked attempts are not passes. No dependency or runtime-source changes were needed. The ignore rule covers only this drill's local fake fixtures.

## Transfer proposal at preparation time

The exact proposal is to upload only those three encrypted fake-data files into the private lab destination through the existing signed-in browser, then download and compare all three byte hashes before running the same quarantined restore checks on downloaded bytes. No application key is needed for this first browser drill. No real memories, Google Drive files, unlock key, independent pins or local-only test input is to be uploaded.

The browser stalled twice while opening/recovering the bucket's upload view. No file chooser was populated or upload submitted. Exact upload/download approval was requested and remains pending at preparation time. Do not infer approval from the bucket's existence or a provider's welcome text.

After approval and browser recovery, verify the current destination, upload exactly the prepared files, confirm provider completion, download the actual remote objects and verify byte identity plus fresh-process recovery. Preserve a content-free result distinguishing local preparation, remote readback and record-only quarantine. Any uploaded objects remain until separately authorized cleanup; no permanent deletion is included in this proposal.

This drill does not test a restricted uploader credential, permission denials, retention locks, independent trust/key/catalogue survival, full authority recovery, runtime integration or billing enforcement. Browser-mediated same-machine roundtrip is not clean-machine disaster recovery, even if remote byte readback passes. The independent witness and real password-manager setup remain open.

See the [storage comparison](../2026-10-17-memory-storage-choice/README.md) and [recovery trust guide](../../docs/guides/LYA_MEMORY_RECOVERY_PACK.md). [Static checks](static-validation.json) verify the local preparation inventory, source preservation and documentation links; no cloud result is implied.

## Approved transfer and verifier readiness

The owner explicitly approved uploading only the prepared three ciphertext files, totalling 5,395 bytes, to the named private lab bucket and downloading them for recovery verification. This does not authorize a new application credential, other uploads, Google Drive transfers, deletion or private memory use. The approval remains valid while the browser session is restored; do not ask for it again for the unchanged scope.

After reconnection, the upload link navigated to sign-in. The owner must complete reauthentication in their browser; no password or verification code is requested in chat. No upload file chooser has been populated and no upload submitted.

[verify.py](verify.py) takes a separate readback folder and a new evidence name. It checks the pinned preparation source digests, refuses the original upload folder, uses the existing authenticated pack inspection/staging helpers, matches the staged bytes to the preparation hashes, and invokes the existing fresh-process restore worker with independently retained fake inputs. It writes no success report on rejection and refuses an existing report. Local inputs and restored data remain under the ignored fake-fixture directory. It has no network client or account credentials.

Four verifier checks passed: original-folder refusal, damaged-ciphertext refusal, fresh-process verification of a separately copied local pack, and preservation of existing evidence. [Local positive self-check](local-verifier-self-check.json) and [check summary](verifier-checks.json) are **local-only evidence**. The scoped positive run outside the Windows sandbox allowed the existing atomic hard-link operations; no network was involved. A supplied folder does not prove cloud origin, so every verifier report explicitly records `remote_provenance_established_by_script: false`. Actual cloud upload/download must be established separately by browser evidence before a remote result is claimed.

No whole-suite rerun, remote byte readback, independent-host restore, billing enforcement or automated credential acceptance is claimed. [Post-approval static checks](static-validation-after-approval.json) preserve this distinction and the existing source inventory.

## Completed approved browser roundtrip

The owner completed reauthentication after the session expired. Rechecked the private empty destination, then selected only the approved `backup.enc`, `checkpoint.enc` and `keys.enc` paths in the browser file chooser. The file browser displayed those three objects after upload; each details view showed private storage and SSE-B2 encryption. Browser download events supplied actual local download paths for all three objects. No cookies, session token, password, verification code or API key was extracted.

Read each downloaded object with its exact prepared byte limit, compared SHA-256 and length, and copied only matching bytes into a new local readback folder. [b2-readback-verification.json](b2-readback-verification.json) records the successful verifier invocation against that folder. The child re-created an encrypted quarantined database from those bytes, preserved the correction, suppressed forgotten/expired content, denied the old binding and left zero active bindings and resumed jobs. Its unlock and independent fake pins remained local throughout.

[cloud-roundtrip.json](cloud-roundtrip.json) combines content-free browser observations with the verifier result. The verifier still correctly declares that it cannot establish cloud origin by itself; remote provenance comes from the separate observed browser upload/download workflow, not from merely passing a local folder. Visual proof remains in the ignored local fixture directory and is shown to the owner, outside the plaintext ledger and tracked evidence. Live bucket/object identifiers and signed-in account details are omitted from tracked reports.

All three cloud test objects and local fake fixture/downloads remain for inspection. No deletion was requested or performed. No automatic uploader, restricted application credential, retention rule, real key custody, trusted authority/catalogue rebuild, independently surviving witness, clean-machine recovery or production integration was created. Remote storage was exercised; recovery computation and fake trust/key inputs remained on this laptop. Existing runtime sources and tests remain unchanged. [Final static checks](static-validation-completed.json) verify artifact hashes, the preceding source inventory and documentation references. Next: qualify restricted automated access and independently surviving key/trust/catalogue custody before private use; those require their own concrete scope and access setup.
