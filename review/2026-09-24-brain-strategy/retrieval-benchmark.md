# Synthetic native recall benchmark — 2026-09-24

Measured `brain.notes.retrieve(person, "needle")` on this laptop with a
temporary encrypted SQLite file, a disposable Fernet key and one matching
synthetic fact. Five sequential reads per size; reported median and maximum.
No real memory or vault key was accessed. This is a warm, single-process
microbenchmark, not a battery or full-app responsiveness test.

| Notes | Median | Maximum | Encrypted DB |
|---:|---:|---:|---:|
| 100 | 16.06 ms | 17.77 ms | 128 KiB |
| 1,000 | 52.41 ms | 55.51 ms | 512 KiB |
| 2,000 (current cap) | 97.74 ms | 103.03 ms | 928 KiB |

At 2,000 notes, a separate five-run measurement found `store.recall` at
56.92 ms median and full `notes.retrieve` at 103.69 ms. Opening the encrypted
database read-only and counting rows took 5.85 ms median. Thus most of the
cost is decrypting all rows and rebuilding the disposable FTS index, not
opening the encrypted file. The research's `<20 ms` semantic-read budget is
**not met** at 1,000 or 2,000 notes.

## Indexed implementation

`storage/store.py` now keeps an FTS5 table **inside the same whole-file
encrypted SQLite database**. Its triggers update the index on insert, update
and delete. Fresh databases use it immediately. An existing database without
the table backfills **temporarily in RAM on a read**; normal writes leave its
on-disk schema unchanged. Persistent migration requires the explicit
`LYA_ENABLE_SEARCH_MIGRATION=1` setting after a verified backup. A read-only
open does not rewrite the encrypted file. `brain/notes.py` queries
matching IDs and decrypts only the small result set, including eligible
one-hop graph neighbors. No separate plaintext index file is created.

The repeatable fixture in [`bench_retrieval.py`](bench_retrieval.py) measured:

| Notes | Indexed median | Indexed maximum | Encrypted DB |
|---:|---:|---:|---:|
| 100 | 4.09 ms | 4.82 ms | 181 KiB |
| 1,000 | 5.66 ms | 7.89 ms | 693 KiB |
| 2,000 | 10.66 ms | 11.53 ms | 1,237 KiB |

The 2,000-note synthetic median is about **9.2× faster** than the original
97.74 ms and meets the proposed <20 ms *microbenchmark* target. The encrypted
database grew by about 33% at that size. A model call, approval, cold startup,
competing laptop load and battery impact were not part of this benchmark.

`test_search_index.py` covers legacy backfill, unchanged ciphertext on
read-only migration, no automatic on-disk migration on normal writes, explicit
opt-in migration, corrections, forgetting, expiry, person isolation and
credential exclusion. `test_recovery.py` checks search after portable restore.
The change passed 56 focused tests. A real-store migration and long-running
desktop soak remain unverified; the owner should retain a verified recovery
copy before any migration of real data.
