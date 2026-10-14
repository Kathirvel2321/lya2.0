# Durable network witness coordinator — 14 October 2026

Latest same-day follow-up: [safe receipt retirement](../2026-10-14-memory-receipt-retirement/README.md) adds approved acknowledgement of only an idle, locally confirmed protocol generation. Pending operations retain their recovery receipts. The opt-in witness mode, current tests and migration limits are documented there; no production integration is added.

Later same-day follow-up: [witness capacity and recovery drain](../2026-10-14-memory-witness-capacity/README.md) adds receipt-free signed observations, protected finish capacity, prepare preflight and a database page budget. The coordinator now uses those observations. The 115-case results below describe the preceding revision; current affected-component checks and unchanged-source preservation are recorded in the follow-up. Receipt retirement and independent hosting remain pending.

The owner approved the next memory connection after reviewing the build status. [SyntheticNetworkAuthority](../../brain/memory_network_authority.py) now reuses the existing authority's save/read/correct/forget/expiry, takeover, restore and verified-reactivation operations with the [authenticated loopback witness](../2026-10-14-memory-witness-service/README.md). It is an isolated fake-data integration, with no production callers, startup service or remote deployment. Existing local authority/custody/recovery implementations and accepted desktop/mobile paths are preserved.

## Explicit setup and trust

Bootstrap a synthetic encrypted store through `SyntheticAuthority`, register its exact checkpoint/writer epoch and key-capsule digest in `SyntheticWitness`, and explicitly enable the loopback endpoint. Open the existing authority using `SyntheticNetworkAuthority(..., client=client, synthetic_only=True)` and approve `bind_witness(lineage, keys_digest, approved=True)` once. This changes authority schema 2 to schema 4; it never automatically binds, bootstraps a missing catalogue, migrates schema 3 or replaces a binding. The original authority refuses schema 4, including already-open old objects. Its local schema-2/schema-3 behavior remains unchanged.

The one-lineage network binding pins the service/client/lineage, protocol-key fingerprint, capsule digest and last confirmed protocol generation. Port is a reconnectable loopback address, not identity. Wrong keys/identity, missing schema or malformed journals fail closed. Raw storage/recovery/protocol keys, writer tokens, record values and request bodies are not written into this metadata journal. Tests use generated disposable keys and synthetic records; the fixture capsule digest is synthetic metadata, not real key custody.

## Commit and recovery flow

See [coordinator flow](coordinator.mmd). It is an annotated view derived from the reviewed source. The trace helper's [raw import trace](import-trace.json) resolves only the Python entry node; it does not resolve these dotted module imports and is not evidence of a complete dependency graph.

| Durable phase | Meaning and permitted recovery |
| --- | --- |
| `idle` | Exact local checkpoint/epoch and confirmed remote generation match; no pending operation. |
| `intent` | Stable prepare/finish IDs and previous state committed locally before requesting a reservation. Source mutation has not begun. |
| `prepared` | The exact remote reservation and its next generation are persisted. A source writer must recheck ownership and the remote reservation before entering the existing authority body. |
| `committed` | Source pointer/writer/recovery changes and their exact target state committed atomically with the journal. The caller still has no success acknowledgement. |
| `idle` again | The same finish ID's signed current receipt was validated, then the local confirmation committed. Only then may the ordinary operation return; content-bearing replies retain the existing fresh-identity check. |

The endpoint now accepts an optional `expected_generation` on prepare and compares it in the same witness transaction as reservation creation. The coordinator always supplies it. Existing standalone protocol callers keep their earlier request form. This closes the gap where a copied source could reserve after another copy completed an unchanged read: checkpoint equality alone cannot detect that intervening protocol operation.

All source-side steps use the existing catalogue's cross-process SQLite writer lock. Between steps, a pending journal blocks normal APIs. An explicitly approved `reconcile_witness` locks that same source, checks its recorded state and verified latest recovery bundle, and resolves only the saved operation. Before source commit, it can finish unchanged because the writer lock plus atomic journal/pointer prove no committed source transition occurred. After source commit, it finishes the saved target. It never re-executes the user's memory request or reconstructs a lost writer token. A paused original process cannot resume after reconciliation because every later step rechecks the operation ID and phase under that lock.

A lost prepare reply can be resolved against the same reservation ID. A lost finish reply requires the saved finish ID's signed current receipt; a matching head alone is insufficient. This also handles reconciliation dying after an unchanged finish before saving its generation. Divergent checkpoints, another operation's reservation, changed custody, newer protocol generations, missing latest bundles and stale receipts remain blocked. There is no timeout unlock, inferred rollback, older-backup fallback or automatic trust reset.

## Checks and reproduction

[test_memory_network_authority.py](../../test_memory_network_authority.py) adds 22 fake-data checks using real localhost HTTP and encrypted temporary stores. Coverage includes source/confirmation commit failures; prepare/finish/reconciliation reply loss; stale copies competing to write; the unchanged-read generation race; a paused writer fenced by reconciliation; correction, forgetting and expiry; damaged-live-file recovery; interrupted restore/reactivation; lost grants; cancellation/revoked identity; missing/corrupt/pin-changed state; and actual process termination at five durable boundaries.

The [runner](check.py) additionally selects the preceding 75 authority/reactivation/custody/storage/local-witness checks and 18 protocol checks. **All 115 selected Windows checks pass: 22 new coordinator cases plus 93 regressions, zero failures/errors/skips.** Final results and source hashes are in [validation.json](validation.json), with the actual [test log](tests.txt). The initial 20-case coordinator revision passed in [initial coordinator validation](initial-coordinator-validation.json); that is earlier evidence, not a substitute for the final revision. The first sandbox attempt stopped all 20 cases at Windows atomic-link denial before coordinator execution; [sandbox evidence](initial-sandbox-validation.json) is preserved. Tests then ran with permission for workspace-contained atomic links and localhost sockets, preserving the existing publication primitive. SQLCipher emitted expected authentication/decryption rejection diagnostics during wrong-key/corrupt-file regression cases; those cases passed.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-14-memory-network-authority/check.py
```

The runner reuses the existing ignored SQLCipher qualification driver; no installation is needed. It places generated fixtures under this report directory and removes them. [Static and preservation checks](static-validation.json) and [diagram validation](diagram-validation.json) accompany the run.

For the owner-operated Ubuntu lab, refresh the two modules and new test, then run this selection using the existing Linux virtual environment and `test_qualification.py` fixture:

```bash
cd ~/lya-lab
source .venv/bin/activate
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src"/brain/{memory_network_authority,memory_witness_service}.py brain/
cp --backup=numbered "$src/test_memory_network_authority.py" .
python -m unittest -v test_memory_network_authority test_memory_witness_service
```

This revision has not been run in WSL or Oracle by the assistant. Earlier owner-reported WSL results apply to the preceding local integration/protocol revisions.

## Limits and next step

This completes the durable adapter slice in the local fake-data lab. Independent hosting, TLS transport/identity, backup-object/catalogue/key survival, protected production keys and full shared-device integration remain pending. No live service, private data, account, real key, package, OS/WSL setting, paid resource, enrollment, deployment, commit or push changed. There is no real-device, clean-host, power-loss, whole-witness rollback or production security certification claim.

The trusted catalogue is plaintext metadata; whole-store copying and SQLite serialization are bounded prototype choices. Protocol receipts remain capped at 1,024 and are never silently evicted; normal calls consume multiple receipts, so sustained service needs a qualified retention/capacity lifecycle. Pending/invalid operations intentionally block availability until safe reconciliation; a divergent copied catalogue is not automatically adopted. Orphan cleanup and physical erasure remain unimplemented. A witness alone cannot reconstruct lost memory.

Next: owner-operated Linux qualification of this exact revision, then select concrete independent witness/backup survival placement and verify free allowance/capacity. Qualify TLS and lifecycle with synthetic data before protected production-key setup and a separately approved private pilot.
