# Memory hardening and encrypted-storage candidate — 12 October 2026

Later same-day follow-up: [canonical authority and writer fencing](../2026-10-12-memory-authority/README.md)
adds a separate isolated API with verified snapshot commits and stale-writer
protection. The 77-check evidence below describes this preceding stage; the
follow-up records 99 combined checks and the remaining off-host/production gates.

The owner requested fixing the current memory work before continuing; “next 4”
was a typo. This pass hardens the isolated prototypes, then qualifies an optional
SQLCipher candidate. **Generated fake records/keys only. No production caller,
private-store migration, device integration, enrollment or deployment.**

## Current-work fixes

- An already-open memory object refuses a missing database instead of creating an
  empty replacement during recovery/status checks. Storage and recovery paths
  reject symbolic links and Windows junctions at every ancestor. Hostile path
  replacement races remain unqualified.
- Recovery synchronization refuses a changed recovery key before publishing or
  updating an existing acknowledgement. This is not a key-rotation workflow.
- A readable acknowledged snapshot must match the actual source records,
  receipts and deletion register. Equal sequence numbers with different contents
  report `diverged`; synchronization raises a conflict and keeps the previous
  acknowledgement. This detects that case; it does not fence an old writer.
- Invalid clocks and explicit expiry values fail bounded validation, including
  NaN, infinity, booleans, negative values and oversized integers. Authenticated
  recovery payloads with incorrect encoded value/receipt types raise validation
  errors rather than accidental JSON type errors.
- Catalogue schema 2 stores a random recovery-key fingerprint, never key bytes.
  Schema 1 catalogues are refused without modification or automatic migration.
  The memory database remains schema 2; existing method calls remain compatible.

The six initial regression cases are preserved in
[before-fixes-tests.txt](before-fixes-tests.txt) and
[before-fixes-validation.json](before-fixes-validation.json): four failures and
two errors. The old-catalogue case specifies the new schema policy; it is not an
additional pre-existing product bug. The first hardening stage passed **67**
checks ([log](hardening-tests.txt), [result](hardening-validation.json)).

## Encrypted candidate

[SyntheticMemory](../../brain/memory_prototype.py) accepts an explicit generated
32-byte `encryption_key`. It requires SQLCipher with active encryption, page HMAC
and no plaintext header; absent or unsuitable drivers fail without a plaintext
fallback. The default remains the existing plaintext fake-data baseline. No
automatic conversion, default change or key persistence is implemented.

[Recovery](../../brain/memory_recovery.py) uses the selected driver's consistent
snapshot API. Its in-memory snapshot destination uses the same SQLCipher key;
records are serialized in RAM and sealed with the separate existing Fernet
recovery key. An explicit restore `storage_key` encrypts both staging and the
published quarantined database. Restores retain zero bindings and zero resumed
jobs. The [repository](../../brain/memory_repository.py) forwards that option.
Catalogue metadata remains plaintext; encrypted backup/checkpoint formats are
unchanged. This is disk encryption, not a guarantee against memory inspection,
swap, hibernation or process dumps.

Driver qualification: `sqlcipher3==0.6.3`, CPython 3.12 Windows x64 wheel, runtime
SQLCipher **4.12.0 community** / SQLite **3.51.1**. The wheel SHA-256 matches the
published PyPI artifact and [pinned test requirement](requirements-windows-test.txt).
It is installed only in ignored `.drivers/`, outside the application's environment;
the wheel is retained in ignored `wheels/`. No app dependency manifest changed.
Primary references: [SQLCipher API](https://www.zetetic.net/sqlcipher/sqlcipher-api/),
[design](https://www.zetetic.net/sqlcipher/design/),
[upstream package and wheel](https://pypi.org/project/sqlcipher3/0.6.3/).
Agent Reach's local backends were unavailable, so primary-source web fallback was
used. No owner content was sent to those sources.

An attempted optional `cipher_memory_security=ON` setting caused a native Windows
smoke-test process to terminate with memory-lock resource warnings. It was removed;
the candidate retains the documented default for this optional setting. Memory
wiping/locking is **not qualified**. Required page encryption/authentication and
file-integrity checks pass without that setting.

## Final evidence

[validation.json](validation.json) and [tests.txt](tests.txt) record **77 passing
checks, zero failures/errors/skips**: 61 previous checks, six hardening cases and
ten SQLCipher cases. Sources:
[hardening checks](../../test_memory_hardening.py),
[encrypted checks](../../test_memory_encrypted.py).
Encrypted cases cover restart/recall/correction/retry/forget/expiry, wrong and
malformed keys, absent/plaintext drivers, refusal of implicit migration,
corrupted/truncated pages, active rollback journals, WAL snapshots, encrypted
restore staging, cancellation, actual SQLite-full rollback, simultaneous edits
and child-process death before commit/after commit before reply. Expected native
HMAC/decryption error messages come from the deliberate wrong-key/corruption cases.
Byte scans find neither the checked synthetic markers nor generated storage keys
in database/journal/WAL files; this is supporting evidence, not a cryptographic proof.

[qualify.py](qualify.py) runs the same 1,000-record corpus through both candidates.
[qualification.json](qualification.json) records 60 corrections, 60 forgets,
940 searchable/restored records, 60 deletion markers, 1,120 receipts/jobs,
restart, integrity/foreign-key checks and quarantined restoration for each.

| Local p95, milliseconds | Plaintext SQLite | SQLCipher |
| --- | ---: | ---: |
| Save | 22.806 | 24.600 |
| Get | 11.300 | 6.718 |
| Search | 7.461 | 54.321 |
| Correct | 21.847 | 24.028 |
| Retry | 7.144 | 7.627 |
| Forget | 23.614 | 24.654 |

Database sizes were 1,171,456 and 1,175,552 bytes respectively. These are one
local run with different SQLite builds (stdlib 3.53.1 versus 3.51.1), injected
synthetic authorization, fresh connections and uncontrolled desktop load. The
regression run overlapped the beginning of this comparison. These numbers are
illustrative; they do not isolate encryption overhead, include phone/network or
native authentication cost, or establish an engine winner. SQLCipher search was
slower here and needs representative platform/load evaluation before selection.

[Static validation](static-validation.json) records source hashes, Python parsing,
scoped whitespace/document-link checks, caller references and fixture cleanup.
Earlier acknowledgement/recovery reports remain dated evidence.

Reproduce the isolated qualification using generated fake keys only:

```powershell
.\.venv-ui\Scripts\python.exe -m pip --isolated download --only-binary=:all: --no-deps --require-hashes -r review/2026-10-12-memory-hardening/requirements-windows-test.txt --dest review/2026-10-12-memory-hardening/wheels
.\.venv-ui\Scripts\python.exe -m pip --isolated install --no-index --find-links review/2026-10-12-memory-hardening/wheels --no-deps --require-hashes -r review/2026-10-12-memory-hardening/requirements-windows-test.txt --target review/2026-10-12-memory-hardening/.drivers
.\.venv-ui\Scripts\python.exe review/2026-10-12-memory-hardening/check.py
.\.venv-ui\Scripts\python.exe review/2026-10-12-memory-hardening/qualify.py
```

The combined runner requires the driver so qualification cannot silently skip it.
Normal test discovery without the isolated driver explicitly skips encrypted
cases. Initial sandbox filesystem restrictions were resolved with permitted
workspace-only fixture execution, preserving atomic hard-link publication.

## Remaining gates and next step

Independent latest-state/deletion custody, a free off-host recovery destination,
real key custody/rotation, old-writer fencing, owner reactivation and clean-host
restore remain open. Rolling back the catalogue and the caller's required sequence
together remains undetectable. A higher-sequence old branch is not fenced, and
unacknowledged writes can be lost with the source. Orphan/retention cleanup,
physical erasure and power-loss directory durability remain unqualified.

PostgreSQL comparison, Oracle ARM/package/resource/free-tier qualification and
production engine selection are deferred; no server or paid resource was created.
No real iPhone/laptop acceptance is claimed. Next: design independently durable
latest-state/key custody and writer fencing, then qualify the chosen platform
before activating valuable shared records. Accepted voice, UI, authentication,
startup, protected local stores and unrelated uncommitted work are preserved.
