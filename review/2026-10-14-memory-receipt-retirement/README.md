# Safe witness receipt retirement — 14 October 2026

The owner approved implementing safe receipt retirement after supplying a complete 50-case Ubuntu WSL result for the preceding capacity revision. This slice changes only [the isolated witness protocol](../../brain/memory_witness_service.py), [its coordinator](../../brain/memory_network_authority.py), new fake-data tests and continuity documentation. This task adds no production caller and changes no accepted client, private store, OS/WSL setting, account, dependency, key custody, service or deployment.

## Explicit mode and bounded state

`SyntheticWitnessEndpoint.enable_retirement(approved=True)` explicitly enables protocol **storage schema 2** on a fresh synthetic protocol store: generation zero, no mutation/head receipts and no reservation. Existing signed observations/nonces may remain. A used legacy store is refused unchanged; no receipt-history migration, automatic conversion or floor reset exists. Schema-1 behavior remains the default. The signed transport envelope/domain stays version 1; storage schema and transport version are separate.

The new mode adds a receipt-generation column and one durable `rpc_retirement.retired_generation` counter. Prepare must carry `expected_generation`; finish already carries its reservation generation. Receipt rows are tagged with that protocol generation. The old receipt-producing `head` request is refused in this mode; signed `observe` remains available. This is the protocol reservation counter, not a memory sequence or writer epoch.

The server rejects a prepare whose proposed generation, or a finish whose generation, is at or below the retired counter before looking for a saved receipt. A fresh nonce or changed request ID cannot revive such a completed operation. After retirement, IDs are scoped by protocol generation: an authorized caller may reuse an ID only in a newly signed higher-generation request. Retained receipt IDs still pin their exact meaning. This deliberately avoids an unbounded per-ID tombstone table; it does not promise eternal global uniqueness of arbitrary IDs.

The durable floor, current witness generation, key/client/lineage pins, receipt schema and receipt-generation ranges are validated on access. Missing/corrupt/downgraded retirement state is refused; it is never recreated. No additional host or independent rollback anchor is introduced.

## Coordinator acknowledgement and recovery

The new `SyntheticNetworkAuthority.retire_receipts(lineage, approved=True)` holds the existing source catalogue writer lock. It requires an **idle, locally confirmed** operation journal, verifies the latest recovery bundle/source state and the exact signed remote head/custody/generation, then acknowledges that generation for retirement. Pending local operations are refused, including source-committed operations whose finish reply or local confirmation was lost.

The signed `retire` request binds the exact witness state, custody digest and generation. In one witness transaction, the service checks that this is the current completed generation with no reservation, advances the retirement counter and deletes receipts at or below it. The returned signed confirmation explicitly binds the retired generation. Retirement needs no new retry receipt and remains possible at the receipt ceiling. Nonce/freshness/body/authentication limits still apply.

The source had already durably confirmed the operation before retirement starts, so no new local retirement journal is needed. A lost retirement reply can repeat the same exact state/generation using a fresh nonce; advancing an already-equal floor is idempotent. If another protocol operation has advanced the head, the old retirement request fails rather than claiming current success. Process death before the witness commit rolls back the floor and deletion together; death after commit retains both. Pending or rolled-back source catalogues cannot use retired finish receipts to reconstruct an acknowledgement.

No saved memory, user-level memory request receipt, writer grant, correction, deletion marker, key envelope or backup is retired by this API. It returns only content-free acknowledgement metadata. The endpoint trusts its authenticated coordinator to acknowledge a durably confirmed source; direct possession of the protocol key is still trusted authority, not a substitute for owner authentication in a future deployed service.

See [retirement flow](retirement.mmd) and [diagram validation](diagram-validation.json). The [raw import trace](import-trace.json) resolves only the entry node; the flow diagram is explicitly annotated from reviewed source because the helper does not resolve these Python dotted imports.

## Evidence and reproduction

[Fourteen new checks](../../test_memory_receipt_retirement.py) cover explicit fresh-only enablement, retired-operation replay with new nonces/IDs, strict generation fields, pending/wrong-state/key rejection, atomic rollback, lost replies/restart, nonce and reply correlation, missing/corrupt/downgraded state, competing prepare/retire, actual process death around retirement commit, source confirmation gating, rolled-back source refusal and unchanged memory/grants.

One new check completes **520 protocol rounds with a two-receipt cap**, retiring 1,040 completed mutation receipts over time while keeping the current receipt count and logical database pages bounded. This is a synthetic durability/capacity check, not a throughput, long-term soak or production-load qualification.

The [runner](check.py) selects the 14 new cases plus all 50 preceding capacity/protocol/coordinator cases, using the existing ignored SQLCipher qualification driver. [Validation/source hashes](validation.json), [test log](tests.txt) and [static/preservation checks](static-validation.json) record current evidence. Temporary fixture stores and generated disposable keys are removed after the run. Prior Windows/owner-reported WSL results remain dated evidence for earlier source revisions, and overlapping counts are not added.

**All 64 selected Windows cases pass in one combined run, with zero failures/errors/skips.** This includes both the new opt-in mode and unchanged legacy-mode behavior exercised by the preceding 50 cases.

Final workspace checks observed unrelated concurrent desktop/security/storage edits, including a changed `desktop/experience.py` baseline hash. Those files were not edited, reverted or reviewed by this memory task. The preservation report distinguishes those observations from the two intended memory implementation changes; no whole-application acceptance is inferred.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-14-memory-receipt-retirement/check.py
```

For the owner-operated Ubuntu lab, refresh the two modules and new test; the three preceding test modules and `test_qualification.py` are already required by the earlier lab selection:

```bash
cd ~/lya-lab
source .venv/bin/activate
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src"/brain/{memory_network_authority,memory_witness_service}.py brain/
cp --backup=numbered "$src/test_memory_receipt_retirement.py" .
python -m unittest -v test_memory_receipt_retirement test_memory_witness_capacity test_memory_witness_service test_memory_network_authority
```

This revision has not been rerun in WSL or Oracle by the assistant. Do not treat the earlier owner-reported 50-case WSL result as qualification of retirement mode.

## Limits and next step

This is an opt-in fresh-store protocol and explicit trusted acknowledgement API. Existing used/full legacy stores are not migrated or repaired, and no automatic retirement scheduler is installed. Nonce saturation, physical disk failure, counter exhaustion and divergent/rolled-back source state still fail closed. Retirement reuses SQLite pages; it does not promise file shrinkage or physical erasure. The existing logical database page cap does not bound journals/WAL, memory or total filesystem usage.

The floor shares the trusted witness disk. Whole-witness rollback/loss, independent backup-object/catalogue/key survival, TLS, protected production keys, native-device authentication, clean-host/power-loss recovery, capacity/admission and real application acceptance remain open. No production readiness or full-repository security certification is claimed. Next owner-operated Linux qualification of this exact revision, then synthetic TLS/service lifecycle work and concrete independent free placement before any private pilot. No external resource, paid service, enrollment, real key setup, deployment, commit or push occurred.
