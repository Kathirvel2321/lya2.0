# LYA distributed memory and skills: research and build contract

Date: 2026-10-06. Status: researched proposal, not deployed or connected to LYA.
Owner scope: reduce laptop data/pressure; organize private, temporary, people,
project and skill memory; retrieve relevant evidence quickly; learn from work.
Working voice, hearing, UI, provider keys, startup and camera policy are preserved.

## Decision

Use a small trusted laptop core with remote bulk storage and background work.
Keep the existing encrypted SQLite store for identity and bounded personal memory.
Use Oracle, after actual account/capacity checks, for public research, approved
public code/skill artifacts and search. Private/security archives may go remotely
only as client-encrypted objects under a separately reviewed transfer policy.
Keep their decryption keys and compact private search catalog local by default.

Start remote search with SQLite FTS5; add pgvector to a PostgreSQL replacement
only if semantic-quality or concurrent-write measurements justify that change
and the verified server has capacity. Do not run multiple search databases.
Obsidian is an optional readable view, Notion an optional sanitized project
dashboard, and Excel an export. None becomes the permission authority or a
mandatory dependency in the answer path.

This extends the earlier local-first plan in
`review/2026-10-06-data-routing-plan/README.md` for the owner's broader distributed
storage request. It does not migrate existing stores or change today's routes.

## What the source actually supports today

| Component | Source evidence | Practical implication |
|---|---|---|
| Native store | `storage/store.py`: authenticated whole-file encrypted SQLite, RAM deserialization, atomic replacement and locking | Reuse for compact records; large attachments would enlarge every whole-file transaction |
| Memory | `brain/notes.py`: person scoping, FTS/BM25, bounded one-hop relationships, note revisions/expiry; 2,000 notes/person, six retrieved notes | Useful starting point; not an unlimited document archive or evaluated semantic search engine |
| Authority | `brain/workflow.py`: verified session plus operation authorization; generic personalized path asks for `memory_read` | Signing in alone does not remove protected-operation approval requirements |
| Key protection | `security/vault.py`: Windows-protected master key, existing recovery tools | A portable encrypted backup needs separately recoverable key material; a copied DPAPI file alone is not a tested cross-account recovery plan |
| Cloud inference | `brain/oracle.py`: opt-in public inference route | Existing Oracle inference is not proof that cloud storage/search/sync is deployed |
| Legacy sync | `brain/sync.py`: older databases/Supabase with a server-side passphrase flow | Not native-store replication; encryption with a remotely available key is not client-only confidentiality |
| Skills | `skills/forge.py`: draft generation and syntax checks; activation disabled. Native workflow explicitly blocks skill activation | Generated code is not a tested usable skill; keep activation gated |
| Legacy graph | `brain/knowledge.py` uses a separate old storage flow | Do not silently merge it into the active protected store |

These are source findings, not a live owner-session acceptance test. Real owner
sign-in, exact-operation approval, cloud backup/restore, multi-device sync and
native skill activation remain unverified or disconnected. Biometric enrollment
remains deferred. The shared project-root `.env` key method stays unchanged;
credentials never become memory records, skill examples or cloud note exports.

## Storage tools: where each one belongs

The decisions below are engineering recommendations for this project, not vendor
claims that a tool alone supplies a secure, accurate autonomous brain.

| Tool/platform | Useful role | Cost/resource/security boundary | Decision |
|---|---|---|---|
| Existing encrypted SQLite | Local identity, permissions, small private facts and catalog | Whole-file transactions need a bounded dataset | Preserve and reuse |
| Oracle block storage + VM | Public corpus, code artifacts, public indexes and background jobs | Finite free quota, capacity/reclaim risk; boot volume consumes allowance | Preferred remote candidate; verify account first |
| Oracle Object Storage | Client-encrypted private objects and backup snapshots | Smaller free allowance; encryption keys stay separate | Candidate archive, not the only recovery copy |
| Obsidian | Human-readable selected Markdown research/skill notes | Core app free; official Sync paid; local vault is not encrypted by Obsidian | Optional sanitized view; avoid duplicating the whole archive |
| Notion | Project decisions, task progress, review links | Remote API quotas/latency; workspace permissions are separate from LYA's authority | Optional sanitized dashboard; asynchronous export |
| Excel/XLSX | Inventory, storage/cost reports, task summaries | Workbook editing is not the transactional memory contract | Generate exports on request |
| Git | Public/sanitized code, recipes, versions, rollback | A repository is not a secret vault; history preserves old content | Use for approved non-sensitive skills/code |
| PostgreSQL + pgvector | Combined keyword/vector retrieval and concurrent remote metadata | Extra server operations and embedding cost; vector proximity is not factual truth | Upgrade candidate after evidence, not another parallel store |
| Qdrant | Dedicated vector/hybrid retrieval at workloads that need it | Another service/index lifecycle; policy filtering still required | Alternative to pgvector, not both |
| Supabase | Managed Postgres/API option if later needed | Current free database/file quotas and inactivity policy need account verification | Alternative, not a second primary sync engine |
| Mem0 | Memory extraction/search library on chosen infrastructure | LLM/embedder/storage configuration; graph memory adds a backend | Evaluate only if measured extraction benefits exceed cost/risks |
| Letta | Persistent-agent memory/workflow platform | Server/model/storage setup; custom-tool sandboxing must be explicitly configured | Architectural reference, not a replacement of accepted LYA |
| Graphiti | Temporal entity/relationship memory | Graph backend plus extraction/embedding services | Later candidate if relationship questions defeat simple links |
| LangGraph | Checkpoints and restartable workflows | Checkpointer infrastructure; side effects still need safe retry design | Learn its persistence pattern; native task records first |
| Restic | Encrypted snapshot backup to compatible repositories | Password recovery, quota, cache and actual restore testing required | Candidate once backup size/destination warrants it |
| Jev / Laya classifier | Typed routing decisions | Neither supplies durable memory, generative reasoning or authorization | Retain native rules; no new default classifier |

Obsidian's core app is free, while its official Sync starts at $4/month billed
annually or $5 monthly. Local vaults are unencrypted by the app even when remote
Sync uses end-to-end encryption. [Pricing](https://obsidian.md/pricing),
[security boundary](https://obsidian.md/help/sync/security).

Notion currently documents per-connection budgets of 180 requests/minute for
most plans and 600 for Business/Enterprise, plus shared workspace/endpoint
limits. This is another reason to keep dashboard synchronization out of a voice
answer's critical path. Its published security controls do not establish that
LYA retains exclusive decryption control over exported pages.
[API limits](https://developers.notion.com/reference/request-limits),
[security practices](https://www.notion.com/help/security-and-privacy).

Microsoft's workbook API supports relevant OneDrive Business/SharePoint files;
consumer OneDrive workbook API access is currently unsupported. Ordinary XLSX
exports do not require this integration.
[Excel API](https://learn.microsoft.com/en-us/graph/api/resources/excel?view=graph-rest-1.0).

PostgreSQL can combine full-text search with pgvector; approximate indexes trade
recall for speed and need filtering tests. Qdrant is a separate hybrid-search
alternative. Neither automatically supplies LYA's owner policy.
[pgvector](https://github.com/pgvector/pgvector),
[Qdrant hybrid search](https://qdrant.tech/documentation/search/text-search/hybrid-search/).

Mem0 permits self-hosted components; its graph option adds graph storage.
Letta's self-hosted server can use pgvector-equipped PostgreSQL and has explicit
tool-sandbox configuration. Graphiti requires a supported graph backend and
model services. Their documented features are reasons to evaluate them, not
evidence of accuracy on this owner's data.
[Mem0](https://docs.mem0.ai/open-source/overview),
[Mem0 graph](https://docs.mem0.ai/open-source/features/graph-memory),
[Letta](https://docs.letta.com/v1-sdk/docker),
[Graphiti](https://github.com/getzep/graphiti).

Supabase currently offers a 500 MB free database and 1 GB file storage, and free
projects can pause after inactivity. These limits make it an alternative for
small workloads rather than a reason to duplicate Oracle/storage services.
[Supabase pricing](https://supabase.com/pricing).
Jev serves billed typed decisions; Laya is an open-source classifier with author-
reported accuracy/calibration limitations. Neither is our retrieval/answer memory.
[Jev](https://docs.typesafe.ai/models),
[Laya author documentation](https://github.com/NandhaKishorM/laya#honest-limits).

## Oracle: realistic free capacity

The current official page lists A1 monthly allowance equivalent to 2 OCPUs and
12 GB RAM, 200 GB combined boot/block storage, five volume backups, and 20 GB
combined Object Storage for Always Free-only accounts, with 50,000 object API
requests/month. Boot storage consumes the block allowance. Idle compute may be
reclaimed; free shape capacity can be unavailable. Oracle warns that objects
over the 20 GB limit can all be deleted when a trial ends without an upgrade.
Do not budget from old 4-OCPU/24-GB tutorials or treat free VM disks as permanent
independent backup. [Current Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

LYA's actual tenancy, region, trial status, VM shape, remaining quota and backup
capacity were not inspected. A tiny AMD free VM and an available A1 VM are very
different hosts. No promise of zero cost, unlimited growth or always-on service
is justified until those checks pass. Stay on existing free-eligible resources;
do not upgrade or create a paid resource automatically. Quota enforcement must
stop/reject excess writes before billing or data-loss boundaries.

OCI encrypts objects server-side; SSE-C even sends the customer's key to the
service for encryption/decryption. For client-only private archives, encrypt
before upload and never send the archive decryption key to that server.
Use private buckets, narrow IAM and separate backup credentials; no public
object links or internet-exposed database ports.
[Object encryption](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/encryption.htm),
[Object Storage security](https://docs.oracle.com/en-us/iaas/Content/Security/Reference/objectstorage_security.htm).

## Memory types and locations

| Type | Example | Proposed lifetime and placement |
|---|---|---|
| Working memory | Current request and intermediate results | Bounded RAM; clear on end/cancel/lock. Crash dumps/swap are separate OS concerns |
| Session memory | Short conversation context | Bounded TTL; private unless explicitly sanitized; not an automatic full transcript archive |
| Task/project state | Goal, current step, files changed, test outcomes | Compact checkpoints; encrypted local control records; only authorized remote copies |
| Semantic memory | Owner-confirmed fact, preference or decision | Existing encrypted person-scoped notes with revisions, source and retention |
| Episode/lesson | What was attempted, failed, fixed and tested | Minimal structured summary linked to evidence, not every raw log |
| Procedural skill | Reviewed app-building recipe and tools | Versioned package; public/sanitized remote code, private variants encrypted |
| Research evidence | Official source excerpt, URL/date, code/doc reference | Public remote corpus plus small hot cache; refresh volatile claims |
| People data | Consented person's relationship or preference | Person namespace and authorization; no shared unrestricted people index or automatic enrollment |
| Restricted/security case | Sensitive finding, private code, incident details | Encrypted local compact index + client-encrypted archive, authorized on-demand local use |
| Credentials/biometrics | API key, authentication material | Existing protected subsystem; excluded from conversational memory and ordinary skills |
| Audit | Authorized operation, result, safe identifier | Bounded access-controlled event record; no private body, credential or biometric logging |

Unknown sensitivity defaults to private. A task called "research" is not
automatically public: a confidential repository, vulnerability or person record
stays protected. Sanitization is a checked transformation that creates a separate
record; it must not simply toggle the original record's privacy label.

Every durable memory record needs a stable ID, owner/project namespace, type,
sensitivity, source/evidence reference, creation/update time, content revision,
retention/expiry, approval state, and encryption/replication status as applicable.
Store artifact bodies separately from small metadata. Relationships use stable
IDs and modest relational links before adding a graph daemon. These fields extend
the future contract; not all exist in today's native schema.

### The unavoidable privacy/search choice

For public data, Oracle may read and index the corpus. For private/security data,
the default design lets Oracle hold ciphertext while the laptop retains keys and
a small encrypted catalog. Retrieval filters that catalog, downloads only needed
objects, verifies/decrypts them locally and uses authorized local tools/reasoning.
Remote identifiers should be opaque; object sizes/timing may still reveal metadata.

An ordinary cloud search engine cannot semantically index content it cannot
decrypt. Private embeddings, summaries and filenames can themselves reveal
information; they are not safely public merely because they are smaller.
If a future private corpus exceeds the compact local catalog, either accept more
local compute/storage, authorize a specifically trusted remote private processor,
or accept slower on-demand search. We cannot promise exclusive local keys,
arbitrarily large private semantic search, near-zero local work and instantaneous
answers simultaneously. No remote private processing is authorized by this report.

## Answer pipeline: correct evidence before fluent output

Privacy must be selected before sensitive input is captured. The current desktop
source already blocks online hearing in private mode and asks for typed input on
the NVIDIA-only route (`desktop/app.py`). Preserve that boundary: classifying a
transcript as private after cloud transcription cannot undo the audio transfer.
For security tasks use that private/text path until a separately qualified private
speech path exists. Storage encryption alone does not protect audio already sent
to a transcription service. This report does not alter accepted hearing behavior.

1. Check verified session, owner/project and operation permission. Private recall
   keeps existing exact-operation approval. Voice/name recognition is not authority.
2. Classify request and sensitivity with native rules; uncertain inputs stay private.
3. Resolve direct commands/calculations/explicit facts without unnecessary model calls.
4. Search authorized local hot records and, for public requests, the relevant remote
   project corpus. Apply ACL, expiry, deletion, revision and skill-state filters
   before ranking, embeddings, reranking, model prompts or caches.
5. Start with keyword/entity matches. Add semantic retrieval only after it beats
   keyword recall on real paraphrases at acceptable measured cost. Fuse candidates
   rather than dumping every stored document into the prompt.
6. Select a small evidence set with source/version/date and any contradictions.
   If evidence conflicts, show the conflict; freshness alone does not prove truth.
7. Use the accepted public route only with public/sanitized context. Private
   deterministic answers can work without a model; private generation still needs
   a separately qualified local route. Recheck authorization before answer/action.
8. Cite actual evidence and tool outcomes. Missing evidence should produce a clear
   limitation or focused follow-up, not an invented confident memory.
9. Save explicit owner facts and checked task lessons under their retention rule.
   Keep inferred candidates separate from confirmed facts; do not save every utterance.

Cache identities must include owner, project, sensitivity, content/index revision
and permission-policy version. A stale or cross-owner answer cache is a leak even
if the underlying database has correct permissions. Revocation, correction,
forgetting and expiry invalidate all affected projections and prompt caches.

PostgreSQL row-level security is useful defense in depth, but table owners and
superusers normally bypass it; a restricted application role and policy tests
remain necessary. [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html).
Web pages, imported documents and generated skills are untrusted task data;
their instructions cannot authorize tools or alter security policy.
[Prompt injection](https://owasp.org/www-community/attacks/PromptInjection).

## Laptop pressure and performance

Proposed first budgets: at most 256 MiB of evictable artifact cache, a separate
bounded session buffer, existing 2,000-note/person private-memory cap, and one
background ingest job. These are design starting limits, not implemented settings,
full-application memory limits or owner workload measurements. Protected identity,
keys and critical unreplicated writes cannot be evicted to satisfy a cache budget.
Reject/pause ingestion when reserved space or outbox limits are reached.

Fetch requested artifacts instead of synchronizing entire drives or Obsidian
vaults. Deduplicate by hash without conflating ACLs, version small summaries,
compress suitable text, and put bulk parsing/embedding on a qualified remote host.
Keep embeddings off the laptop initially. Pause optional background work during
interactive voice and resource pressure. Model files and the current application's
working set still consume storage/RAM; a 256 MiB cache does not bound all of LYA.

Fresh earlier isolated fixture on this date measured current native recall at
2.05 / 4.13 / 6.48 ms median for 100 / 1,000 / 2,000 notes (five warm reads each).
Evidence: `../2026-10-06-data-routing-plan/retrieval-benchmark.txt`.
It used fake keys/disposable stores and one exact-keyword planted fact. It does
not measure paraphrase accuracy, cold decrypt, network, owner approvals, full-app
load, answer-model latency or background concurrency. It establishes a small
local starting point, not "lightning speed" for the proposed distributed brain.

This task also adds a reproducible quality baseline in `check_memory_baseline.py`:
six synthetic facts, six exact-term questions and six hand-authored paraphrases.
Current retrieval found 6/6 exact cases and 3/6 paraphrases. The fixture also checks
six isolated boundaries: another person's canary absent, expired note absent,
unknown identifier absent, corrected old term absent, revision retained and the
current plaintext body absent from the encrypted file. See `baseline-results.json`.
These checks are not workflow authorization, network leakage, deletion/restore
or cloud integration tests. This tiny illustrative corpus cannot estimate real
owner accuracy. It does demonstrate the need to evaluate semantic recall instead
of assuming that a fast keyword benchmark solves differently worded questions.
No query, result or model output from the fixture was sent to LYA's answer route.

The first semantic candidate to evaluate is `BAAI/bge-small-en-v1.5`, an English
embedding model with MIT licensing and documented ONNX usage. Evaluate on the
verified remote host for public data, with pinned model revision and one embedding
job at a time. It is a search component, not an answer generator. Acceptance must
compare hybrid retrieval against keyword-only on the same scoped fixtures, including
irrelevant close matches; cosine similarity is not an answer-confidence percentage.
No download, installation, RAM estimate or speed claim is made here.
[Author model card](https://huggingface.co/BAAI/bge-small-en-v1.5).

Private synonym/paraphrase search remains a separate qualification: start with
owner-confirmed aliases and the compact private catalog, then evaluate bounded
local semantic work only if needed and affordable. Sending private queries or
their embeddings to the public remote index would violate this design. The
current keyword-only private path is not declared accurate for arbitrary wording.

Measure capture-end -> transcript -> authorization -> retrieval -> first answer
-> speech separately. For memory acceptance, proposed targets are p95 <50 ms
for warm bounded local lookup and <500 ms for a small remote metadata query on
the actual connection. These are targets, not results or total-response promises.
Quality gates should include paraphrases, exact technical identifiers, conflicting
facts, stale sources, no-answer questions, two owners and security canaries.
Target >=90% relevant-evidence recall@6 on the agreed fixture, 100% exact-ID cases,
and zero cross-owner/private-cloud leak cases; an empty correct answer must not
inflate ordinary retrieval success. Tune targets after baseline workload review.

## Skills: learning by working without uncontrolled self-rewriting

Learning here means retaining verified knowledge, procedures and lessons. It
does not mean retraining model weights after every conversation or treating
generated text as senior-developer expertise. Skills package what LYA can do,
with narrow tools and measurable checks; memory supplies project-specific context.

For "add an app-builder skill for this topic":

1. Define the actual task: platform, users, requirements, privacy, success criteria
   and allowed tools. Start with a narrow skill, such as a small web expense tracker,
   rather than an unsupported claim to build every kind of app.
2. Reuse existing project capabilities and maintained official documentation.
   Record source date/version/license and what was inferred versus tested.
3. Draft a concise recipe, required tool permissions, example code and checks.
   Generate only necessary files for this task; avoid downloading huge repositories.
4. Run static checks and useful functional tests with fake data in an isolated
   workspace. A Python audit hook or syntax check alone is not an execution sandbox.
   Any code-bearing generated skill must wait for a qualified execution boundary.
5. Preview a concrete result with test evidence and known limits. Owner-authorized
   activation binds the exact reviewed version/hash and its capabilities.
6. On real tasks, keep checkpoints, change summaries, test results and a rollback
   revision. Record failure lessons as scoped evidence, not universal rules.
7. Propose improvements as new drafts; revalidate before promotion. Never let a
   skill rewrite authentication, permissions, keys or its own activation gate.

Proposed states: DRAFT -> TESTED -> APPROVED -> ENABLED. FAILED/STALE/REVOKED
versions cannot supply executable tools. Documentation-only recipes may be read
as evidence; reading them never expands authority. A skill result records whether
checks were actually run, which environment/version was used and what remains
untested. See `app-builder-skill-draft.md` for a concrete non-executable package.

Long-running tasks need durable step state and incremental tests, rather than
relying on a model's last conversation window. Checkpoints and artifacts support
continuation, but retries must not repeat payments, messages or deployments.
[Agent harness evidence](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents),
[workflow persistence](https://docs.langchain.com/oss/python/langgraph/persistence).
These are reusable engineering patterns, not a claim to match another assistant's
capabilities or an instruction to install either platform.

## Backup, failure and deletion contract

Use one authoritative writer per namespace initially; updates carry a revision
and idempotency ID. Multi-device concurrent editing requires a later explicit
conflict design. A durable encrypted outbox holds authorized pending writes until
remote acknowledgement; no lost write or deletion just because the network fails.
Cap the outbox and stop accepting further durable saves with an honest status
when full. Checksums detect corruption but do not replace authenticated encryption,
permission checks or proof that retrieved content is factually correct.

Keep critical recovery outside the primary Oracle VM/account failure domain:
an independently accessible encrypted copy, using an existing suitable removable
drive or separately verified destination. No new paid backup purchase is assumed.
Prefer existing portable recovery for the small protected store; evaluate Restic
for larger snapshot archives rather than writing another backup engine. Restic
supports S3-compatible targets, but OCI endpoint/credential and restore behavior
must be tested with fake data before any real transfer.
[Restic repositories](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html),
[OCI compatibility](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/s3compatibleapi.htm).

Back up recovery material through a separate protected procedure; never put the
decryption key alongside its ciphertext as ordinary cloud files. Test restoration
on a disposable different-account/machine-equivalent environment. For "forget",
invalidate live caches/indexes and record an authenticated deletion revision;
backup retention may still contain older versions until expiry. Explain that
retention rather than claiming instant erasure of every immutable snapshot.

When Oracle is unavailable, use authorized cached facts, report missing/stale
evidence, and queue bounded writes. Do not invent absent content or send private
context to another provider. Different models on one provider do not cover that
provider's outage. Do not add artificial VM load to evade idle reclamation.

## Build order and acceptance gates

| Stage | Concrete deliverable | Required check before advancement |
|---|---|---|
| 1. Protected foundation | Existing-store recovery and actual owner/approval journey; agreed memory contract | Fake-store roundtrip, expiry/correct/forget, denied owner/approval, independent restore. Real sign-in separately accepted; enrollment stays deferred |
| 2. Remote public archive | One chosen Oracle host/destination, read-only search first, stable artifact IDs | Account/free capacity, private IAM, pinned SSH host identity, no public DB port; fake corpus upload/fetch/integrity/rollback; no private content |
| 3. Bounded cache + reliable writes | Small local cache, encrypted outbox, deletion/revision tracking | Crash/retry/outage/quota/conflict checks; never evict critical unacknowledged data; resource check alongside voice |
| 4. Retrieval and grounding | Scoped corpus search with sources; semantic upgrade only if needed | Paraphrase/freshness/no-answer/cross-owner fixtures; cold/warm latency; no restricted cloud prompts |
| 5. Skill registry | One app-builder documentation skill then one isolated tested code skill | Draft/test/review/activation/rollback journey; generated code cannot bypass permissions; no auto deployment |
| 6. Views and private archive | Optional sanitized Obsidian/Notion/Excel projections; ciphertext remote backups | Export leak tests, retention/deletion behavior, recovery on separate environment; explicit private-transfer policy |

Storage contracts and fake-data recovery checks can start before real enrollment.
Live private memory and camera still require the verified owner/approval flow.
We do not need a new public admin-registration system merely to draw this plan.
Do not migrate every legacy store before proving one native end-to-end journey.

## Research method, validation and boundaries

Read project continuity first, inspected relevant native/legacy source and the
prior architecture/recovery evidence. Agent Reach's public Jina reader was used
alongside primary vendor/author web documentation. `agent-reach`, `mcporter` and
`gh` were unavailable on PATH; CLI doctor/update were therefore unavailable.
No logged-in social accounts, cookies, cloud account, private recordings, owner
database or provider secrets were accessed. Public research queries were sent;
no private runtime corpus was transmitted. No models/services were installed.

Mermaid import trace was run on `brain/workflow.py`; it does not capture dynamic
imports/framework wiring. The accompanying architecture diagram marks existing
source components versus proposed connections explicitly. JSON parsing, contract
consistency and diagram syntax are checked separately in `validation.json`.
Document validation is not a security test, live integration test or model-quality
evaluation. The separate synthetic retrieval baseline has the narrower scope above.
No product code/default changed. Next implementation step is Stage 1,
with Stage 2 conditional on real Oracle capacity and destination verification.
