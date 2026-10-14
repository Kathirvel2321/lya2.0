# Canonical recovery authority and writer fencing — 12 October 2026

Later 12 October follow-up: [verified recovery and owner reactivation](../2026-10-12-memory-reactivation/README.md)
adds the pending-recovery gate and exact-quarantine activation for a freshly
verified pre-existing owner. Current authority schema 2 refuses schema 1 without
migration. The 99-check artifacts below preserve the preceding stage.

Owner authorized building the next recovery/writer-protection slice, with strong
security and architecture as ongoing requirements. This adds an isolated
[SyntheticAuthority](../../brain/memory_authority.py). **Fake data, generated
keys and local temporary storage only; no production integration or deployment.**
The authority is a separate trusted state store in this test architecture, not
an independently hosted or rollback-resistant service.

## Commit and authorization contract

| Boundary | Enforced behavior |
| --- | --- |
| Canonical state | Only the authority catalogue's committed pointer selects current memory. Bootstrap/device copies and unacknowledged candidates cannot become current by changing their own sequence numbers. |
| Writer grant | A trusted, explicitly approved takeover increments a durable generation and issues a random 32-byte bearer token. Only its hash is persisted. Wrong tokens, writer IDs, generations and lineages fail. Tokens are server-writer capabilities; they must not be issued to a model or ordinary phone/browser client. |
| Fresh owner authority | Every memory operation still requires the existing fresh signed-fixture `PublicTurn`, active owner binding and literal server-side approval. A writer token does not replace owner verification or authorize another owner's records. |
| Optimistic concurrency | A new operation supplies the exact latest checkpoint anchor. An outdated anchor raises a conflict; the caller must refresh and resolve the current record revision. |
| Retry | A matching durable receipt can be replayed against an older anchor, with fresh authorization and a still-current writer grant. Changed request content fails. Receipts contain IDs/revisions, never forgotten values. |
| Commit point | Stage an encrypted copy, verify it matches the committed logical snapshot, apply the existing memory transaction, publish/read back the encrypted live file and recovery bundle, then atomically commit the pointer and live-file hash. A reply is released after that catalogue commit. |
| Takeover ordering | The catalogue transaction serializes grant validation, publication and commit against takeovers. A write already holding the transaction can finish before takeover; after takeover returns, its old grant cannot publish or read through this API. |
| Recovery | Restore only the authority's exact latest anchor. Successful recovery increments the generation and clears the writer capability. Restored databases are encrypted and quarantined with zero bindings/jobs; owner reactivation/cutover is not implemented. |

The authoritative tuple is the lineage, writer generation/token hash, exact
checkpoint anchor and encrypted live-file hash. The catalogue stores metadata
only; SQLCipher protects the live snapshots, and the existing separate Fernet key
protects the recovery backup/checkpoint. Actual protected key custody is still
unimplemented. The candidate requires an explicit storage key; there is no new
plaintext authority-memory mode or implicit migration.

The code reuses `SyntheticMemory`, `SyntheticRecovery`, `SyntheticRepository`,
their bounded validation, consistent SQLite backup API and atomic file publication.
Those modules and the accepted apps were not changed by this slice. No new driver,
framework, broker or service was installed. The isolated SQLCipher driver from
[the preceding qualification](../2026-10-12-memory-hardening/README.md) is reused.

## Failure behavior

Candidate database commits are provisional. A crash, cancellation, expired/revoked
turn, destination failure or catalogue failure before the authority commit leaves
the previous committed state current; partial files can remain unacknowledged.
A process death after the authority commit can lose the reply, but the matching
request receipt recovers the same result. There is no interval where a returned
successful new write relies only on an unbacked local source commit.

Changing an old bootstrap/device database, even to a higher sequence, cannot
replace the authority. Re-registering a lineage fails. The live snapshot's hash
and its logical state must match the acknowledged recovery snapshot. The staged
copy is checked again before applying a new operation, so a changed source during
copy is refused rather than incorporated. Missing/corrupt current files stop
writes. A healthy latest recovery bundle can restore even if the live file is
damaged. Missing latest recovery files never select an older retained bundle.

Successful restore fences the previous writer when the authority transaction
commits. If publication or catalogue commit fails, no success is returned;
a published but unacknowledged destination, if one remains, is quarantined and
cannot activate itself. This does not implement a new owner enrollment flow.

## Evidence and reproduction

[test_memory_authority.py](../../test_memory_authority.py) adds **22 checks**.
[validation.json](validation.json) and [tests.txt](tests.txt) record **99 passing
combined checks, zero failures/errors/skips**, including the preceding 77.
The [first authority pass](authority-first-pass-tests.txt) preserves the earlier
20-check stage before the final approval/copy-race cases were added.

A final test-only adjustment removed an assumption about which thread delivers
its reply first. The [targeted takeover recheck](takeover-validation.json)
([log](takeover-tests.txt)) passes while still requiring commit serialization and
rejection of the superseded grant; the authority implementation is unchanged.

Cases cover source loss and restart, unchanged bootstrap files, encrypted storage
and content-free catalogue/token representation, stale/forged/cross-lineage grants,
fresh owner/approval enforcement, concurrent takeovers and writes, in-flight
publication versus takeover, stale anchors and lost-reply retries, logical forget
and expiry recovery, quarantine/revocation, outdated restores, live corruption,
missing latest bundles/catalogues, wrong keys/schema, old-device re-registration,
source mutation during copy, publication/cancellation/revocation failures,
catalogue failure after files publish, and actual child-process death before and
after the authority commit.

The initial sandbox run failed at atomic hard-link publication before the cases
could run ([sandbox log](sandbox-tests.txt)). Permitted workspace-only execution
passed without replacing the publication primitive. SQLCipher's expected native
HMAC errors in the combined run come from existing deliberate corruption tests.
No public model, real authentication store, network endpoint or external account
is involved. Fake signed-passkey fixtures and generated keys are temporary.

```powershell
# Uses the existing isolated CPython 3.12 Windows x64 SQLCipher test driver.
.\.venv-ui\Scripts\python.exe review/2026-10-12-memory-authority/check.py
```

The runner requires the driver and rejects skipped qualification cases. The
driver setup is documented in the preceding encrypted-storage report. Normal
unittest discovery without that isolated driver explicitly skips these cases.
[Static validation](static-validation.json) records source hashes, parsing,
document links, caller checks, preservation of the preceding seven source hashes
and absence of temporary fixture directories.

## Limits and next step

Fencing applies to this new authority API and its canonical pointer. Existing
prototype files are not retroactively fenced. Devices must eventually call the
protected service rather than receive direct filesystem access or writer tokens.
Local trusted code with catalogue/filesystem access is outside this capability
boundary. No hostile-filesystem race or malicious-host protection is claimed.

The metadata catalogue and encrypted objects are on one test disk. Whole-authority
rollback/loss, account loss and key loss remain unprotected. Persisted tokens are
hashes, not implemented key custody; a caller must arrange protected keys/grants
or request a new explicitly approved generation. Grants have no clock lease;
revocation is by takeover/recovery. No automatic offline writer election exists.

Whole-store copying and retaining immutable snapshots intentionally prioritize
isolated commit semantics over throughput. Snapshot retention, orphan cleanup,
physical erasure, disk budgeting, bounded service admission and representative
load/latency must be qualified before production. Old encrypted snapshots may
still contain logically forgotten values. The catalogue uses a single SQLite
writer with a three-second lock timeout. Process-death checks do not establish
power-loss/directory durability, native device acceptance or clean-host recovery.

Next: qualify a concrete free off-host placement for the trusted latest-state
catalogue and encrypted recovery objects, protected key custody and owner
reactivation, then select/qualify the production engine and connect approved
device flows. Oracle free eligibility/platform capacity, PostgreSQL comparison
and real phone/laptop acceptance remain open. No valuable private memories,
accepted UI/voice/startup changes, paid provisioning, commit or push occurred.
