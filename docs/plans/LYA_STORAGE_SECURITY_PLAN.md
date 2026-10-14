# LYA private memory and recovery plan

Status: 2026-09-20. This describes inspected code and isolated tests, not a
production security certification. Real enrollment remains deferred at the owner's
request. Nothing in this plan enables camera capture, cloud sync or background uploads.

## Decision

Use the existing encrypted SQLite store as LYA's memory authority. Keep personal
inference on the laptop. Store only explicitly approved notes; a model response is
not automatically a fact. Add portable encrypted recovery before cloud sync.
Use standard formats and small, replaceable components for long-term maintenance.

No application can promise that nobody can ever access its data. Malware or an
administrator controlling an unlocked Windows account can read process memory and
invoke that user's DPAPI. Our achievable boundary is authenticated access inside
LYA, encrypted files at rest, restrained data collection, and no personal-context
cloud inference through the reviewed Brain path. OS security and recovery custody
remain necessary. Prompt instructions alone are not security enforcement.

## What exists and what is pending

| Area | Current evidence | Remaining work |
| --- | --- | --- |
| Local memory | Scoped encrypted notes, expiry, correction, deletion and bounded relationships; synthetic tests | Real authenticated owner journey |
| Private answers | Verified personal requests select local inference in Brain; no cloud fallback on local failure | Laptop quality/performance and full desktop acceptance |
| Permission gate | Exact expiring challenge; literal approval required; role/session rechecks | Working trusted verifier/session binding; Python callbacks remain trusted code |
| Recovery | Native selection/key-confirmation/preview UI plus atomic no-overwrite file export; synthetic full restore into a fresh local key passes | Real trusted owner binding, real key custody and clean-device drill |
| Google Drive | Design only | Scoped OAuth, encrypted archive upload/download, quota and restore tests |
| Obsidian | Candidate for explicitly selected Markdown exports | Evaluate current official docs and build export preview; no plugin installed |
| NotebookLM | Optional non-private research destination | Recheck current official privacy terms before any use; no integration or upload |
| Biometrics | Separate synthetic registration foundation | Owner enrollment deferred; no new collection |

Run the isolated storage checks with `check-storage-recovery.cmd`. See
`archive/history/reviews/2026-09-20-storage-recovery/README.md` for core evidence, and
`archive/history/reviews/2026-09-20-recovery-interface/README.md` for the newer UI/file evidence.
Diagram: `diagrams/17-storage-recovery.png`; editable flow:
`diagrams/17-storage-recovery.mmd`. The PNG is a companion overview, not a Mermaid
engine rendering. It is the earlier core-only snapshot; its pending UI is now
implemented and tested with synthetic profiles. Current UI screenshots are in the
newer evidence folder. Remote connections remain unimplemented.

## Memory lifetimes and ownership

| Category | What belongs here | Where / lifetime | Removal behavior |
| --- | --- | --- | --- |
| Request context | Current question and a bounded set of relevant evidence | Process memory, request duration | References released after use; not guaranteed RAM wiping |
| Session notes | Explicit `remember session label = note` | RAM; up to 20 notes | Cleared on sleep, identity change and expiry/15-minute idle checks; idle detection occurs on the next request, not a background eraser |
| Short | Useful recent facts/preferences | Encrypted notes, 7 days | Excluded after expiry; purged by relevant memory operations |
| Long | Ongoing project decisions | Encrypted notes, 90 days | Same expiry behavior |
| Until | A note needed until a specific deadline | Encrypted notes, explicit timezone-aware timestamp | Original deadline survives backup/restore |
| Permanent | Explicit durable knowledge chosen by the owner | Encrypted notes, no automatic expiry | Still editable and deletable; permanent does not mean immutable |
| Credentials | Provider keys, passwords, recovery keys | Separate protected configuration/custody | Never a conversational note or backup note type |
| Biometrics | Consented authentication templates | Separate encrypted tables | Excluded from portable note backups; enrollment deferred |

Every saved note carries owner, kind, source, revision, creation/update time and
retention/expiry. Corrections increment revision without silently extending its
lifetime. Explicit relationships (`supports`, `contradicts`, `depends_on`,
`related_to`) link notes of the same owner; deleting a note deletes its links.
Relationships are user declarations, not proven causal knowledge.

The current budget is 2,000 notes per owner and bounded retrieval. It avoids a
separate graph service and persistent plaintext search index. Whole-database
encryption loads/serializes the database in memory per transaction; this is not
claimed to scale to millions of notes. Large files and models do not belong in
the note table. Measure workload before changing engines or adding a vector DB.

## How an answer and save should work

1. Classify the request without granting authority from a name, face color or model output.
2. For personal work, require an active verified owner session and exact approval.
3. Retrieve only that owner's unexpired notes, with source and revision. Treat their contents as data, never executable instructions.
4. Personal context uses the configured local inference client; unavailable means stop. The built-in local HTTP client disables proxies and redirects. An injected adapter is trusted code and must be reviewed.
5. Check cancellation, identity/role and evidence expiry again before displaying an answer.
6. Only an explicit authorized save/correction changes memory. Model replies and council agreement do not establish truth or modify permissions.

Guest public questions may use cloud. The secret-word detector is only a secondary
heuristic; it cannot recognize every private detail. Select private mode before
typing confidential text. No claim is made that every legacy module follows this
path. Legacy Supabase sync must stay inactive until separately reviewed.

## Local encryption and key handling

Runtime database: `%LOCALAPPDATA%\LYA\lya.db.enc` unless `LYA_DATA_DIR` overrides it.
The store is serialized into RAM and encrypted before atomic disk replacement;
it uses process/thread locking. Read-only recovery checks do not rewrite the
database. Failed replacement cleans up its own encrypted temporary file and
preserves the original database.

The existing cipher is Fernet: AES-128-CBC with HMAC-SHA256 authentication.
The existing local key is DPAPI-protected at the ignored legacy location
`security/.lya_key`; this task does not move it or touch the real store.
Do not claim AES-256 or assured secure deletion. SSD behavior, swap, crash dumps,
external copies and snapshots require separate consideration. Ordinary deletion
cannot guarantee physical erasure everywhere.

The registration recovery-code hash is not a database decryption key. Losing the
Windows key is recoverable for selected notes only if an independent note archive
and its matching recovery key were retained beforehand.

## Portable recovery contract implemented now

`storage/recovery.py` is an internal library for a trusted controller. Its file
helpers now publish encrypted archives without overwriting, read bounded archives
and authenticate previews. It does not read `.env`, enroll anyone or contact any
network service. The native controller is `desktop/recovery.py`.

1. `new_recovery_key()` produces a random Fernet key in memory. It is not a password. The UI shows it masked by default, requires separate-custody acknowledgement and re-entry, and never writes a key file or automatically copies to the clipboard. Real key custody and recovery still need an owner drill.
2. `export_notes()` requires explicit note IDs, an active owner session and exact approval. The approval includes a selection digest, resolved database path and recovery-key fingerprint. It rejects expired, foreign and protected credential rows.
3. It creates versioned JSON containing only selected note content/metadata and relationships between those notes. The whole payload is authenticated and encrypted under the independent key. The API returns ciphertext bytes.
4. `restore_notes()` binds approval to the exact archive digest and resolved destination. It checks authentication, version, size, counts, allowed fields, kinds, relationships and lifetimes.
5. Restore requires an already initialized, empty owner profile. It cannot restore identities, grant roles or overwrite existing memories. It re-encrypts content with the destination's local key and remaps relationship IDs.
6. Expired notes and their links are skipped. Session changes, cancellation, malformed data and write failures abort the transaction.

Limits: 16 MiB input archive, 2,000 notes, 8,000 selected links; export additionally
limits plaintext size. No compression or executable attachments. User-owned notes
can still contain sensitive material; a secret wrongly saved as an ordinary fact
cannot be reliably detected by its kind. This is why selection and encryption
are mandatory. Archive length and creation-time metadata are not hidden by Fernet.

Forgetting a live note does not delete a disconnected backup. Expiry is enforced
by the restore implementation, but someone holding the recovery key can decrypt
an old archive outside LYA. The future archive-retention/deletion UI must explain
this explicitly. An attacker with both archive and key can read and forge it.
No automatic backup schedule or deletion has been activated.

## Google Drive, Obsidian and NotebookLM

**Google Drive:** proposed transport for already encrypted note archives. Keep the
recovery key outside the same cloud account/folder. Never synchronize `.env`, raw
biometrics, the full repository or live database blindly. Use app-specific access
or access to explicitly selected app files, rather than all-drive access. Official
scope references: [Drive authorization](https://developers.google.com/workspace/drive/api/guides/api-specific-auth)
and [application data](https://developers.google.com/workspace/drive/api/guides/appdata).
We have not configured OAuth, verified account quota or uploaded anything.

**Obsidian:** proposed optional reading/editing surface for selected Markdown
exports. Do not make it the authority for roles, keys or private access. Treat
exported Markdown as plaintext unless a separately verified protection layer is
used. Keep community plugins out of the private-memory path. Import, if later
added, must preview changes and require approval; file contents cannot execute
tools or redefine LYA's policy. Current Obsidian product-specific security and
sync claims were not verified in this research pass.

**NotebookLM:** an optional cloud research workspace, outside our local-only
secret-memory boundary. Restrict any future use to public or intentionally
sanitized documents. Do not upload LYA's private store, keys, faces or voice
templates. Provider privacy promises are not the same as a design in which only
the owner holds the decryption key. Recheck the official account-specific terms
before integration; none was enabled here.

## Remaining implementation order and acceptance gates

1. **Trusted owner session.** Finish existing Windows Hello/session binding and cancellation handling when the owner is ready. Do not simulate successful enrollment or downgrade to name/face-only authorization. Test guest denial and real owner approval in the normal Windows desktop.
2. **Recovery UI and file boundary — implemented, synthetic-tested.** Selected labels, key confirmation, archive preview and explicit restore are connected. Atomic ciphertext publication refuses overwrites; cancellation, disk failure, destination races and fresh-key restore pass temporary-profile tests. Remaining gate: real owner session/approval and clean-device recovery with user-managed key custody. No live profile was changed.
3. **Key lifecycle.** Migrate the legacy repository key location only after recoverability is verified. Plan a reversible format/key migration, interrupted-write recovery and key rotation. Recovery credentials require their own verified custody flow; don't reuse the registration code silently.
4. **Archive management.** Owner chooses the loss window and retention before scheduling. Track archive versions and deletion, including old remote copies. Deletion acknowledgement must distinguish live records, local archives and cloud copies.
5. **Drive adapter.** After explicit account connection, use minimal scopes and ciphertext only. Test access revocation, offline behavior, interrupted transfer, quota exhaustion and download -> restore. No paid fallback. Mobile remote retrieval requires connectivity; offline mobile needs a previously approved local copy.
6. **Optional note applications.** Implement selected export preview first. Obsidian/NotebookLM must not become privileged tool controllers or silently receive all memories. Keep exports/imports reversible and documented.
7. **Release maintenance.** Version storage schemas and recovery formats; test old fixtures against every migration. Pin dependencies, review security updates, rerun isolated tests, and preserve a rollback path. Models can be replaced without changing note ownership or keys. Measure latency, RAM, disk size and restore time on the actual laptop before claiming capacity.

A five-to-ten-year lifespan comes from maintainable formats, recovery drills and
updates. It is not a guarantee that today's hardware, providers or model quality
will remain suitable without maintenance.

## Research limitation

Agent Reach was used for the research attempt. A public-document fetch escalation
was rejected because automatic approval review hit a usage limit; it was not a
safety determination. The blocked fetch was not bypassed. Therefore the product
fit above is a conservative integration design, not an exhaustive current GitHub
or vendor-security audit. Local implementation/tests proceeded independently.
