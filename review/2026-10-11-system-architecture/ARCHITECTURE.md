# LYA full architecture contract

2026-10-11 - proposed target, not implemented. Read alongside RESEARCH.md,
CAPACITY.md and IMPLEMENTATION.md. The owner requested a detailed design before
implementation. Existing private memory placement approval is still pending.

## A. Product invariants and platforms

One logical assistant means the same authenticated owner, memory revision rules,
approved style and capabilities contract across devices. It does not mean a single
mutable session or identical hardware capabilities. Laptop and phone get separate
turn IDs, streams, cancellation and device grants. A simultaneous phone question
must not cancel unrelated laptop work or mix their private context.

| Platform | Responsibility | Technology and status |
|---|---|---|
| Windows laptop | Native orb/panels, microphone, private vault, local inference and allowlisted device execution | Existing Python/PySide6, Fernet/DPAPI and llama.cpp paths retained |
| iPhone | Thin familiar interface, consented foreground audio, verification and transient results | Existing HTML/CSS/JavaScript/private HTTPS; no intentional retained chat/model/photo database |
| Oracle Linux host | Shared identity mapping, orchestration, authoritative selected memory and bounded background workers | Existing Ubuntu host/private ingress; new Python service and PostgreSQL/pgvector are proposed |
| Public model/speech providers | Eligible public generation and consented speech recognition | Reuse qualified routes; availability, privacy and quota checked per route |
| Independent recovery location | Restore after Oracle loss or corruption | Owner-controlled encrypted destination outside Oracle plus offline copy; not provisioned |
| Future native iOS adapter | Supported App Intents/Shortcuts and notifications | Separate project gate; neither needed for shared facts nor promised by a website |

Keep a modular Python application, with process separation at actual trust/resource
boundaries: UI gateway, memory/orchestration service, database, heavy worker and
native executor. Boxes in the diagrams are responsibilities, not one microservice
per box. Reuse the current request validation/authentication code. Add a streaming
server dependency only if the existing server cannot safely support the selected
protocol. No Kafka, Kubernetes, Redis, graph cluster or agent swarm is required by
the first complete system.

## B. Identity, ownership and trust

The server derives `principal_id` from a verified session; it never accepts a
client-supplied role/name as proof. A device grant binds its credential, owner,
allowed operation, resource scope, expiry and revocation generation. Sensitive
operations use fresh, request-bound authorization, preserving current proof rules.
An owner greeting is presentation; it cannot grant memory or tool access.

The first memory domain is `shared_personal`: NEW selected records explicitly
approved for Oracle placement. Existing `local_private` data remains in the laptop
store and cannot be silently sent to the shared service. Public research remains
in `public_archive`, with separate credentials. Credentials and biometrics belong
to a `secret` domain excluded from conversational memory. Unknown sensitivity is
private until resolved. Changing a label cannot erase the source's restrictions.

The proposed shared service and its host are trusted to decrypt/search shared
personal records. It is not end-to-end encrypted against Oracle. Server-side
search and server-blind encryption are different designs. If server-blind privacy
is required later, encrypted client-side retrieval/key custody must be designed,
and the laptop-off/no-phone-content constraints will limit the available behavior.

Use a local database socket, no public database port, separate OS accounts, narrow
database roles, explicit storage permissions, encrypted volume/backups and
revocable device sessions. TLS does not encrypt database files. Database encryption
does not protect against a compromised running service. Indexes, embeddings,
temporary files, checkpoints and crash diagnostics inherit the same sensitivity.

## C. One request, from hearing to reply

1. A device creates a request ID and sends text, or captures audio after consent.
   Privacy mode must be selected before sending audio to a public ASR endpoint.
2. Resolve identity/project, validate lengths/codec/rate limits, assign a deadline
   and attach cancellation. Uncertain or unfinished speech must not authorize an
   action. Existing pause behavior stays until a replacement passes owner tests.
3. Choose a lane: deterministic command, explicit memory operation, recall,
   public conversation, private local reasoning, or an authorized longer task.
4. Retrieve only eligible active facts and evidence. Direct recall may answer
   without an LLM. Private reasoning on the laptop follows its local path.
5. Compile bounded context and select an eligible model. Public prompts contain
   no personal memory. Model outputs remain proposals until checked.
6. Validate source support, tool outcomes and current request identity. Stream
   checked sentence chunks only after streaming has passed its separate gate.
7. Speak with the accepted Amy voice. Cancellation discards pending chunks and
   stops playback; remote provider cancellation is best effort, not a billing claim.
8. Enqueue permitted indexing/maintenance separately. Ordinary chat does not become
   a durable record because it reached a model or appeared in a checkpoint.

For user-facing latency, record both time since last speech and time since confirmed
turn end. Hiding endpointing delay from the metric would misrepresent responsiveness.

## D. Memory selection, forms and retention

| Memory class | Exact durable form, if permitted | Policy |
|---|---|---|
| Raw speech / frames | None by default; bounded RAM buffers | Discard after processing/cancel; no voice archive |
| Working/session context | Bounded typed in-memory messages | Session expiry/restart; current session limits retained |
| Episodic event | Approved concise event row plus approved source reference | Explicitly pinned event, not every exchange |
| Fact / preference / decision | Typed relational row with JSONB value, revision and evidence | Explicit save; 7/90 days, exact expiry or permanent |
| Inference / lesson proposal | Separate unconfirmed object in session, or separately approved task state | Never silently promoted; owner confirmation before lasting fact/skill |
| Entity / relationship | Scoped IDs and typed SQL edge rows with evidence and validity interval | Names do not identify people globally; no automatic merging across owners |
| Project knowledge | Source-backed public records or approved private records | Project and sensitivity preserved; source freshness recorded |
| Procedure / skill | Versioned source files, manifest, tests and activation state | Review and test before execution; no self-deployment |
| Persona | Versioned approved style plus allowed preferences | No invented history, permission changes or unrestricted system-prompt edits |
| Task checkpoint | Explicit task state and artifact references, encrypted when personal | Minimal progress needed for an authorized task; expire at agreed completion policy |
| Attachments | Encrypted original bytes; DB metadata/opaque reference and integrity hash | Explicit opt-in and quota; no existing photo/vault migration |
| Search projection | FTS index, optional model-versioned vectors and graph links | Rebuildable from authorized active sources; delete when parent expires |
| Operation diagnostics | Safe IDs, stage duration, sizes, status codes and versions | Proposed 7-day diagnostic detail; aggregates contain no content |

Storage retention and factual validity are distinct: an address could be valid
until September yet retained as approved history longer. `valid_from/valid_to`
express the world timeline; `recorded_at` expresses when LYA learned it;
`expires_at` controls retention. A late correction must not rewrite history as if
LYA had always known it. Forgotten private content overrides historical retention.

The database is authoritative. JSON is the API/export representation; JSONL is a
portable export stream only inside an encrypted package. Markdown is a readable
view for approved project material, not another writable private authority.
Binary embeddings use the database's vector type with a pinned dimension/model.
Audio transport currently uses bounded mono PCM16/WAV after browser conversion;
an Opus/WebRTC transport is an independently tested future choice, not a new store.

## E. Schema and transaction rules

The ER diagram is conceptual, not executable migration SQL. Every personal table
must carry or enforce owner/project scope, including relationship endpoints,
evidence links and jobs. Composite foreign keys prevent linking one owner's
record to another owner's source. A same-text hash never authorizes cross-owner
deduplication. Exact sensitive content hashes are protected metadata, not log IDs.

Use stable UUIDs, UTC timestamps, explicit type enums and bounded UTF-8 values.
See `memory-record.example.json` for a synthetic durable-record representation;
its owner and approval fields are server-derived, never trusted client input.
Unique `(principal_id, request_id)` handles retry deduplication. Correction requires
`expected_revision`; conflicts return a conflict result instead of silently
overwriting a newer device edit. Uniqueness for single-valued preferences is scoped
by owner/project/key. Multi-valued events are separate records, not accidental
overwrites of the same preference.

A successful save commits the active record, its provenance, immediate keyword
visibility and an outbox job atomically. Only then return the revision. Embeddings
may arrive later; the write is durable even if the indexer fails. A job checks its
expected revision before publishing so a late embedding cannot revive a deleted
or corrected value. Workers use leases, bounded retries and a failed-job state.
Delivery may repeat; effects must be idempotent. Do not claim exactly-once external
actions across a network failure: record the action intent/result and reconcile
uncertain outcomes before retrying a non-idempotent tool.

The ordinary device gets no raw SQL, arbitrary memory paths or model-written
authorization fields. API validation rejects unknown properties, invalid retention,
oversize content and unavailable storage domains.

Proposed API shape (names are a contract sketch, not current endpoints):

| Operation | Request essentials | Response essentials |
|---|---|---|
| `POST /v1/turns` | request ID, project, input, declared mode | streamed state/text/audio or bounded error |
| `POST /v1/memories` | request ID, kind, typed value, retention, approved domain | memory ID, committed revision, expiry |
| `POST /v1/memories/query` | query, project, time scope, bounded limit | supported records, evidence IDs, revisions; no reliable match is valid |
| `PATCH /v1/memories/{id}` | expected revision and correction | new revision, or conflict |
| `DELETE /v1/memories/{id}` | expected revision and scoped proof | committed deletion revision and backup-retention explanation |
| `POST /v1/turns/{id}/cancel` | device-bound active turn | cancellation acknowledgement |

Authentication determines the owner server-side for every operation. Query text
goes in request bodies rather than URL query strings that proxies might log.

## F. Retrieval and context compilation

Start with exact IDs/keys and PostgreSQL text search. English stemming cannot be
assumed to work for Tamil; compare a language-appropriate/simple tokenizer and
Unicode-normalized literal matching. Normalization must preserve names/meaning.

The qualified hybrid path runs scoped keyword and semantic candidates, plus
bounded relationship/time lookup where relevant. Fuse ranks with a transparent
method such as reciprocal-rank fusion; prefer active owner-confirmed facts and
direct evidence over inferred summaries. Similarity is not a probability of truth.
Use a reranker only if it improves held-out recall enough to justify latency.

Proposed initial limits: 20 candidates per retrieval method, at most two relation
hops, 50 visited relationships, 6 final memory items and a 2,000-token evidence
budget. These are test settings, not deployed defaults. Broad questions may need
explicit multi-step research with a larger budget; ordinary chat should not fan
out into multiple model calls. Sources that disagree remain distinguishable.

The context compiler orders: fixed policy, approved style, authorized task state,
selected evidence with IDs/times, current request and small recent context. Token
allocation is relative to the actual selected model window, with output reserve.
Do not silently truncate a request or a critical source condition. Compress only
with provenance and a way to retrieve an approved original. No full-history dump.

A cache key includes owner, project, operation policy, memory revision, query
normalization and embedding/model version. TTL never exceeds source expiry.
Revoke/correct/forget invalidates relevant entries. A global cache keyed only by
question text is prohibited for personal results. No private prompt cache at a
public provider. A stale unavailable answer is preferable to returning another
person's cached fact.

## G. Model, speed and voice strategy

The fastest accurate response often uses no model: exact recall, arithmetic and
fixed actions take the direct lane. Retain the existing public generation route
and provisional local private route until a measured alternative wins. Define a
small capability record per configured model: supported modalities, structured
output, measured context limit, privacy class, streaming support, deadline, token
budget, failure domain and last evaluated version. This keeps memories portable
when technology changes without building a generic provider marketplace.

Separate interactive work from background extraction/indexing. At first allow one
heavy background job and two admitted text turns, with bounded queues and visible
busy responses. Preserve the existing single-heavy-audio behavior until measured.
Keep a model/voice worker warm only after its steady/peak memory fits its own cap;
previous long voice fixtures nearly filled the existing 256 MiB service. Do not
raise that limit silently or assume retained models cost no memory.

Streaming prototype order: public text chunks, sentence-safe Amy audio chunks,
stale-turn cancellation, then separately qualified streaming ASR/turn detection.
Never execute a speculative tool action before the complete request and approval.
Speculative text can waste provider quota, so it stays disabled until it improves
measured latency without worsening interruptions. Full-duplex audio needs echo
handling and real Safari tests; changing a pause timer alone is not the solution.

## H. Learning and task execution

The original eight neural layers map to input adapters, session state, selected
events, typed facts, reviewed skills, approved persona, verification and background
maintenance. They are responsibilities rather than eight neural networks.

A lesson cycle is: observe an authorized task result -> propose a concise lesson
with evidence -> owner approves scope/retention -> test on a new case -> store the
confirmed lesson. A skill change is source code: isolate, inspect, test, version,
approve activation and retain rollback. No unattended model weight training,
credential changes or policy rewrites are part of ordinary learning.

Long tasks checkpoint minimal state and artifact references. Resume revalidates
identity, tool scope, external state and deadline. A previously approved operation
does not authorize a different action after a context or parameter change.
Retrieved websites, documents and memories never become executable instructions.

## I. Durability, deletion and failure behavior

Use durable database transactions; do not weaken fsync/synchronous commit to meet
a benchmark. Monitor free space, WAL growth, failed jobs and backup age. Expiry is
enforced on reads immediately even if physical cleanup is delayed. Permanent
memories are never silently dropped for quota pressure.

Start with consistent daily encrypted logical backups and tested object manifests.
Move to qualified base backups plus WAL archiving when a recovery requirement
justifies it. Copying live database files is not a backup method. Backup destination
and credentials must be independent of the live service. Keep the latest deletion
register independently so old recovery copies cannot resurrect forgotten values.
Missing deletion state requires reconciliation before serving restored memory.

Deletion removes the active value, history that policy requires removed, embeddings,
search/cache entries and eligible attachments; retain only minimal opaque deletion
metadata. Backup generations may retain old content until expiration/pruning.
Do not promise immediate secure erasure from SSDs or immutable historical copies.

| Failure | Required behavior |
|---|---|
| Laptop asleep | Shared approved memory works if Oracle is reachable; local-only memory/actions unavailable |
| Oracle/network unavailable | Laptop local capabilities continue; phone reports unavailability; no fake successful save |
| Public provider fails | Direct recall still works; only prequalified privacy-compatible fallback may run |
| Private model unavailable | Explain limitation; never export the private context |
| Indexer delayed | Committed exact/keyword records remain readable; semantic projection reports lag |
| Disk full / quota reached | Fail new save clearly; preserve existing committed records |
| Conflicting device writes | Revision conflict; reconcile rather than last-writer data loss |
| Device revoked | Reject further operations and invalidate relevant cached authority |
| Crash after external action | Reconcile recorded intent/result; do not blindly repeat |
| Restore from older backup | Enforce latest deletions/expiry, revoke old sessions, ensure only one active writer |

## J. Operations, upgrades and acceptance

Use safe event IDs and stage histograms. Measure p50/p95/p99, not only one fast
example. Record queue time, cold/warm retrieval, time to first text/audio, provider
failures, false interruptions and unsupported recall. No raw prompts/audio/notes
in ordinary diagnostics. A full observability stack is optional; begin with local
bounded metrics and add OpenTelemetry export only to an approved destination.

Pin dependencies/model/tokenizer versions and artifact hashes. Changes first run
against synthetic isolated stores; schema upgrades take a verified backup and
reversible staging copy. Compare old/new recall on held-out fixtures before
switching indexes. Read-only shadow evaluation can compare versions without
double-writing live personal stores. Revoke the old writer at cutover. Preserve
compatible export formats so replacing a model cannot strand years of memory.

Implementation gates, performance targets and practical capacity are in the other
two documents. A full diagram is not proof of integration, uptime, privacy or speed.
