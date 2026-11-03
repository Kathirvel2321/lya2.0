# Memory recovery pack — synthetic foundation

This is an isolated fake-data transport helper in [memory_recovery_pack.py](../../brain/memory_recovery_pack.py). It packages existing encrypted artifacts for a later approved independent destination. No provider, account, scheduler or production caller is connected. It does not create real recovery keys or configure a password manager.

## What must survive

| Material | Job | Boundary |
| --- | --- | --- |
| `backup.enc` | Encrypted complete record snapshot and idempotent memory receipts. | Existing recovery format; no live database, binding, writer token or job queue is copied. |
| `checkpoint.enc` | Encrypted exact record heads, revisions and deletion state. | Its digest must match the independently trusted latest checkpoint. |
| `keys.enc` | Existing sealed storage/recovery-key capsule. | The independent capsule digest and separate unlock key are required to open it. |
| Fresh independent `RecoveryPins` | Exact checkpoint/writer observation, capsule digest and acknowledged backup digest. | Keep outside the pack's trust boundary. Never accept a pin supplied only by the same untrusted backup copy. |
| Unlock key | Opens the sealed capsule. | Keep outside the backup/witness host's failure domain; never put it in pack files, command arguments, chat or the project ledger. |
| Protected authority catalogue, owner mappings and surviving latest-state service | Full authority/writer continuity and later approved reactivation. | Not exported by this helper. Their independent protected survival and recovery remain a separate requirement. |

The two hashes for backup/checkpoint and the capsule hash are fingerprints of exact encrypted bytes. They detect replacement only when the expected fingerprints come from a separately trusted source. A backup cannot establish its own freshness. Replacing both the pack and its supposed independent pins with old copies is not detected by this local helper.

`RecoveryPins.state` comes from an independently trusted `WitnessState`. Its backup digest must come from the corresponding verified catalogue acknowledgement. A writer-epoch-only change can leave the same checkpoint/artifacts usable, but the surviving authority must still fence old writers. The pack reader does not contact a live witness, establish a physical failure domain or enforce writer fencing.

## Stage and inspect

`stage_pack()` takes the existing backup, checkpoint and capsule paths, an explicit **new** destination directory, independently obtained pins, a generated fake unlock key and exact `synthetic_only=True, approved=True` flags. It:

1. Bounds the complete encrypted input to eight MiB and validates exact fingerprints.
2. Opens the existing capsule with its independent digest and verifies the existing authenticated recovery formats.
3. Requires a complete backup/checkpoint pair at the same acknowledged sequence, with matching owners, record heads and revisions. An older partial snapshot is refused even when the core recovery layer could suppress unavailable records.
4. Publishes only the three fixed files, using the existing per-file atomic create operation.
5. Reads back and verifies the destination before returning a content-free transfer acknowledgement.

It does not overwrite an existing destination. Interrupted copies may leave a partial directory without an acknowledgement. Keep the failed attempt for inspection or remove only that owned failed fixture explicitly; start another attempt in a new directory. Directory presence alone is not successful transfer. No recursive copying, archive extraction, new backup format or plaintext manifest is used.

`inspect_pack()` requires exactly those three names and the same explicit trust/approval inputs. Missing files, extra files, links, oversized data, corruption, a changed capsule or stale content against fresh pins fail closed. Existing unlink/junction protections are reused. A provider's upload-success message is not a substitute for destination readback verification.

## Restore

`restore_pack()` revalidates the pack and calls the existing encrypted recovery code with the capsule's storage key, trusted checkpoint and exact acknowledged backup digest. There is no plaintext fallback when SQLCipher is unavailable. It publishes to a new destination.

Obtain the required independent pins again before a recovery decision. An old successful transfer receipt is not evidence of today's latest state. The helper cannot refresh that observation on the caller's behalf.

Existing restore rules remain:

- Corrections survive; forgotten content and records expired at restore time remain suppressed.
- The recovered database is quarantined, with zero active bindings and zero resumed jobs.
- Old device access, writer grants and pending external actions are not reconstructed.
- Cancellation and an existing output path refuse publication.

This is **record-only recovery**. It does not bootstrap a new trusted authority from an untrusted pack, reconnect a phone, map a real owner, resume work or reactivate writers. Use the separately qualified authority restore/reactivation path with surviving protected metadata and fresh owner proof for that later step.

## Qualification and next decision

[The dated report](../../review/2026-10-17-memory-recovery-pack/README.md) records staging, refusal and fresh-process drills with fake data. The source fixture, catalogue and local witness are deleted before the child reconstructs an encrypted quarantined database using only copied artifacts and separately supplied fake trust/key inputs. These folders and processes share one physical host. This is not a clean-machine, independent-host or power-loss test.

Before real use, verify destination allowance and survival scope, establish protected custody, protect the catalogue/latest-state service, qualify durable publication/readback/quotas, and rehearse recovery on the actual supported host. B2 passed the [browser fake-data roundtrip](../../review/2026-10-17-memory-b2-transfer/README.md) and the later [native finite-worker fake-data drill](../../review/2026-10-21-memory-b2-pilot/README.md). The owner selected [Bitwarden Free plus an offline copy](LYA_MEMORY_KEY_CUSTODY.md) and reports completing account/harmless custody checks; real LYA unlock-key enrollment and independent latest-state/catalogue survival remain pending. No real-memory backup, scheduling or working real-key password-manager integration is claimed. Do not promote disposable test keys or store an unlock key next to its capsule. Face anti-spoofing remains deferred; accepted assistant behavior is unchanged.

## Portable encrypted trust record — 2026-10-21

The [native B2 fake-data roundtrip](../../review/2026-10-21-memory-b2-pilot/README.md) subsequently passed. The [portable trust helper and source-loss drill](../../review/2026-10-21-memory-recovery-trust/README.md) now support carrying `RecoveryPins` in a separate encrypted file, without changing the three-file pack. `seal_trust(destination, pins, unlock_key, synthetic_only=True, approved=True)` returns its fingerprint after readback. `open_trust(path, unlock_key, trusted_digest=current_independent_fingerprint, synthetic_only=True, approved=True)` returns the validated pins for existing pack operations. Use only generated fake keys in this foundation; no real vault/offline enrollment is enabled.

Keep the trust record outside the pack and keep the unlock key separately protected. The current fingerprint must survive through an independently trusted channel. Neither the encrypted trust record nor an old successful transfer receipt can prove that its fingerprint is today's latest. Wrong/missing fingerprints refuse recovery; jointly rolling back the trust record and its supplied fingerprint remains outside local detection. Simulated separate folders/source deletion and a fresh process do not prove actual independent storage or complete authority recovery.

## Separate latest-publication guard — 2026-10-21

The new isolated [latest-state guard](../../review/2026-10-21-memory-recovery-latest/README.md) binds pins and trust fingerprint in a separately trusted existing store. Explicit first-time `create()` and initial `begin(None, head)` are bootstrap operations; recovery must never create replacement trust when that store is missing. For updates, reserve `begin(previous_head, candidate_head)` before publishing candidate files. This records durable pending state and blocks recovery. Confirm only with `finish(candidate_head, pack_folder, trust_path, unlock_key)` after complete readback; exact interrupted/committed-reply-loss retries are idempotent. Calls that write or restore require `approved=True`; the store requires explicit `synthetic_only=True` at creation/opening.

Use `restore(lineage, pack_folder, trust_path, new_destination, unlock_key, approved=True)` for latest-gated fake recovery. It obtains current expected pins/fingerprint from the separate store, refuses pending/missing trust and rejects replayed old pack/trust pairs while that store survives current. It retains encrypted quarantine and zero resumed jobs/bindings. Do not bypass the gate by choosing a fingerprint from an older receipt.

This is a local simulation of the publication boundary. The separate store is still plaintext metadata on the same physical laptop, and the actual memory authority acknowledgement path is not connected to it. Its safety covers its confirmed publications, not source changes acknowledged without consulting it. Rolling back the latest store as well remains outside its protection; real independent placement, protected catalogue/identity recovery and physical failure acceptance are pending.

## Portable cold-host preparation — 2026-10-21

The [code-only recovery package](../../review/2026-10-21-memory-recovery-host/README.md) prepares a future second-host fake-data drill. Its ZIP contains only nine Python source members, with separately recorded inventory/hash; backup/trust/latest-state/unlock material and native dependencies are excluded. The isolated entry point accepts bounded exact fake-only JSON through stdin, obtains current trust from the separately supplied existing latest-state store, invokes the current gate and leaves recovered memory encrypted/quarantined with zero active bindings/jobs. It refuses loose project-module imports and missing SQLCipher, with no plaintext fallback or secret/error echo.

Use only a separately reviewed/verified code archive with compatible qualified runtime dependencies. Keep the fake unlock outside commands and artifacts, and keep latest-state custody separate from rollbackable backup copies. The actual second-host/runtime choice, independent data/key transfer and any deployment remain pending; local Windows/WSL process checks do not establish a physical failure domain or production readiness.

## Opt-in publication-confirmed source — 2026-10-21

[SyntheticPublicationAuthority](../../review/2026-10-21-memory-publication-ack/README.md) adds a local fake-only acknowledgement path. Explicitly bind one previously bootstrapped unwitnessed authority to its existing exact latest head/trust record. Schema 5 prevents older authority code from bypassing the binding; the default authority/runtime is unchanged. The new mode reserves recovery before source mutation, journals the committed target with the source pointer, verifies/publishes the pack and trust, confirms the separate latest head, then returns success. Its opaque reservation is refused by the unchanged cold-recovery package until safely resolved.

An interrupted call can have committed its source even though no success reply arrived. Approved `reconcile_publication()` proves commit/rollback under the source writer lock, completes only the journaled publication and returns metadata; it never replays content or returns a writer token. Then retry an ordinary memory request using the same request ID and a fresh authenticated turn. Missing/divergent source or custody must refuse; never recreate trust or infer rollback from an exception.

This remains a local generated-data integration. Existing TLS/network witness binding is separate, and real assistant startup/storage/enrollment is untouched. Independently surviving protected catalogue/key/latest-state custody, remote fencing and the eventual production cutover still require qualification.

## Pre-existing fake-owner reactivation — 2026-10-21

The optional publication mode now reuses the existing `activate_restored()` validation and encrypted recovery implementation; see the [qualification report](../../review/2026-10-21-memory-owner/README.md). It requires a surviving trusted authority catalogue and owner mapping, the exact acknowledged quarantine, current anchor/epoch, literal approval and fresh verification of an already registered fake owner. One binding is activated, zero jobs resume, and a new writer generation is returned only after publication confirmation and another fresh-turn/cancellation check. No new owner enrollment is included.

If activation raises, explicitly reconcile publication before continuing. A rollback keeps recovery pending and permits a fresh activation attempt. A committed activation consumes recovery even when the reply or grant was lost: reconciliation returns metadata only, and repeating activation must refuse. A separately approved writer takeover can issue a later generation after reconciliation; there is no token recovery or automatic replay. A refusal after entering a transaction can also leave a reservation requiring reconciliation.

Record-only recovery from the portable code archive still produces zero bindings/jobs, including for a pack published after activation. It cannot bootstrap a trusted authority or replace fresh owner proof. Real independent custody, owner/device acceptance and production connection remain pending.

## Complete fake-authority transfer — qualified 2026-10-22

The [full-authority transfer helper and requalified evidence](../../review/2026-10-21-oracle-recovery/README.md) additionally preserve the catalogue and pre-existing fake-owner mapping in a bounded encrypted envelope. Restore requires the exact separately trusted envelope fingerprint, fake unlock and existing current latest state; it fences old writers and publishes recovery before returning a zero-binding/job quarantine. Explicit incomplete-recovery reconciliation preserves failed candidates; fresh owner verification is still required for activation. This helper remains fake-only and has no production caller.

Eight transfer cases pass in fresh full Windows/Ubuntu runs. A preserved earlier Oracle result covers the same cases plus cross-host recovery, but its latest store was bootstrapped from the incoming drill packet and removed afterwards. It does not prove independently surviving custody. Envelope capture is explicit, not automatically included in every memory acknowledgement; a newer latest state can correctly render an older envelope unusable. Use the [next placement/acknowledgement qualification plan](../../review/2026-10-21-oracle-recovery/placement-plan.md) before independent custody or private-use claims. Existing source/defaults and real-key enrollment remain unchanged.
