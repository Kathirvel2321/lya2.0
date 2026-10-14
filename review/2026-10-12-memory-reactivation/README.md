# Verified recovery and owner reactivation — 12 October 2026

Continues the owner's “next” request after canonical authority/writer fencing.
This completes the next **isolated fake-data cutover**, reusing the existing
SQLCipher candidate and signed fake-owner fixtures. No real key store, device
enrollment, external destination, production path or deployment is connected.

## Implemented contract

[memory_authority.py](../../brain/memory_authority.py) now uses authority schema 2.
Schema 1 is refused byte-preserving, without migration. Memory database schema 2
and repository schema 2 are unchanged. Existing registered fake identities are
captured at bootstrap as principal fingerprints mapped to stable owner UUIDs in
the trusted metadata catalogue; raw principal values, keys and writer tokens are
not persisted there. No new identity is registered by this work.

| Step | Required behavior |
| --- | --- |
| Restore | Verify the exact latest authority anchor, publish an encrypted quarantined database, and atomically record its ciphertext digest with the revoked writer generation. |
| Pending recovery | `head` reports `recovery_pending`. Normal `acquire` cannot resume the previous canonical store or bypass reactivation. Old grants remain unusable. |
| Reactivation proof | `activate_restored` requires literal trusted approval and a fresh verified `PublicTurn` whose principal was already mapped to an owner of this lineage. The caller cannot select an arbitrary owner UUID. |
| Restore selection | Require the current restore generation/anchor and exact acknowledged file digest. A later restore supersedes earlier activation receipts. Missing, modified, unacknowledged or wrong-lineage inputs fail closed. |
| Candidate validation | Copy the quarantine into encrypted staging; recheck its logical snapshot and source digest. Reject existing bindings/jobs. Bind only the freshly verified pre-existing principal to its original owner UUID. |
| Cutover | Publish and verify a new encrypted live snapshot and recovery bundle, then atomically advance the canonical pointer, writer generation and capability hash and clear pending recovery. Return the new grant only after commit. |
| Other owners/jobs | Other owners' records remain scoped but their bindings are not automatically activated. Old jobs are never resumed. The original quarantine file remains unchanged. |

Restore advances the memory sequence once; reactivation advances it once more.
The restore itself remains quarantined. Only the new committed canonical snapshot
contains the single approved binding. Writer capabilities are server-side secrets;
ordinary phone/browser/model requests must never receive or mint them. Existing
native/phone authority is still represented only by trusted fixtures here.

Failure before the authority commit keeps the acknowledged quarantine pending
and leaves the earlier canonical pointer/grant state unchanged. Published orphan
files cannot activate themselves. A process death after activation commit may
lose the returned grant, but the canonical state survives; a separately approved
takeover can issue a replacement capability for the newly active state. The
activation request itself is not an automatic token-replay or enrollment API.

## Evidence

[test_memory_reactivation.py](../../test_memory_reactivation.py) adds 15 cases.
The initial 14-case pass is preserved in [first-pass-tests.txt](first-pass-tests.txt).
**114 distinct checks verified:** the [combined run](combined-before-test-fix-validation.json)
passed 113 checks, with one concurrency-test failure. Its
[full log](combined-before-test-fix-tests.txt) is preserved. The test expected
only a conflict, but the safe losing request hit the existing three-second
catalogue lock timeout. It now captures thread errors, accepts only that exact
timeout or a conflict, and verifies retry cannot perform a second activation.
The [targeted recheck](concurrency-recheck-validation.json) and
[recheck log](concurrency-recheck-tests.txt) pass. No implementation changed
between these runs. [validation.json](validation.json) records this aggregation;
a single all-green combined rerun is not claimed. The preceding 99 checks all
passed in the combined run.

Checks cover unchanged encrypted quarantine, stable owner rebind, disabled old
grants/jobs, blocked takeover while pending, wrong approval/unknown or unverified
identity, revoked proof during publication, missing/modified/unacknowledged files,
superseded restores, owner isolation, changed candidate copies, publication and
catalogue failures, concurrent activation, schema refusal, and actual process
death before/after commit. The complete source-loss case checks correction,
forgetting and expiry through restore, activation and phone/laptop fixture recall.

The earlier wrong-schema test now uses invalid version 999, preserving its
original purpose after version 2 became valid. No accepted app code, memory or
recovery primitives, provider, dependency or startup behavior changed.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-12-memory-reactivation/check.py
```

The runner requires the existing isolated SQLCipher driver and rejects skips.
Driver setup remains in the [encrypted-storage report](../2026-10-12-memory-hardening/README.md).
Fixtures and generated keys are temporary and workspace-contained. Atomic
hard-link publication runs with the required filesystem permission; it was not
replaced by a weaker copy. Expected native HMAC logs in the combined suite come
from deliberate existing corruption cases. [Static validation](static-validation.json)
records hashes, parsing, source preservation, local links and fixture cleanup.

## Remaining qualification gates

| Gate | Still required |
| --- | --- |
| Independent latest state | A separately durable, trusted catalogue/checkpoint source and failure-domain policy. Another old encrypted backup alone cannot establish freshness. Whole-authority rollback/loss remains unprotected. |
| Off-host placement | A concrete owner-selected destination, verified free-account eligibility/capacity and real failure/restore checks. No cloud resource or account was selected, accessed or provisioned. |
| Key custody | Protected recovery/storage keys in an owner-approved location separate from losing the sole source host. No real keys are created, saved or transferred by these tests. |
| Lost identity | This slice accepts only pre-existing verified principals. Lost passkeys/replacement devices require a separately approved recovery/rebinding or enrollment design; they are not silently registered. |
| Production cutover | Protect authority metadata/filesystem access, route all clients through the authority, qualify native fresh-owner proof and actual phone/laptop use. Legacy raw prototype calls remain outside fencing. |
| Resources and durability | Retention/orphan cleanup, old-backup physical erasure, disk/admission budgets, throughput, Oracle/platform/engine selection, clean-host recovery and power-loss behavior remain unqualified. |

All catalogue/objects are still local same-disk fixtures. Principal fingerprints
and owner UUIDs are metadata requiring protection, not public diagnostics.
Whole-store snapshots and single-writer serialization remain a prototype cost.
Earlier encrypted snapshots may retain logically forgotten values until a future
retention/erasure policy is implemented. No new cloud or paid dependency is
justified by this isolated result.

Next: select and qualify the free independent latest-state/recovery destination
and protected key custody, then a real clean-host/native identity acceptance
drill before valuable shared records. Enrollment, private migration and deployment
remain deferred. Accepted voice, UI, auth, startup and unrelated local work are
preserved; no commit or push.
