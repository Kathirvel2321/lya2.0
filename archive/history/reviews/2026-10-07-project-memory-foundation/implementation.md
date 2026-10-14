# Project memory foundation — implemented first build unit

Date: 2026-10-07. Owner authorized starting the distributed memory/skills build
from the 2026-10-06 researched plan and asked to check existing Oracle configuration.
Status: connected native code and isolated integration tested; real owner-session
acceptance and remote storage deployment are still pending.

## What changed and why

Added explicit project namespaces to the existing encrypted memory store. A label
such as `framework` can now exist in ordinary personal memory, `app-builder` and
another project without overwriting or retrieving the other project's value.
The new path supports save, recall, correction, forgetting and within-project
relationships. Project notes remain private and require the existing verified
owner and exact-operation approval; a project name is not authorization.

This is the compact local record foundation for future remote evidence/artifacts.
It does not offload existing data or install a new model, database or daemon.
All existing notes default to the empty project namespace and keep their previous
retention. Ordinary conversation and unprefixed memory commands retain their
existing paths. Temporary session memory remains as previously implemented;
project-prefixed session saves are explicitly unsupported in this build unit.

## Native examples

After actual owner verification and required operation approval, use the text
input for these structured commands. Live voice parsing of this new colon grammar
has not been accepted.

```text
project app-builder: remember long framework = FastAPI
project app-builder: recall framework
project app-builder: correct framework = Django
project app-builder: forget framework
project app-builder: show memories
project app-builder: link 12 depends_on 13
project app-builder: show graph
```

The link example needs actual note IDs from that same project. Project IDs contain
1–64 ASCII letters, numbers, underscores or hyphens, normalized to lowercase.
Default personal memory uses the existing commands without a project prefix.
No automatic project inference, task learning, public export or skill activation
is performed. Unknown/malformed explicit project commands stop instead of becoming
model-directed actions. Ordinary requests such as `project ideas for a simple game`
continue through the existing conversation route.

## Files and boundaries

- `storage/store.py`: additive `project_id` field and owner/project/expiry index;
  shared namespace validation; person/project-scoped raw recall and forgetting.
  `get_person` now uses a read-only transaction. Its previous pure lookup rewrote
  the encrypted database during permission checks, including denied requests.
- `brain/notes.py`: project-scoped save/duplicate detection, FTS candidate selection,
  graph expansion, linking and recall. Filtering precedes selected-body decryption;
  both relationship endpoints must have matching owner/project, kind and expiry.
- `brain/workflow.py`: explicit scoped memory prefix through the existing operation
  authorization. Approval receives the entire original command, including project.
  Project recall excludes ordinary session notes and returns deterministic evidence.
- `brain/capabilities.py`: one owner-appropriate command example in existing help.
- `storage/recovery.py`: project-aware selected-note payload v2; mixed scopes can
  retain identical labels safely. Ordinary-only exports still use v1, and legacy v1
  archives remain readable. Restores preserve namespaces, revisions, deadlines and
  relationship scopes, into an empty verified profile only. Recovery labels identify
  new project records without redesigning the UI.
- `test_project_memory.py`: 11 focused isolated project/legacy/approval/archive checks.
- `test_recovery_ui.py`: one additional native file-to-new-key project restore check.

There is one existing encrypted store and one existing search index, not a database
per project. The existing 2,000-note/person cap includes every project; creating
projects cannot bypass it. The six-note retrieval limit is retained. Profiles,
keys, sensors, accepted hearing/output/UI choices and provider defaults are not
changed by this storage feature.

Project boundaries are application/query boundaries inside the same trusted local
process and encrypted file. They are not independent cryptographic compartments
or an OS sandbox. Existing lower-level APIs remain trusted-controller APIs, not
an authorization interface exposed to model-generated code. Friend/delegated
project permissions and a full independent security audit are not implemented.

## Migration and recovery

The schema addition uses a constant empty-string default. On read-only transactions,
needed schema/index changes are only in RAM and the source ciphertext is unchanged.
An ordinary write persists the additive metadata through the existing authenticated
encryption, lock and atomic replacement. A synthetic pre-project store was checked
for unchanged read bytes and preserved legacy data after a new project write.
[SQLite column-addition rules](https://www.sqlite.org/lang_altertable.html).

No real owner store was opened/migrated in this development run. Before live data
acceptance, verify an independent recoverable backup and the owner/approval journey.
Project archives use the existing authenticated envelope with payload schema v2;
older readers fail closed on that payload. Rolling code back to pre-project query
code after saving project data would lose query separation, so retain compatible
readers and recover deliberately. Never overwrite the sole live store during a drill.

## Checks and measured limits

| Check | Result |
|---|---|
| Project, FTS/search, selected-note recovery, native brain and exact approval suites | 73 passed |
| Existing storage and offscreen native recovery UI suites, with disposable key injected before imports | 19 passed |
| Total isolated acceptance/regression checks | 92 passed |
| Seven affected Python files compiled without bytecode writes | Passed |
| Scoped Git whitespace check | Passed; CRLF normalization notices only |
| Fake-store project lookup at 2,000 total notes | Seven warm reads: median 15.984 ms, max 18.134 ms |
| Fake encrypted database size | 1,296.1 KiB |
| Profile/recall read disk immutability | Passed |

The project tests were first run before implementation and failed, establishing
that the new commands/scopes were missing. The next run exposed the existing
profile-read rewrite, which was corrected at the shared lookup. Final suites passed.
An ordinary-project-conversation regression was added to avoid reserving every
sentence that begins with `project`. Its verified-owner expected route follows
the existing private conversation path, not a new public routing policy.

Tests cover identical labels across scopes, cross-owner/project canaries, malformed
IDs/queries, correction, expiry, budget, cross-project edges, exact original-command
approval, guest/nonliteral denial, session change/revocation during approval, v1/v2
archives, authenticated invalid project metadata, new-key recovery, native UI recovery
and pre-project compatibility. Fake keys, fake profiles and disposable stores only;
no real enrollment, microphone/camera collection or provider inference.

Timing is synthetic keyword retrieval, not semantic/paraphrase quality, cold startup,
production p95, sustained CPU/RAM, full-app hearing/model latency or user accuracy.
The prior 3/6 paraphrase baseline is not claimed fixed by project namespacing.
No new large model/dependency/background service was installed. The resource and
read-only readiness evidence are saved separately in JSON.

## Oracle readiness actually checked

The existing local Oracle configuration, key-file presence and pinned host file
were valid. A read-only SSH probe using the existing identity/host pin succeeded;
it reported aggregate CPU/RAM/free-space information and the expected inference
file's presence. No inference API was called, no remote file was written, and no
owner memory/artifact was uploaded. Host/key names, credentials and raw error
messages are excluded from `oracle-readiness.json` and the continuity ledger.

The VM is running and reachable. Linux resource capacity is not proof of tenancy
free-tier quota, billing eligibility, IAM isolation or an independent backup.
Those remain required before cloud storage is enabled. Existing inference code
and its routes were left intact. No browser login or new cloud credentials were
requested. Public technical documentation was reviewed through Agent Reach's
Jina-reader route and the official SQLite page; no private runtime corpus was sent.

## Next build unit

1. Actual owner/operation-approval and independent recovery acceptance remain the
   private-data gate; this run does not perform biometric enrollment or bypass it.
2. Verify Oracle free eligibility and storage/IAM/backup allocation. Then build one
   separate public artifact archive/search path using synthetic public data first,
   with bounded local cache/outbox and outage/deletion/restore checks.
3. Evaluate semantic retrieval against the saved exact/paraphrase fixtures before
   claiming natural-language recall accuracy. Skills remain draft/test/review/activate
   work after these foundations; generated code activation is not connected yet.
