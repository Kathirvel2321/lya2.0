# Encrypted backup and deletion-aware recovery prototype

11 October 2026. The next authorized slice is implemented in
[brain/memory_recovery.py](../../brain/memory_recovery.py), using the installed
`cryptography` Fernet implementation and the isolated
[memory baseline](../2026-10-11-memory-prototype/README.md).
**Fake data only. Backups and checkpoints are encrypted; the live and restored
SQLite databases remain plaintext. Nothing is connected to production or deployed.**

## What happens

1. SQLite's backup API captures a consistent snapshot in memory, including
   committed WAL data. It does not copy a live database file blindly.
2. The snapshot becomes validated, bounded UTF-8 JSON: stable owner IDs, current
   records/tombstones, revisions and metadata-only retry receipts. It excludes
   credential bindings, sessions and background jobs. No database schema, SQL or
   triggers are imported during recovery.
3. Fernet encrypts and authenticates the snapshot with a generated random key.
   A separately captured encrypted checkpoint contains record IDs/scopes,
   revisions, expiry, deletion state and deletion markers, without record values.
4. Restore requires both files, the key, explicit trusted fixture approval and the
   **latest independently trusted checkpoint anchor**: lineage, sequence,
   checkpoint ID and SHA-256 of its encrypted file. The anchor must come from a
   trusted source outside the old backup. A hash supplied by the backup is not
   proof of freshness.
5. Restore rejects a missing, mismatched, stale, incomplete or wrong-lineage
   checkpoint. It keeps only unchanged, current, unexpired values. Later-forgotten
   values remain cleared tombstones and are absent from rebuilt keyword search.
   Expiry is checked at restore time, even without prior cleanup. A newer
   correction or post-backup record whose current value is unavailable becomes an
   explicit `restore_unavailable` tombstone; the obsolete value is not served.
6. A fresh database is built and checked in a temporary staging directory, flushed
   and atomically published under a new filename. Existing files are never
   replaced. Cancellation or failed publication leaves no published partial file.
   Restored owners retain their UUIDs, but have **zero active bindings and zero
   resumed jobs**. There is no production reactivation flow in this slice.

Schema version 2 adds a random store lineage and transactional state sequence to
the disposable memory baseline. Owner provisioning/rotation and record mutations
advance the sequence with their transaction. Version 1 prototype databases are
rejected without automatic migration. No real database uses this prototype.
The previous 1,000-record timing artifact is retained as a dated version 1 result;
this slice does not requalify those measurements for version 2 or encryption.

## Checked

[test_memory_recovery.py](../../test_memory_recovery.py) has **17 passing checks**.
Together with 19 memory and ten conversation-contract checks, **46 pass**. All use
generated fake keys, signed synthetic owner fixtures and temporary databases.

- Encrypted round trip, value-free checkpoint, stable owner IDs and quarantined
  access; a second backup/restore of the recovered database also succeeds.
- Older backup plus latest checkpoint suppresses later forgetting, expiry,
  corrections and unavailable post-backup records; search excludes removed text.
- Missing/wrong/malformed key, truncated or altered backup/checkpoint, missing
  state, old checkpoint replay, wrong lineage/scope, changed state without a
  revision, incomplete deletion register and malformed authenticated JSON fail.
- Literal approval, cancellation before publication, existing-output protection,
  injected publication failure, size bounds and duplicate JSON fields.
- A held reader keeps a real SQLite WAL active while another connection commits;
  the backup includes the new committed record. Old schema bytes remain unchanged
  when rejected.

```powershell
.\.venv-ui\Scripts\python.exe -m unittest test_memory_recovery -v
.\.venv-ui\Scripts\python.exe -m unittest test_memory_prototype test_conversation_contract test_memory_recovery
```

See [validation.json](validation.json) for the recorded check boundaries. Temporary
SQLite/loopback fixture access must be allowed. No real enrollment, microphone,
camera, owner records, network provider or external storage is used by these tests.

## Required before valuable records

This is a recovery algorithm qualification, not an independent backup service.
Tests use separate directories on one temporary disk. They do not prove survival
of disk, Oracle account or host loss. Real key custody, a free independent
destination, retention/versioning, transfer verification and clean-host recovery
remain unconfigured. No dependency or paid resource was added.

If both the checkpoint and trusted anchor are rolled back together, this code
cannot detect that rollback. If either the required latest state or key is lost,
restore refuses; encrypted data has no password-reset bypass. Production writes
need a durable independently acknowledged checkpoint policy, visible saved versus
recoverable status, and old-writer fencing before any recovered owner is rebound.
Those policies are not implemented by a caller passing `approved=True`.

Forgetting here is logical suppression during approved restore. It does not erase
older encrypted backups or make their plaintext inaccessible to someone holding
the key. Backup expiry, deletion propagation and protected key access still need
real implementation. Ciphertext size and Fernet timestamps remain observable.

The staging database is plaintext; filesystem/temporary-file protection and live
database encryption are unqualified. Atomic publication requires hard links on
the destination filesystem and fails if unsupported. File flushing is tested;
directory durability under power loss and interruption at every process boundary
are not. Memory use, maximum capacity, real phone latency and clean-host/Oracle
operation were not qualified. No PostgreSQL/SQLCipher engine winner is claimed.

Next: qualify the live encrypted storage choice and implement independent free
recovery/key custody and write fencing before connecting valuable shared records.
The owner's Oracle-free-only budget and accepted clients, voice, pause, pairing,
private stores and startup behavior remain preserved.
