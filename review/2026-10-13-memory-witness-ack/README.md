# Witness-confirmed memory operations — 13 October 2026

The owner authorized connecting the isolated memory authority to its latest-state witness. The optional witnessed mode in [memory_authority.py](../../brain/memory_authority.py) now waits for the witness commit before returning a write, takeover, restore or activation result. Reads also require the exact witnessed checkpoint and writer generation, including reads that perform expiry cleanup. The standalone witness's locked operations in [memory_custody.py](../../brain/memory_custody.py) are reused rather than opening a second connection during coordination.

## Explicit cutover

Existing authority schema 2 keeps its previous local-only behavior. For generated fake stores only, bootstrap that authority, register its exact checkpoint/generation and key-capsule digest in an existing `SyntheticWitness`, then reopen `SyntheticAuthority(..., witness=witness)` and call `bind_witness(lineage, keys_digest, approved=True)`. Binding checks the canonical encrypted source and exact registered witness, then atomically changes the authority schema to 3 and persists the custody digest and transition record. It is an explicit one-time cutover, not enrollment, key rotation or an automatic migration. A bound authority cannot reopen without its witness; even an older already-open unbound authority object is refused after cutover. Fresh construction with a witness and missing authority state is rejected.

## Commit order and failures

1. Lock the existing witness, then the authority catalogue. Require the exact current witness, capsule digest and journaled authority checkpoint/generation.
2. Run the existing authority operation. Its verified encrypted snapshot, pointer/generation and previous/next witness states commit together in the authority catalogue.
3. Advance the witness using that same held witness transaction and commit it before releasing success. Cancellation is checked around the commit boundaries; authenticated turns are rechecked before releasing conversation or activation replies.

The last transition stays in the trusted catalogue as metadata only. It contains no bearer capability, raw key, owner proof or conversation content. `witness_confirmed=True` on witnessed replies means the configured witness committed that operation; it does not mean backup objects or keys are independently hosted.

| Failure | Behavior |
| --- | --- |
| Before the authority commit | Authority and witness retain their old state; provisional published objects are not selected. |
| Authority committed, witness did not | No success is returned. Reads, writes, takeover, restore and activation are blocked by the mismatch. Explicit approved `reconcile_witness` verifies the latest bundle and durable local transition before advancing the witness. |
| Witness committed, reply lost | Matching receipt retries do not create another write. Reconciliation is idempotent and returns content-free state only. A lost takeover/activation capability requires a separately approved new takeover; the token is never reconstructed or replayed. |
| Source rollback, divergent witness or changed capsule digest | Reconciliation fails closed; it cannot republish stale state or silently rotate keys. |
| Missing witness, lineage, binding or schema | No trust state is recreated and no older backup is selected. |
| Concurrent witness advancement during recovery | The local witness writer lock spans check, restore/activation and both commits. A competing stale advancement fails after the lock is released. |

A failed restore can leave an encrypted quarantine file. Reconcile its committed generation before explicit activation; do not interpret a file's existence as a successful recovery or blindly overwrite it on retry. Existing zero-binding/zero-resumed-job and pre-existing-owner checks remain in effect.

## Validation and reproduction

[test_memory_witness_ack.py](../../test_memory_witness_ack.py) adds 18 portable fake-data checks: explicit cutover, reopening without trust, save/correct/forget/expiry, both commit failures, lost replies, generation-only takeover, restore and activation, source rollback, missing/corrupt trust, cancellation, identity revocation, simultaneous writers, recovery versus witness advancement, and actual process death before/between/after commits.

The initial sandbox run could not perform the existing atomic hard-link publication. Its [log](sandbox-tests.txt) and [result](sandbox-validation.json) are preserved. With the required filesystem access, the [targeted run](targeted-validation.json) passed all 18 checks. The combined run passed **75 checks**, zero failures/errors/skips: 18 new cases plus 57 existing authority/reactivation/custody/storage regressions. Results are in [validation.json](validation.json) and [tests.txt](tests.txt); [static-validation.json](static-validation.json) records source preservation, parsing and documentation checks. Older evidence folders were not overwritten. This runner rejects skipped checks and keeps generated fake keys/stores in a temporary workspace fixture directory.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-13-memory-witness-ack/check.py
```

For the owner's existing Ubuntu lab, refresh the two changed modules and copy the new test, preserving previous copies as numbered backups:

```bash
cd ~/lya-lab
source .venv/bin/activate
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src"/brain/{memory_authority,memory_custody}.py brain/
cp --backup=numbered "$src/test_memory_witness_ack.py" .
python -m unittest -v test_memory_custody test_qualification test_memory_witness_ack
```

That portable selection contains 38 checks. The owner subsequently supplied Ubuntu WSL output showing **all 38 passed**, including all 18 new acknowledgement cases. See [reported validation](wsl-user-reported-validation.json) and [sanitized case results](wsl-user-reported-tests.txt). This was not independently rerun by the assistant, and the lab source hashes were not independently measured. The pre-WSL static report retains its original observation; this later result supplements it. Oracle has not run the new revision; earlier Oracle results apply to earlier source. No Linux settings, package installations, Oracle staging or service changes were performed for this change.

## Remaining boundary

This is coordination across two local SQLite stores in a fake-data prototype. The witness lock is not an implemented network protocol, lease or independently hosted service. Both stores and encrypted objects can still be lost together; whole-witness rollback remains outside protection. Raw files/repository access is outside the authority API. Retention/orphan cleanup, physical erasure, disk/admission/throughput budgets and power-loss durability remain unqualified. The tests simulate process death and database/commit failures, not power failure.

Next: design the authenticated independent witness/backup placement and its serialized service protocol. Keep real password-manager setup, owner/device acceptance and production memory activation separate. Accepted desktop/mobile/voice/authentication paths are not connected to this prototype.
