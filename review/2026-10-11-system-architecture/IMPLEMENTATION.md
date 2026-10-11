# Implementation sequence and acceptance gates

**Sequence update, 2026-10-11:** use [FINAL-ROADMAP.md](FINAL-ROADMAP.md) for the latest
numbered order. It brings baseline measurement forward and places tested recovery
before live valuable shared records. The cases and rollout safeguards below remain
applicable; the original stage table is retained as dated design history.

Research/design only, 2026-10-11. The full target architecture is deliberate; it
must be reached through independently testable changes that preserve accepted
voice, interface, startup, pairing and protected local data.

| Stage | Concrete deliverable | Exit evidence |
|---|---|---|
| 0. Settle placement and capacity | Owner reviews the server-readable NEW-memory scope, recovery destination and cost eligibility | Explicit placement scope; account/free-budget check; no private migration inferred |
| 1. Isolated competing prototypes | Same fake memory API/corpus against SQLCipher+FTS and PostgreSQL+pgvector, no live services | Transaction, scope, expiry, correction, crash and restore tests; measured resource/latency comparison |
| 2. Shared identity and records | Existing laptop/phone adapters bind to one logical owner and new shared memory API | Laptop save -> phone recall; phone correction -> laptop revision; restart persistence; conflicts/idempotent retries |
| 3. Memory quality | Evidence, valid time, relational links, optional qualified embeddings and abstention | Held-out recall/update/temporal/mixed-language tests; zero cross-scope disclosures in the test suite |
| 4. Recovery before valuable use | Independent encrypted backup, key recovery and deletion-aware restore | Restore into empty isolated host; verify objects, current deletions/expiry, sessions and recovery duration |
| 5. Consistent interaction | Same approved persona and memory presentation on both devices | Owner verifies familiar style, correct saved/forgotten status and laptop-asleep shared recall |
| 6. Latency work | Stage timing, then measured warm workers/text/audio streaming improvements | No regressions in pauses, complete questions, Stop, Amy quality, quotas or peak RAM |
| 7. Reviewed learning and tasks | Minimal resumable tasks and confirmed lessons, then separately approved skills | Failed/uncertain action recovery; repeated task improves on held-out cases; no unauthorized activation |
| 8. Growth | Larger corpus, expanded recovery budget and measured index/migration strategy | 1m-row test only when gates justify it; export/import, rollback and version upgrade qualification |

The prototype is an evaluation harness, not a second production system. Use fake
people, fake secrets, deterministic clocks, temporary storage and synthetic public
text. Do not import personal histories to make a benchmark more realistic.

The test set must include:

- Exact and paraphrased preferences, Tamil/English/mixed-language queries, spelling
  variations, conflicting names and truly unanswerable questions.
- Facts that change over time, late corrections, two devices editing one revision,
  expired facts, deleted facts and stale embeddings/cache entries.
- Owner/project isolation, revoked device grants, prompt-injected research text,
  generated false memories and private egress denial.
- Crash before/after commit, lost reply after a successful commit, repeated request
  IDs, index-worker retry, disk full and database unavailable.
- Backup restore after a later deletion, missing recovery key, corrupt object and
  incomplete deletion register. A restore must not resume service in these states.
- Incomplete speech, internal pause, noisy audio, false interruption, stop during
  inference/audio, hidden phone page and old audio arriving after cancellation.

Hold out evaluation cases from tuning. Compare retrieval independently from the
answer model; report each metric's numerator/denominator. Model-judge scores need
manual review of disagreements, and cannot replace deterministic permission tests.
Published LongMemEval/MemoryArena ideas guide the cases; we have not run those
benchmarks or claimed their scores.

Production cutover must be reversible: a separate service and new store, staged
fake data first, explicit writer ownership, confirmed backup, health checks and
rollback. No migration of the existing laptop vault, public archive or passkeys
is implied. A no-error process exit is not end-to-end owner acceptance.

## What was completed in this research task

Primary-source review; source-traced current boundaries; read-only laptop/Oracle
resource inspection; full architecture and seven focused diagrams; conceptual
data schema; explicit formats/retention/privacy/consistency rules; model and
database comparison; capacity arithmetic; prototype/rollout gates; local rendered
architecture explorer. See `validation.json` for actual artifact checks.

No production database/model installed, no private records collected/transmitted,
no billing console inspected, no provider inference called and no runtime feature
changed. Diagram rendering and calculator checks do not prove the proposed system.
