# Memory recovery acknowledgement — 12 October 2026

Later same-day follow-up: [hardening and encrypted-storage qualification](../2026-10-12-memory-hardening/README.md)
adds recovery-key pinning, same-sequence divergence detection, catalogue schema 2
and an optional SQLCipher fake-data candidate. The results below describe the
earlier 61-check stage; use the follow-up for current implementation status.

Continues the owner's memory implementation request. This slice adds
[SyntheticRepository](../../brain/memory_repository.py) to the existing
[memory](../2026-10-11-memory-prototype/README.md) and
[recovery](../2026-10-11-memory-recovery/README.md) prototypes. **Fake data only;
no production path, private record, external destination or key store is connected.**

## Implemented

- `SyntheticRecovery.bundle` captures one consistent committed SQLite snapshot,
  then encrypts a backup and deletion checkpoint from that same state. A source
  mutation during transfer cannot make the two files describe different states.
- `SyntheticRepository.sync` publishes new immutable files, reads/decrypts both
  back, verifies their hashes and complete matching heads/owners, then commits a
  metadata-only SQLite catalogue acknowledgement with FULL synchronous commits.
  It returns only after commit. Saving a memory and verifying its backup remain
  separate outcomes; destination failure never rolls back or claims to back up
  an already committed memory.
- Status reports `pending`, `verified`, `unavailable` or `source_behind`, along
  with observed source/acknowledged sequences. `verified` means the observed
  synthetic state has a readable matching encrypted snapshot. It does **not**
  establish independent recovery, encrypted live storage or production safety.
  A later save, correction, forget or expiry cleanup advances the source sequence
  and leaves status pending until synchronization succeeds.
- Restart and retry reuse the acknowledgement without another bundle when its
  state and files still verify. A corrupt/missing bundle can be replaced by a
  newly captured verified bundle from the trusted synthetic source. Earlier
  encrypted files remain intact. A source behind the catalogue cannot replace a
  newer acknowledged state. Concurrent publishers serialize through SQLite.
- Restore uses the catalogue anchor, verifies the backup hash again at the
  actual restore read, and requires an independently supplied `required_sequence`.
  A known later unacknowledged deletion therefore blocks restoration of the older
  snapshot. Existing restore rules still suppress expired/deleted records and
  publish a new database with zero bindings and zero resumed jobs.
- A missing catalogue is an error, including on reopening its existing directory;
  it is not silently recreated. Unrelated database bytes are preserved. Paths
  reject symbolic-link ancestors; explicit synthetic opt-in and literal trusted
  operation approval remain required.

The new repository has no runtime callers. The only pre-existing implementation
changed is [memory_recovery.py](../../brain/memory_recovery.py), extracting its
existing validation for reuse and adding bundle capture plus an optional trusted
backup digest. Existing backup/checkpoint/restore call sites remain compatible.
There is no database schema change or migration in the memory baseline.

## Evidence

[test_memory_repository.py](../../test_memory_repository.py) adds **15 checks**;
the combined conversation, memory, recovery and repository suite has **61 checks**.
See [validation.json](validation.json) and [tests.txt](tests.txt) for the recorded
result. [Static validation](static-validation.json) records four parsed Python
sources, local-link checks and removal of temporary fixture directories.
Tests include actual child-process termination before acknowledgement
commit and after commit before a reply, concurrent publishers, a source write
during transfer, a known unacknowledged forget, readback damage, missing files,
wrong keys, authenticated ciphertext replacement, replacement between verification
and restore, transfer/catalogue errors, cancellation, stale source rejection,
restart/retry, lineage isolation and quarantined restoration.

Reproduce with generated fake keys and workspace-contained temporary storage:

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-12-memory-acknowledgement/check.py
```

Initial direct unittest execution encountered Windows sandbox temporary-file
permissions. The workspace runner resolved that fixture location. The sandbox
also denied the existing atomic hard-link publication operation; final checks
ran with that operation permitted, without replacing it with a weaker copy.
An initial round-trip assertion assumed physical SQLite row numbers survive
restoration; it was corrected to compare stable IDs and record contents instead.

## Remaining gates

The catalogue and destination are separate directories **on the same test disk**.
Neither is an independently trusted off-host freshness service. Rolling back the
catalogue together with the caller's required sequence can bypass freshness;
this slice cannot detect it. The caller-supplied sequence is a trusted fixture
input, not a consent proof or implemented live protocol. A missing freshness
source must not be guessed from an old backup in a future integration.

Source writes are not fenced or synchronously coupled to acknowledgement. Status
is true only for the observed sequence and can become stale immediately after
another write. An unacknowledged change may be lost if the source disappears;
its latest sequence/deletion state needs independently durable custody before
valuable writes. There is no owner reactivation flow. Restores remain quarantined.

Live and staging SQLite databases and catalogue metadata remain plaintext.
Backups/checkpoints alone are encrypted. Key custody, key rotation, free off-host
placement, SQLCipher/PostgreSQL qualification, clean-host restore, directory
durability under power loss, hostile-filesystem race qualification and real
device integration remain open. Interrupted publication can leave unacknowledged
orphan bundles; automatic cleanup, backup retention and physical erasure are not
implemented. No quota, capacity, resource or latency qualification is claimed.

Next: qualify encrypted live storage and independently durable latest state/key
custody, then implement writer fencing before connecting valuable shared records.
No deployment, enrollment, private transfer, dependency installation or paid
resource provisioning occurred. Accepted voice, UI, authentication, startup,
mobile additions and existing private stores are preserved.
