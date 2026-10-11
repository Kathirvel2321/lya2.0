# Public research archive — first remote storage stage

Date: 2026-10-07. Status: implemented, deployed on the existing Oracle VM and
tested remotely with synthetic public documents. Native commands passed fake-owner
integration checks. Actual owner sign-in/approval and native usage remain unaccepted.

## Delivered in order

1. Read-only readiness: existing pinned SSH, FTS5, installation permission and
   unused archive paths checked. Owner confirmed the existing VM and storage are
   within free allowances; this is owner evidence, not a billing API audit.
2. Separate archive: a new `lya-archive` account and root-controlled Python worker
   under `/opt/lya-public`. Public SQLite/FTS data lives in that account's private
   data directory. The existing inference account/files/services remain unchanged.
3. Bounded laptop cache: public revisions only, up to 256 MiB, allocated on demand.
   No new daemon, model, SDK or Python dependency. Native commands reuse LYA's
   existing verified-owner and exact-operation approval path.

## Native usage

These are structured text commands. Voice recognition of this grammar has not been
qualified. Reopen LYA to load changed Python code, then use an actual verified owner
session and complete the existing required operation approval. No enrollment or
permission bypass was performed during development.

```text
public archive app-builder: save python-guide 0 permanent | Python guide | https://example.invalid/guide | Synthetic guide explaining asyncio.
public archive app-builder: find asyncio
public archive app-builder: read python-guide 1
public archive app-builder: save python-guide 1 permanent | Python guide | https://example.invalid/guide | Corrected synthetic guide explaining threads.
public archive app-builder: delete python-guide 2
```

The example URL/document is deliberately fake. For real public research, review the
source/title/body first: this command explicitly sends them to Oracle. Private and
restricted notes are not exported by existing memory commands. `public archive`
does not pull local memories, chat history, files, keys, people or security records.
Do not label confidential data public. Public review is a deliberate operator
decision, not an automatic content classifier.

New saves use previous revision `0`; corrections name the exact previous revision.
Retain explicitly using `permanent` or an ISO timestamp with timezone, for example
`2026-11-01T18:00:00+05:30`. The same content/revision/expiry is an idempotent retry.
A conflicting version fails. Find returns up to six scoped excerpts and their
source/ID/revision; read names an exact revision. Source material is unverified data,
not authority to execute instructions. No language model is invoked by these routes.
Private mode blocks the external archive before any request.

## Storage and failure contract

- One public-only SQLite archive; no copy or migration of the protected local store.
- Strict request/record fields, public sensitivity, literal review acknowledgment,
  safe namespace IDs, integer versions and bounded text/wire sizes checked before
  transmission and on the server. Owner namespace is an opaque SHA-256 of the
  verified ID; real display names and raw person IDs are not transmitted.
- Owner/project filters precede returned FTS candidates. Quoted tokens prevent
  submitted FTS operators from becoming query syntax. Expired content is hidden
  immediately by query conditions and purged on the next request for that scope;
  there is no idle expiry daemon. Deletion clears content/index entries and keeps
  a minimal revision tombstone, preventing stale writes from resurrecting a document.
- Transactional corrections, idempotent retries, explicit acknowledgments and
  quota failures that preserve existing data. No silent paid/provider fallback.
- 24,000 UTF-8 bytes/document text, 65,536 bytes/encoded packet, six search results,
  10,000 total rows including tombstones, 128 MiB serialized active content and
  SQLite's 65,536-page ceiling (256 MiB with the new default 4 KiB page size).
  Larger corpora need measured capacity/recovery planning before raising limits.
- Remote transport uses the existing host pin, a separate least-capability key,
  no agent/port forwarding, a 12-second operation deadline and cancellation.
  Remote shell output/errors are not exposed. A timed-out write may have committed:
  completion is never claimed without its exact acknowledgment; retry unchanged.
- Cache identity includes owner/project/document/revision. Atomic files, checksum,
  expiry, correction/deletion invalidation and size eviction are tested. The cache
  is public plaintext, not a private store. A checksum detects corruption, not a
  malicious same-user rewrite. One trusted process is the current cache ceiling.
- Normal reads verify the requested revision remotely. Network failure does not
  silently use stale cached data. The low-level explicit cache API labels offline
  content `offline_unverified`; the native command does not offer offline answers.
- Writes are synchronous. A persistent encrypted outbox/automatic replay is not
  implemented: no critical private writes enter this public route. There is no
  public data migration or automatic save of model output.

## Access and deployment evidence

The new SSH account's home/authorized-key files and worker are root controlled;
only its data subtree is writable by that account. Its public key has OpenSSH
`restrict` and a forced `python3 -I` archive command. A live request that specified
an unrelated shell command still returned the archive response, without shell
output. Data permissions and code/authorized-key ownership were checked.

The private SSH key remains in the ignored
`security/public-archive-identity.local/` directory, with inheritance removed and
access granted to the current Windows identity. No provider key store was added;
the existing provider `.env` and inference key are unchanged. Only an archive
section was added atomically to the existing ignored `desktop/oracle.local.json`
after the checks passed. Runtime loading is lazy, on an explicit archive command.
The continuity report includes no key material, host address or account identifier.

This is a restricted account/forced protocol, not a complete OS sandbox or a
penetration-test certification. The operator's existing privileged SSH access
still exists. One archive identity manages public data; delegated/multi-tenant
server authentication is not implemented. Private memory remains local and must
retain its separate live acceptance gates.

Automatic approval review initially refused the persistent account/key change.
The owner then explicitly approved: “Yes, deploy the restricted archive.” Only
after that approval did the installation run. Neither rejected attempt executed.

## Recovery and checks

A consistent public SQLite snapshot was transferred to an independent disposable
laptop folder and opened without SSH or the original server. The expected synthetic
document was recovered; the live document was then deleted and both remote read and
cache confirmed its absence. The disposable recovery copy was removed. This proves
the synthetic recovery procedure, not an ongoing backup of future real documents.
Automatic full archive snapshots/off-device retention are still needed before
using it as the sole copy of irreplaceable research. Deleting a document does not
erase existing backups; retention must apply to those independently.

| Check | Evidence |
|---|---|
| Focused archive/native memory/search/recovery/approval/SSH regressions | 89 passed |
| Final scoped expiry cleanup checks | Eight archive checks passed |
| Compile and scoped Git whitespace | Passed |
| Fake corpus, 1,000 documents, seven warm exact-keyword reads | Median 2.111 ms, max 3.683 ms |
| Fake corpus database | 2,652 KiB |
| Live synthetic SSH operations | Seven calls, 501.726–1,348.399 ms |
| Live restricted-command/permissions/recovery/deletion | Passed |

SQLite's transaction context does not close connections. An initial Windows
cleanup failure exposed that handle leak; explicit `closing()` fixed it and the
temporary-store suites passed. The cache eviction fixture budget was corrected
to actually force eviction. An early restricted-runner test hung and was stopped;
the successful suites ran in the approved normal runner with synthetic data.

Timings exclude full LYA/hearing/inference, semantic accuracy, sustained CPU/RAM,
production p95 and owner data. No owner audio/camera/private corpus/provider
inference was used. These checks are not actual owner-interface acceptance.

## Files and next stage

- `storage/public_archive.py`: public archive worker, validation, backup primitive,
  bounded public cache; standalone stdlib worker, no private-store/model imports.
- `cloud/public_archive.py`: restricted, pinned, cancellable transport and lazy
  settings/cache adapter. Disabled unless all explicit deployment gates are true.
- `brain/workflow.py` and `brain/capabilities.py`: narrow explicit command path,
  permission gate and help entry. Existing routes/accepted voice/UI remain intact.
- `test_public_archive.py`: eight runnable synthetic acceptance checks.
- `probe_oracle.py`, `readiness.json`, `deploy_public_archive.py`, `deployment.json`,
  `check_resources.py`, `resource-check.json`, `validation.json`: reproducible
  checks, one-time reviewed deployment and safe aggregate evidence.

Next in order: independent retained backup/outbox design where data would otherwise
have only one copy; semantic retrieval quality/resource qualification against the
saved exact/paraphrase fixture; then tested skills with exact-version activation
and rollback. Current archive search is keyword FTS. The previous 3/6 paraphrase
baseline is not fixed or claimed improved by remote storage. No generated skill
was activated and no new semantic model was installed in this stage.
