# LYA advanced master blueprint

**Version:** 2.0  
**Updated:** 2026-11-04  
**Repository:** `Kathirvel2321/lya2.0`

This document is the advanced engineering map for LYA. It is written for the
owner, maintainers and coding assistants that need to build one feature without
breaking another. It describes the current source organization, contracts,
request flows, security boundaries, status vocabulary, test strategy and merge
rules.

This is not a claim that every planned capability is working. The repository
source, current project brain and latest dated evidence remain authoritative.
When this document conflicts with newer source or evidence, stop, record the
conflict and update this document before implementing a risky change.

## 1. Authority and reading order

Read these in order before editing:

1. [`lya-project-brain.md`](../lya-project-brain.md) — binding owner
   requirements, current status, dated limits and work ledger.
2. [`LYA_VISION.md`](../LYA_VISION.md) — product direction and accepted
   desktop, phone, voice, privacy and authority choices.
3. This document — system map and integration contracts.
4. [`LYA_BLUEPRINT.md`](LYA_BLUEPRINT.md) — concise branch and handoff rules.
5. The relevant architecture guide, plan, source files and tests.
6. The newest `review/YYYY-MM-DD-*` evidence for the affected capability.

`archive/` is historical reference only. It is not a runtime, import or normal
test source. Dated review results are evidence for the revision they describe,
not proof of current deployment.

## 2. Product definition

LYA is one logical personal assistant with a native desktop presence and a
lightweight phone interface. Hands-free conversation is primary; typing is a
fallback. LYA should answer public questions, preserve explicitly approved
memory, research bounded public sources, prepare or execute narrowly authorized
tasks, and recover safely from interruption.

The product is not:

- a collection of unrelated legacy scripts;
- a face-recognition system whose result grants all authority;
- a model that can silently save its own answers as facts;
- a browser dashboard replacing the native desktop;
- a cloud data-export pipeline;
- proof of production readiness merely because an isolated prototype passes.

The owner requires a zero-subscription/free-tier direction, preservation of
accepted voice/hearing/UI behavior, explicit authority for private actions,
bounded resource use, fake-data isolation during development, and honest
classification of pending integrations.

## 3. Truthful status model

Use the narrowest applicable status:

| Status | Meaning |
|---|---|
| Specified | Requirement or design exists; implementation is not claimed. |
| Implemented | Source exists for the described behavior. |
| Connected | A supported client reaches that source path. |
| Isolated-tested | Synthetic/fake-data checks pass on a named revision. |
| Live-tested | A permitted real provider/device/runtime check passed. |
| Deployed | A named runtime/device is running that revision. |
| Accepted | Owner or responsible reviewer confirmed the behavior. |
| Pending | A dependency, device, approval, custody or integration step remains. |
| Blocked | Work cannot proceed without a named missing prerequisite. |
| Deferred | Owner intentionally postponed it. |
| Legacy | Retained compatibility or historical code, not a current path. |

Never convert `implemented` into `working`, or `isolated-tested` into
`deployed`, without the corresponding evidence.

## 4. Repository zones

| Zone | Responsibility | Do not assume |
|---|---|---|
| `brain/` | Conversation contracts, orchestration, memory, reasoning and shared commands | Every module is connected to the live desktop/phone path. |
| `cloud/` | Mobile HTTP service, model routing, research, automation and public services | A cloud helper has credentials, deployment or private-data authority. |
| `desktop/` | Native PySide6 application, visual experience, controls and desktop hooks | A UI check proves voice, model, camera or device acceptance. |
| `audio/` | Microphone, wake/interrupt, transcription, TTS and voice auth adapters | Speech recognition is accurate merely because audio was captured. |
| `security/` | Sessions, approval, passkeys, vault, liveness and audit mechanisms | Face/voice/name/color can replace exact approval. |
| `vision/` | Face embeddings, identity personalization and camera snapshots | Recognition is enrollment or confidential authorization. |
| `storage/` | Local encrypted stores, visitors and public archive boundaries | Public archive is safe for private data. |
| `skills/` | Bounded local actions and draft/guard helpers | A skill is authorized simply because a model requested it. |
| `docs/` | Maintained architecture, guides, plans and operator instructions | Documentation is runtime evidence. |
| `review/` | Dated evidence, runners and reports | A report from an older revision proves current behavior. |
| `archive/` | Historical source and evidence | It may be imported or executed during normal development. |

## 5. Runtime entry points

### 5.1 Native desktop

The native path is the primary visual interface:

```text
launch script
  -> desktop/app.py:main
  -> Desktop / Crystal / GlassPanel
  -> BrainJob background worker
  -> brain.workflow.Brain
  -> answer/panel/voice result
```

`desktop/app.py` owns presentation, worker signals, cancellation and safe
allowlisted document display. Slow model, file and voice work must remain off
the Qt UI thread. A dismissed panel must not be reopened by a late result.
Preserve the accepted orb/crystal body, visual states, voice and startup
choices unless the owner explicitly requests a change.

### 5.2 Conversation contract

`brain/conversation.py` defines fresh-context public turns for desktop and
phone. It creates a bounded context, binds session identity/expiry, executes a
turn, and rechecks cancellation and authorization before returning. Do not
create a second session or expiry policy in a feature module.

### 5.3 Brain workflow

`brain/workflow.py` is the model-facing orchestration boundary. Its important
responsibilities are:

1. Bind a verified session or report guest state.
2. Authorize the requested operation.
3. Select public/private/local/research/deterministic/council paths.
4. Retrieve only permitted context.
5. Invoke a bounded model or deterministic evaluator.
6. Verify evidence and output boundaries.
7. Return an answer without silently saving it.

Model output is advisory. It cannot grant permissions, create memory, claim a
tool ran, or turn an unsupported source claim into a fact.

### 5.4 Mobile

The supported phone path is the thin service/page represented by:

```text
cloud/mobile.html
  -> cloud/mobile.py HTTP/session boundary
  -> cloud/mobile_runtime.py inference/transcription/TTS/research adapters
  -> cloud/mobile_client.py client behavior
  -> brain conversation/shared-memory contracts where explicitly connected
```

Phone sessions, passkey proof, expiry, origin checks, cancellation and public
versus private routing are separate boundaries. The phone must not receive
server secrets, local model weights, private databases, credentials or
biometric material.

## 6. Capability map

### 6.1 Conversation and answer quality

| Capability | Main source | Current boundary |
|---|---|---|
| Public answer | `brain/workflow.py`, `cloud/answering.py`, `brain/oracle.py` | One bounded model route; source/evidence rules apply. |
| Local deterministic calculation | `brain/workflow.py` and related evaluator path | Use for bounded calculations rather than asking a model to invent arithmetic. |
| Public research | `cloud/web_research.py`, `cloud/web_reader.py`, `cloud/evidence.py` | Bounded queries/pages/time; fetched instructions are untrusted. |
| Answer verification | `cloud/answering.py`, evidence and evaluation fixtures | Unsupported claims must be removed, qualified or blocked. |
| Council | `brain/council.py` | Explicit request only; bounded perspectives/calls; agreement is not evidence. |
| Technology updates | `cloud/tech_news.py`, `cloud/news_sources.py`, `desktop/news.py` | Official/public sources, duplicate-safe notifications, no private access. |

### 6.2 Memory and shared state

| Capability | Main source | Current boundary |
|---|---|---|
| Local notes | `brain/notes.py`, `storage/store.py`, `security/vault.py` | Explicit save/recall/correct/forget; retention and identity scope apply. |
| Memory prototype | `brain/memory_prototype.py`, `brain/memory_repository.py` | Fake-data/isolated qualification; not automatically production. |
| Authority/writer fencing | `brain/memory_authority.py` and extensions | Generation, token, exact-anchor and recovery checks; legacy callers may remain unfenced. |
| Recovery/custody | `brain/memory_recovery*.py`, `brain/memory_custody.py` | Multiple fake-data drills exist; independent latest/key/custody and production use remain gated. |
| Shared desktop/phone commands | `brain/shared_memory.py`, `cloud/shared_memory.py` | Explicit commands and configured synthetic publication path; no general private-memory claim. |
| Public archive | `storage/public_archive.py`, `cloud/public_archive.py` | Separate public scope; never a private-memory export shortcut. |

Memory lifetimes are explicit: working context, session notes, short-term,
longer-term, deadline-based and permanent-until-deleted. Expiry excludes a
record from reads; it is not a forensic-erasure guarantee. Automatic chat
transcript storage is not implied by conversation.

### 6.3 Identity, sessions and approval

| Layer | Source | Purpose |
|---|---|---|
| Session policy | `security/policy.py` | Maps session role and phone approval to allowed actions. |
| Approval challenge | `security/approval.py`, `security/escalation.py` | Exact action/parameter/expiry/single-use approval. |
| Passkey ceremony | `security/passkeys.py`, `cloud/mobile.py` | Signed device/owner proof and expiry boundaries. |
| Local owner profiles | `storage/store.py`, `security/owner_profiles.py` | Protected owner/profile data and consent boundaries. |
| Face personalization | `vision/identity.py`, `desktop/familiarity.py`, `storage/visitors.py` | Low-risk personalization and owner-reviewed visitor handling. |
| Liveness | `security/liveness.py` | Separate anti-spoof dependency; not a general permission substitute. |
| Audit | `storage/store.py` and security modules | Bounded safe action/outcome records without secrets. |

Guest is the default. A display name, orb color, face similarity, voice
similarity or model statement cannot unlock confidential memory or execute a
protected action. Strong approval must be bound to the exact person, challenge,
action, parameters and expiry, then consumed once.

Enrollment and real biometric capture remain deferred unless explicitly scoped.
Never use real faces, audio, private notes or credentials in fixtures.

### 6.4 Voice, hearing and interruption

`audio/voice.py` owns speech activity, microphone capture, pause detection,
transcription adapters, TTS, stop-speaking, wake words, double-clap wake and
spoken interruption. `desktop/app.py` connects voice signals to the native
experience. Local and hosted adapters live beside it.

Required behavior:

- complete the spoken turn before answering;
- represent listening/thinking/speaking through the accepted interface;
- stop stale work and speech on spoken stop/interruption;
- preserve the accepted familiar voice;
- treat wake gestures as wake only, never identity;
- report uncertain/truncated recognition instead of treating it as reliable.

Audio capture, transcription quality, semantic completion and owner acceptance
are separate checks.

### 6.5 Automation and skills

`cloud/job_policy.py` defines structured limits and authority. `cloud/job_store.py`
persists run/action/outbox state. `cloud/job_runner.py` executes bounded jobs
through adapters in `cloud/job_adapters.py`. `cloud/routine_drafts.py` and
`desktop/routines.py` review/save/reopen/remove proposals.

A reviewed draft does not enable a job, connect an account, send a message,
approve private cloud access or install a timer. Default authority is deny.
`skills/` modules must be inspected individually; legacy skills are not proof
of current reachability.

## 7. Data and trust contracts

### 7.1 Data classes

| Class | Examples | Allowed default route |
|---|---|---|
| Public | General question, public source text | Bounded configured public model/research path. |
| Synthetic | Fake identities, fake secrets, temporary stores | Local isolated tests only. |
| Session | Current turn and explicit short-lived context | RAM/session scope; clear on expiry/change/lock. |
| Private | Approved notes, owner profiles, local vault records | Eligible local/private path only, with exact approval. |
| Credential | API keys, passkeys, recovery keys | Protected configuration/vault only; never model context or chat. |
| Biometric | Face/voice templates, photos, embeddings | Explicit consented protected path; enrollment deferred by default. |
| Recovery | Encrypted snapshots, latest-state trust, custody records | Separately scoped custody and recovery workflow. |

Never silently promote data between classes.

### 7.2 Persistence rules

`storage/store.py` owns the local SQLite schema and bounded records. It contains
people, profiles, memories, links, face/voice templates, pending visitor
records and audit events. New persistence must define:

- owner/person scope;
- project scope where applicable;
- retention/expiry;
- revision/conflict behavior;
- deletion/forget behavior;
- encryption and key custody;
- recovery and rollback behavior;
- test isolation and migration compatibility.

Do not introduce a new database, graph server, sync layer or serialization
format merely because a feature is easier that way. Reuse an existing contract
or document why it cannot satisfy the requirement.

### 7.3 Shared memory write contract

The explicit shared command path is:

```text
client command
  -> parse_command(text, request_id)
  -> authenticated/approved client request
  -> configured shared service
  -> publication/authority writer
  -> durable target/revision result
  -> client response after expiry/cancellation recheck
```

Supported semantic operations are save, recall, correct and forget. A label
must not silently target a later revision after an interrupted request; durable
resolved IDs/revisions and the original request ID are used for retry safety.
Missing or uncertain trust, stale grants and incomplete recovery refuse use.

## 8. Request-flow rules

### 8.1 Ordinary public text

```text
client input
 -> normalize/classify
 -> session/expiry check
 -> public route selection
 -> bounded history/context
 -> model call with timeout/cancellation
 -> answer/evidence validation
 -> presentation
```

No automatic private-memory retrieval or saving occurs.

### 8.2 Private memory operation

```text
explicit memory command
 -> verified person/session
 -> exact operation approval
 -> project/person/retention validation
 -> encrypted store or approved authority
 -> revision/idempotency handling
 -> expiry/cancellation recheck
 -> concise result
```

Guest, expired, revoked, mismatched or unapproved requests deny without
success-shaped fallback.

### 8.3 Public research

```text
research intent
 -> bounded query plan
 -> allowed public source adapter
 -> source identity and excerpt validation
 -> claim/evidence association
 -> synthesis
 -> citation/uncertainty rendering
```

Page instructions are data, not authority. Missing source identity, malformed
claims, quota exhaustion or timeout fails closed.

### 8.4 Protected action

```text
requested action
 -> classify sensitivity
 -> issue exact challenge
 -> verify approved person/device
 -> bind action + parameters + expiry
 -> execute one bounded operation
 -> record safe outcome
 -> consume/revoke approval
```

No model response, face greeting, voice phrase or color state can skip this
flow.

### 8.5 Cancellation and stale work

Every asynchronous path must define cancellation. A result is discarded if the
request was cancelled, the panel/session closed, identity changed, approval
expired, profile was revoked, or the result no longer matches the request.
Cancellation hiding a late result does not prove that a remote request was
physically interrupted.

## 9. Integration recipe for a new feature

Before coding, write a feature packet with:

1. observable owner outcome;
2. allowed files and out-of-scope files;
3. existing entry point and contract to reuse;
4. policy/data/storage boundary;
5. desktop, phone, voice and text surfaces;
6. failure, timeout, cancellation and retry behavior;
7. focused and regression checks;
8. evidence artifact location;
9. rollback approach;
10. exact next integration step.

Implementation order:

1. inspect current branch and uncommitted changes;
2. read brain, vision, blueprint and affected source;
3. add or update a fake-data contract test first where practical;
4. implement the smallest domain change;
5. connect only the named client entry point;
6. run focused checks;
7. run affected regressions;
8. update the relevant guide and current status;
9. append a dated brain-ledger entry;
10. review the diff for scope, secrets, authority and unrelated behavior.

## 10. Test and evidence contract

Every meaningful change reports each case as `PASS`, `FAIL`, `BLOCKED` or
`NOT RUN`, with environment and revision.

Minimum coverage:

- happy path;
- missing/unknown input;
- guest or denied authority;
- expiry/revocation;
- cancellation and stale result;
- timeout/dependency failure;
- retry/idempotency where writes exist;
- partial commit/recovery where durable state exists;
- privacy/data-class boundary;
- preserved existing behavior.

Use the smallest relevant runner. Read older scripts before executing them:
some historical tests touch real stores or external services. Use temporary
storage and fake credentials. Do not run blanket archive discovery.

Evidence must state:

- changed files and source hashes when useful;
- exact commands and results;
- what was isolated versus live;
- what was not tested;
- deployment/device status;
- known limitations and next step.

## 11. Dependency and deployment boundaries

Dependency presence is not integration. A missing package, model, certificate,
provider, device permission or account must be reported as a blocker or pending
prerequisite, not bypassed by weakening security or changing defaults.

Do not:

- install paid resources or resize infrastructure;
- upload private data or recovery material;
- connect real accounts or enable jobs without explicit scope;
- perform owner enrollment from a coding task;
- copy Windows-bound secrets to a phone or work-managed laptop;
- claim Oracle, iPhone, Windows Hello, microphone, camera or voice acceptance
  from Linux/fake tests;
- deploy merely because source tests pass.

## 12. AI coding-agent operating contract

Give another agent this instruction before its feature packet:

> You are working on `Kathirvel2321/lya2.0`. Read
> `lya-project-brain.md`, `LYA_VISION.md`,
> `docs/LYA_ADVANCED_MASTER_BLUEPRINT.md`,
> `docs/LYA_BLUEPRINT.md`, and every packet-listed source file before editing.
> Treat the current source and newest evidence as authoritative. Work only in
> the packet scope. Preserve accepted voice, hearing, UI, startup, privacy and
> authority behavior. Reuse existing contracts. Use fake identities, fake
> secrets and temporary storage. Do not inspect, print, request, commit or
> transfer secrets, private notes, biometric material or recovery keys. Do not
> import or execute `archive/`. Run focused checks and affected regressions.
> Report changed files, commands/results, implemented/connected/tested/deployed
> status, limitations, rollback and the next integration step. Do not claim
> production readiness without device/provider/deployment evidence.

The agent must stop and ask for clarification when the packet would require a
new authority model, new data class, behavior change to an accepted feature,
real enrollment, private transfer, paid resource, deployment, or a choice
between multiple reasonable product behaviors.

## 13. Merge gate

A branch is mergeable only when:

- the diff stays inside the packet;
- current working features are preserved;
- the required policy and failure paths are covered;
- no secret/private data/unintended dependency appears;
- focused checks and relevant regressions are recorded;
- docs and the project-brain ledger are updated;
- implemented, connected, tested, deployed and pending states are separated;
- rollback is clear.

A helper without an entry point, policy boundary, client behavior and evidence
is preparation, not a complete feature.

## 14. Current high-level status snapshot

The current project brain records substantial implemented and isolated-tested
foundations in routines, automation governance, technology updates, public
research, answer-quality routing, desktop presentation, mobile conversation,
shared commands, memory/recovery authority and witness protocols. The same
records also explicitly leave real device acceptance, production private
integration, independent custody/placement, live provider qualification,
deployment and several enrollment steps pending.

The most important rule for future agents is therefore:

> Build the next named connection or acceptance step; do not rebuild an
> already-qualified foundation and do not infer production readiness from a
> synthetic result.

## 15. Maintenance protocol

Update this blueprint when a meaningful task changes:

- a source-of-truth module or entry point;
- an authority/data boundary;
- a persistence or recovery contract;
- a supported client surface;
- a required dependency or deployment assumption;
- a status classification.

For ordinary feature work, update the feature guide and project brain instead
of duplicating detailed results here. Keep this document architectural and
stable; keep test logs and large outputs in dated `review/` artifacts.
