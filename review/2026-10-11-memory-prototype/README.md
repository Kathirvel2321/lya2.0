# Selective memory: disposable SQLite baseline

11 October 2026. Implemented the next authorized fake-record memory slice in
`brain/memory_prototype.py`. It is isolated from the running laptop and phone.
**This prototype is plaintext and accepts fake data only.** It requires an explicit
database path and `synthetic_only=True`; no existing store or default path is used.

Later on 11 October: [encrypted recovery qualification](../2026-10-11-memory-recovery/README.md)
adds schema version 2 lineage/state sequencing, encrypted snapshots/checkpoints
and deletion-aware quarantined restore. The live prototype database remains
plaintext. Version 1 fake databases are refused without migration. The original
timing table and `qualification.json` below are retained version 1 observations,
not a new version 2 or encryption benchmark.

## What works in the isolated prototype

| Operation | Behavior |
|---|---|
| Save | Explicit per-operation trusted approval, typed flat JSON value, kind, project and retention; commit before returning a receipt |
| Recall | Exact ID or bounded literal keyword/phrase search; current authorized owner/project only, at most six search results |
| Correct | Requires the current revision; preserves ID, original recorded time and retention; increments revision and replaces search content atomically |
| Forget | Removes current value/key/source and keyword projection; keeps a content-free deletion marker and revision; stale retries cannot recreate it |
| Expire | Seven days, 90 days, explicit future UTC epoch or permanent; expired records are excluded and tombstoned during the next scoped operation |
| Retry | Owner-scoped request ID plus request fingerprint; identical retry returns the original metadata receipt, changed content conflicts |
| Rotate credential | Trusted fixture simulates approved rotation; stable random UUID owner remains, old pairing binding is revoked |
| Restart | Record, revision, binding mapping and retry receipt survive reopening the same database |

There is no ordinary-chat auto-save, inferred-fact promotion, attachment/biometric/
credential ingestion, transcript archive, model call, external export, new server
or production API. Kinds are fact, preference, decision and lesson. Values are
flat JSON objects with at most 16 named scalar fields and a 4 KiB encoded limit.
Owner-confirmed means explicitly selected by the synthetic user, not independently
verified truth. Current-value records carry save/correction request provenance;
full valid-time history and relational/semantic retrieval remain later work.

Stable owner IDs are separate from credential hashes. Trusted provisioning maps
an authenticated existing pairing binding to a random owner UUID. Approved fixture
rotation preserves that UUID and records; it cannot silently reuse a revoked or
already assigned binding. This tests storage semantics, not a deployed credential
rotation, lost-key recovery or enrollment flow.

The adapter takes the previous slice's immutable `PublicTurn`, rechecks fresh
verification, resolves its binding server-side, and requires literal trusted
approval for reads and writes. Client requests cannot carry owner, approval,
privilege, storage-domain, source-authority or arbitrary path fields. This approval
argument is a fixture boundary, **not a real consent proof or production grant**.
Live adapters must bind existing exact approval to the actual operation and
revalidate authority at commit. No phone privilege was expanded by this prototype.

## Transaction and deletion rules

SQLite transactions commit the current record, keyword projection, revision-bound
outbox job and retry receipt together. Corrections require `expected_revision`,
so two devices editing revision 1 yield one committed revision 2 and one conflict.
Request IDs are scoped to stable owner, including across device sessions/rotation.
Receipts contain ID/revision/operation/commit status, never values. Replaying an old
save after forgetting returns a historical receipt, not evidence the record still
exists; callers must query current state before displaying it as saved now.

Composite foreign keys scope outbox/deletion references to the same owner/project.
Older pending jobs become obsolete on correction/deletion. Fake job acknowledgement
checks the current revision, expiry and deletion state. No embedding model, external
worker, lease/retry scheduler or actual downstream publication is implemented.

Forgetting clears active content and search visibility; it does not promise physical
erasure from SQLite free pages, filesystem copies or backups. The deletion register
is in the same database. It **cannot prevent an older backup from restoring
a later-forgotten fact by itself**. The later recovery prototype requires a latest
separately trusted checkpoint/anchor and suppresses these values in isolated tests;
an actual independent destination and acknowledgement policy remain pending.
Expired rows are immediately ineligible for reads/jobs; physical cleanup is lazy.
An explicit new save after expiry/forget creates a new ID rather than reviving one.

This small baseline serializes reads and writes with `BEGIN IMMEDIATE`, has FULL
synchronous commits and closes each connection. Guards: 10,000 total memory rows
including tombstones, 40,000 ordinary write receipts plus room for one deletion
receipt per record, and 16,384 SQLite pages (64 MiB with default 4 KiB pages).
These are configured prototype limits, not qualified operating capacities.
Ordinary receipt exhaustion does not block forgetting; real disk exhaustion still
can. Free-space reserves, maintenance, concurrency and diagnostic retention require
qualification before live use. No idempotency history is silently evicted.

## Actual checks

19 new memory checks plus the previous 10 contract checks pass: **29 total**.
They use signed fake WebAuthn keys/disposable stores. Covered cases include owner/
project isolation, fresh proof/approval, unknown fields, malformed values/retention,
Unicode, restart, corrections, concurrent conflict, retry, expiry, forgetting,
rotation, stale jobs, composite foreign keys and revocation during a transaction.

Failure checks include:

- A failing SQL trigger after record/search writes: record, projection, job and
  receipt all roll back.
- Stop or revoked phone proof before commit: no partial record or receipt.
- Actual child-process exit before SQLite commit: journal recovery leaves no write.
- Child-process exit after commit but before reply: retry returns the one durable
  receipt and does not create another record.
- SQLite `SQLITE_FULL` caused by a temporary page-count limit: failed operation
  leaves no partial writes. The physical laptop disk was not filled.
- Unrecognized existing database: rejected with original bytes preserved;
  unavailable storage: no success acknowledgement.

`qualify.py` creates **1,000 synthetic records** in disposable storage, measures
storage operations with an injected context, corrects/retries/forgets 60 records,
then checks reopen persistence, integrity and foreign keys. The database occupied
1,175,552 bytes at the end of this run; see `qualification.json` for exact counters.

| Operation | Samples | p50 ms | p95 ms |
|---|---:|---:|---:|
| Save | 1,000 | 12.008 | 18.591 |
| Get | 60 | 3.552 | 4.517 |
| Keyword search | 60 | 3.880 | 5.286 |
| Correct | 60 | 13.192 | 16.617 |
| Retry | 60 | 3.530 | 5.567 |
| Forget | 60 | 13.576 | 18.115 |

These are one local plaintext SQLite run, not phone/network/model performance,
encrypted storage performance, native authentication cost, a cold/warm study,
10,000-row/load qualification or a PostgreSQL/SQLCipher comparison. Isolated tests
ran concurrently; ordinary desktop load was uncontrolled. Tests verify
literal Tamil/English/Tanglish keyword cases; paraphrase/transliteration accuracy
is not qualified. PostgreSQL and SQLCipher drivers were absent; neither installed
or chosen as a tested production engine. Full roadmap order 4 remains open on
encrypted engine comparison even though this semantics baseline is implemented.

## Reproduce

```powershell
.\.venv-ui\Scripts\python.exe -m unittest test_memory_prototype test_conversation_contract
.\.venv-ui\Scripts\python.exe review/2026-10-11-memory-prototype/qualify.py
```

Temporary store/loopback access must be allowed. The tests perform only synthetic
enrollment in local fixtures, not real enrollment or owner sensor collection.
The qualification script writes a content-free result JSON and removes its fake
database afterward. Its injected identity deliberately excludes real auth costs.

Next: qualify encrypted live storage with an explicit engine comparison and real
independent recovery/key custody. Fake encrypted backup/restore checks are recorded
in the linked recovery slice; they do not complete the live recovery gates.
Production cutover and valuable shared records
still require free-tier/cost verification, approved server-readable placement,
independent recovery destination and key custody. Existing apps, voices, pause
behavior, prompts, pairing, private stores and Oracle resources are unchanged.
