# Witness capacity and recovery drain — 14 October 2026

Later same-day follow-up: [safe receipt retirement](../2026-10-14-memory-receipt-retirement/README.md) adds an explicitly enabled fresh-store mode with generation-tagged receipts, a durable retired-generation floor and coordinator acknowledgement. The retirement-pending statements below describe this capacity revision; default legacy stores remain unchanged and are not automatically migrated. The prior 50-case WSL result does not qualify the newer retirement revision.

The owner requested the next memory implementation. This slice qualifies bounded witness storage and preserves recovery when retry receipts approach their limit. It changes only [the synthetic witness protocol](../../brain/memory_witness_service.py) and [its isolated coordinator](../../brain/memory_network_authority.py), plus tests/documentation. No live assistant, provider, deployment, host setting, account or production key changed. The owner subsequently supplied Ubuntu WSL output reporting all 50 selected cases passing; see the owner-reported evidence below. Independent placement remains undecided.

## Behavior

- New signed `observe` requests return a fresh exact head/reservation/generation without creating a retry receipt. They still authenticate, bind replies to the original request, enforce nonce/time/body limits and reject replay. An observation is a point-in-time read, not a durable mutation receipt. Reusing an existing mutation receipt ID with a different observation meaning fails.
- Prepare requires two free receipt slots: one for prepare and one for finish. While a reservation exists, other new receipt-producing requests cannot consume its last finish slot. Existing exact receipt retries remain available at the receipt ceiling. No receipts are evicted or rewritten.
- The coordinator uses observations for state checks. Its initial observation requests a receipt-capacity check before committing local intent, so an already exhausted receipt budget rejects new ordinary work without leaving a pending journal. Prepare still checks capacity atomically; preflight is not a reservation or guarantee against competing callers.
- `SyntheticWitnessEndpoint.capacity()` exposes only local operator counters and configured limits. It returns no record values, keys, lineage, tokens or request IDs, and has no network route. These counters are not a service-readiness or disk-availability guarantee.
- Every endpoint connection applies a **4 MiB logical SQLite database page limit**. Oversized existing databases and growth beyond the limit fail closed. This covers the main database's pages, not filesystem-wide usage, rollback journals/WAL, temporary files, process memory or other direct trusted filesystem writers.

The existing signed `head` receipt behavior remains available. Schema versions, identity/key pins, stable prepare/finish IDs, durable reservations, writer fencing and approved reconciliation remain intact. No missing-state recreation, timeout unlock, old-backup fallback or trust reset was introduced. See the source-derived [capacity flow](capacity.mmd) and [diagram validation](diagram-validation.json).

The [raw import trace](import-trace.json) resolves only the Python entry node; dotted imports are outside that helper's resolution. The capacity diagram is annotated from the reviewed source rather than presented as a complete generated dependency graph.

## Checks

[Ten new fake-data cases](../../test_memory_witness_capacity.py) cover signed observation/replay/correlation; strict flags and wrong authentication; protected finish capacity; full-store lost-reply retry after endpoint restart; prepare preflight; nonce expiry without receipt deletion; content-free counters; actual SQLite-full rollback; oversized-file refusal; and integrated authority reconciliation at the final receipt slot. The [runner](check.py) also selects the 18 protocol and 22 coordinator regressions. [Results/source hashes](validation.json), [test log](tests.txt) and [static preservation/link checks](static-validation.json) record the evidence. All fixtures/keys are disposable and temporary within the workspace; the existing ignored SQLCipher driver is reused.

**All ten new checks pass on Windows, and all 40 affected protocol/coordinator regressions pass.** The initial 50-case selection passed 49 cases, including all 40 regressions; one new wrong-key test expected only `PermissionError`, while the existing client also rejects unsigned authentication errors with `ValueError`. That assertion was corrected to match the existing rejection contract, then all ten new cases were rerun with zero failures/errors/skips. No implementation changed between runs. Thus 50 distinct cases are verified across those runs; a single all-green combined rerun is not claimed. [Initial validation](initial-validation.json) and [initial log](initial-tests.txt) are preserved.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-14-memory-witness-capacity/check.py
```

The owner subsequently refreshed the modules/tests using the commands below and supplied a complete 50-case Ubuntu WSL run: all individual cases `ok`, final `OK`, with no failures/errors/skips. The selected test names match the current 10 capacity, 18 protocol and 22 coordinator definitions. See [owner-reported WSL validation](wsl-user-reported-validation.json). The assistant did not rerun WSL or independently measure copied-source hashes. This establishes owner-reported selected-test evidence, not Oracle, TLS, device or production qualification.

To reproduce that owner-operated lab selection:

```bash
cd ~/lya-lab
source .venv/bin/activate
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src"/brain/{memory_network_authority,memory_witness_service}.py brain/
cp --backup=numbered "$src"/{test_memory_network_authority,test_memory_witness_service,test_memory_witness_capacity}.py .
python -m unittest -v test_memory_witness_capacity test_memory_witness_service test_memory_network_authority
```

The lab must already contain the preceding memory modules and `test_qualification.py`. No WSL execution/settings or package installation was performed by this task. Earlier 75 local memory regressions remain dated evidence for their unchanged sources, not an additional fresh run here.

## Remaining limits and next step

This is safe bounded admission/drain, **not automatic receipt retirement or indefinite service capacity**. The 1,024 receipt and 2,048 live-nonce ceilings remain. Coordinator operations normally consume two receipts; fresh observations consume nonce capacity. Expired nonces may be removed under the existing freshness rules; receipts are retained permanently. A nonce-full window or real disk-full condition may temporarily block recovery. This cannot repair an older already-full reserved store created before finish capacity was protected.

A competing caller can exhaust receipts after preflight and before prepare; the local intent then remains blocked under the existing approved-reconciliation rules. There is no unsafe local unlock. A monotonic retirement/acknowledgement design and its recovery proof are still required before sustained production operation. These limits, database-full handling and administrative recovery need qualification on the eventual independent host.

Next: design and prove safe receipt retirement, then establish independent free witness/backup survival placement and synthetic TLS/service lifecycle qualification before protected production keys and a separately approved device pilot. TLS, independent backup objects/catalogue/keys, power-loss/clean-host recovery, retention/physical erasure and live-device acceptance remain open. No production readiness, full-repository pass, external provisioning, paid resource, deployment, commit or push is claimed.
