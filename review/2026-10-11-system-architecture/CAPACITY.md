# Capacity, formats and performance envelope

2026-10-11. GiB means 1,073,741,824 bytes. GB in provider documentation may use
decimal units. Observations below are a point-in-time resource reading, not a load
test, a tenancy/billing inspection or a resource reservation.

## Actual available machines

| Resource | Read-only observation | Consequence |
|---|---|---|
| Laptop CPU | Intel i3-1215U, 6 physical cores / 8 logical processors | Keep UI and deterministic private functions light; measure CPU inference |
| Laptop RAM | 7.70 GiB total, 1.16 GiB free at the reading | Do not auto-load multiple new models or infer available runtime RAM from model file size |
| Laptop C drive | 250.68 GiB free | Potential recovery destination; current space is not a reserved backup budget |
| Oracle CPU | aarch64, 4 logical CPUs | PostgreSQL and one bounded index worker are plausible candidates |
| Oracle RAM | 23.41 GiB total, 22.73 GiB available | Headroom exists for an isolated prototype; no performance guarantee |
| Oracle filesystem | 192.69 GiB total, 189.21 GiB free | OS, WAL, indexes, objects, staging and recovery all share this finite space |
| Current phone service | Active; 20.31 MiB current, 256 MiB hard memory cap, 40-task cap | New storage/index work needs its own tested resource envelope |

Safe evidence files: `capacity-observed.json`, `laptop-capacity-observed.json`.
`inspect_capacity.py` reads OS counters through the existing pinned SSH connection;
it does not return host addresses, credentials, private records or provider outputs.

**Cost mismatch to resolve before deploying:** current Oracle documentation lists
2 A1 OCPUs / 12 GB of Always Free memory, while this host exposes more resources.
The OS cannot establish whether the account has grandfathered eligibility, credits
or billable allocation. Do not infer either free eligibility or an actual charge
from this discrepancy. Existing services were not resized or stopped.
The documented storage pool is 200 GB combined boot/block storage and 20 GB object
storage, subject to account conditions; neither equals this application's budget.
[Oracle policy](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

## What “maximum capacity” can honestly mean

| Layer | Limit | Meaning |
|---|---|---|
| Current laptop notes | 2,000 notes per person | Implemented application cap, unchanged |
| Current public archive | 10,000 rows; 128 MiB content; 256 MiB DB guard | Implemented separate public archive limits, unchanged |
| Current phone | Last 2 exchanges in RAM; 15-minute session | No lasting phone memory database |
| Proposed first qualification | 100,000 selected records, 2 active devices | A benchmark target; not a passed result |
| Proposed growth qualification | 1,000,000 selected records | Separate load/restore gate; not promised current operating capacity |
| Proposed primary DB budget | Initially 2 GiB soft planning budget; 20 GiB growth ceiling only after recovery capacity grows | Design settings only; service/WAL limits still need implementation |
| SQLite engine | About 17.5 TB at default 4 KiB pages; about 281 TB with 64 KiB pages | Format upper bounds, not speed guarantees or LYA capacity |
| PostgreSQL engine | Default relation limit 32 TB; database size bounded in practice by resources | One table/index relation differs from the whole database; not unlimited hosting |

Engine references: [SQLite](https://www.sqlite.org/limits.html),
[PostgreSQL](https://www.postgresql.org/docs/current/limits.html).

## Transparent storage estimate

Proposed boundary limits for the first shared-memory prototype (not deployed):

| Item | Initial bound | Overflow behavior |
|---|---|---|
| One structured memory value | 16 KiB UTF-8 | Reject with an explanation; offer a separately approved document reference |
| One memory-write request including metadata | 64 KiB | Reject before database/model processing |
| List page | 100 records, also capped at 256 KiB serialized | Return a continuation cursor; never silently truncate a record |
| Recall result | 6 items / 2,000 evidence tokens | Return supported subset or enter an explicit longer research task |
| Background queue | 1,000 pending jobs, one heavy worker | Coalesce duplicate revision work or defer new ingestion visibly |
| Optional attachment | 10 MiB each, 10 GiB total proposed initial ceiling | Reject oversize upload; no attachment ingestion enabled by this design |
| Relationship expansion | 2 hops / 50 visited edges | Report bounded coverage rather than invent a complete graph answer |

Byte, token, row and time limits are different safeguards. Attachment limits do
not grant permission to upload photos or private files. Record count is additionally
limited by measured DB/backup budgets; the 16 KiB maximum is not the 8 KiB average
used in the estimates below.

Planning assumptions, not measured row sizes:

- Average text/value, metadata, selected revision/source/link overhead: 8 KiB/record.
- Reserve another 8 KiB/record for ordinary indexes, alignment and growth overhead.
- Optional 384-dimensional float32 vector: 1,536 raw bytes, plus the same amount
  provisionally reserved for vector/index overhead.
- Total illustrative allowance: **19 KiB per record**. Real graph degree,
  revision count, PostgreSQL layout and HNSW parameters can exceed this assumption.
- Excludes attachments, model weights, logs, WAL, temporary sorts and backups.

| Records | Text + metadata + index allowance | Raw 384-d vector bytes | Total with vector/index allowance |
|---:|---:|---:|---:|
| 10,000 | 0.153 GiB | 0.014 GiB | 0.181 GiB |
| 100,000 | 1.526 GiB | 0.143 GiB | 1.812 GiB |
| 1,000,000 | 15.259 GiB | 1.431 GiB | 18.120 GiB |

At this assumption, a 20 GiB DB budget holds about 1.10 million records. That is an
arithmetic estimate, not a certified record limit. A million photos is an entirely
different workload. More vector dimensions increase index/storage costs; 1024-d
float32 uses 4,096 raw bytes/vector before type/index overhead. Reducing dimensions
or quantizing requires recall-quality evaluation, not just a smaller file.

| Selected new records per day | Records after 10 years (365-day years) | Illustrative primary size |
|---:|---:|---:|
| 10 | 36,500 | 0.66 GiB |
| 100 | 365,000 | 6.61 GiB |
| 1,000 | 3,650,000 | 66.14 GiB |

These are retained selected records, not every sentence spoken. Expiry/deduplication
may reduce counts; evidence/history may increase space. Never delete permanent
records just to force the estimate to fit.

## Backup capacity can be the first limit

Seven daily plus four weekly copies represent up to 11 full generations in a
conservative no-deduplication estimate. A 1.81 GiB primary needs about 19.93 GiB for
those database copies; an 18.12 GiB primary needs about 199.32 GiB. Objects, staging,
recovery metadata and free-space headroom are additional. Compression/deduplication
can help, but are not guaranteed capacity. The 20 GB Oracle object allowance cannot
be assumed to hold every generation of a large memory store.

Therefore the usable cap is the minimum of disk budget, measured performance,
qualified restore capacity, backup capacity and cost eligibility. Raising the
database limit alone is unsafe. Proposed first backup budget: reserve an independent
destination large enough for the initial corpus and headroom before accepting
valuable memories; growth requires increasing that destination or revising an
explicit recovery policy. No destination or schedule was configured here.

## Proposed resource and latency qualification

An initial isolated trial may budget up to 2 GiB for PostgreSQL, 256 MiB for the
new Python service, 768 MiB for one embedding worker, and 512 MiB for maintenance,
with additional OS/file-cache headroom. These are proposed caps to measure and
adjust, not installed settings. The existing phone cap remains 256 MiB. Test ARM
package/model support and peak memory during index creation/backup, not only idle.

| Measurement | Proposed acceptance target | Conditions |
|---|---|---|
| Exact/keyword memory lookup | p95 under 50 ms | Warm 100k synthetic records, 2 active clients, measured on Oracle |
| Hybrid recall | p95 under 200 ms | Includes query embedding and ranking; separately report cold start |
| Memory commit | p95 under 100 ms | Durability enabled; no attachment upload or background embedding |
| Direct text recall | p95 under 500 ms | Authenticated device request to displayed result; report network separately |
| Model first text | p95 under 1.5 s after confirmed turn | Aspirational target dependent on eligible provider/model/network |
| Voice first audio | p95 under 2.5 s after confirmed turn | Aspirational streaming target; also report delay from actual speech end |
| Local playback stop | p95 under 150 ms from stop event | User device measurement; upstream cancellation reported separately |

None of these targets has been passed in this research. A failed target leads to
profiling/admission limits or an explicit revised target, not a fabricated success.
Use 1k/10k/100k rows first, then 1m only after capacity allows; report p50/p95/p99,
peak RSS, CPU, disk/index size and error rates. Separate exact, paraphrase, temporal,
multi-hop, mixed-language and unanswerable cases.

The architecture explorer includes this same arithmetic with editable record count,
average record size, vector dimensions and backup generations. It is a capacity
calculator, not a running LYA memory prototype or benchmark.
