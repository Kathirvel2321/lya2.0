# LYA advanced brain: researched design and first implemented upgrade

Reviewed 2026-09-13. Owner reports Oracle Free Tier and collected API keys.
Oracle VM size/region, provider inventory and usable quotas remain unverified.
No credentials were displayed or used; no remote infrastructure was changed.

## Decision

Build a resource-bounded personal assistant with selective memory, explicit evidence,
feedback and tested skills. Human-inspired organization is useful; a biological
neural simulation is not the engineering target. No technique below guarantees
human judgment, consciousness or perfect accuracy. There is no universally best
stack without testing the owner's actual tasks, languages, resources and latency.

The current native UI has a brain dispatcher but still lacks real identity/approval
binding and an available model. More memory sophistication does not remove those
integration gates. Existing legacy API fallback code is not the new workflow's
configured model adapter. Collecting keys does not prove endpoints or quotas work.

## Research translated into decisions

| Primary source | Finding relevant to LYA | Decision and limit |
|---|---|---|
| [MemGPT](https://arxiv.org/abs/2310.08560) | Manage limited model context using external memory tiers | Retrieve selected evidence into a bounded context. This does not make context literally infinite. |
| [Generative Agents](https://arxiv.org/abs/2304.03442) | Memory, planning and reflection support simulated behavior | Separate experiences, learned lessons and plans. Believable behavior is not factual correctness. |
| [Reflexion](https://arxiv.org/abs/2303.11366) | Text feedback can improve later trials without updating weights | Propose lessons from observed results; retain provenance and require approval before promotion. The paper's benchmark results are not LYA results. |
| [Lost in the Middle](https://arxiv.org/abs/2307.03172) | Tested models can miss relevant evidence inside long contexts | Prefer a small relevant evidence pack; evaluate retrieval instead of dumping all memory. This historical result does not measure our chosen future model. |
| [GraphRAG](https://arxiv.org/abs/2404.16130) | Graph-based indexing and summaries support corpus-level questions | Keep a small local graph now; defer automatic entity extraction/community summaries until corpus-wide questions justify their indexing cost. |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | Built-in full-text indexing and BM25 ranking | Implement scoped RAM-only ranked search now. Lexical retrieval still misses synonyms and cross-language paraphrases. |

## First upgrade implemented in this task

`brain/notes.py` now builds a disposable in-memory FTS5 index from only the current
person's active, non-credential notes. It ranks by BM25 with label weighting.
Tokens are quoted rather than interpreted as caller-controlled search operators.
The database connection is closed after retrieval and no plaintext search database
is created on disk. RAM can still be paged by the operating system; this is not a
promise of forensic erasure or protection from a compromised running process.

Before: searching `art` could retrieve `cart`, and six lexical matches left no room
for a linked warning. After: full tokens determine matches; a six-result budget
reserves up to two places for linked notes, prioritizing declared contradictions
and dependencies. Corrected/forgotten notes cannot remain in a stale search cache
because the index is rebuilt. This does not detect contradictions automatically.
The model's separate character budget may still omit some retrieved evidence.

The engine limits reads to 2,000 notes and returns at most six. Empty/common-only
queries list recent notes by ID. FTS5 support was checked on this interpreter;
other builds lacking FTS5 fail visibly through the workflow's existing error path.
No dependency, embedding model or additional database service was installed.

Acceptance: **91 isolated checks passed; one online voice test skipped**.
New checks cover substring false matches, malformed search syntax, full-result
contradiction inclusion and correction freshness. Existing identity, expiry,
credential exclusion, UI, council and migration checks also passed. Evidence:
`review/2026-09-13-retrieval/results.json` and its suite logs. This small synthetic
suite proves these behaviors; it is not an overall intelligence benchmark.

## Target working loop (partly implemented, not a completion claim)

Request -> authenticated person -> permitted data scope -> task classification ->
ranked retrieval -> linked context -> evidence freshness check -> model or council
-> validate output/action -> concise answer -> observed outcome -> proposed lesson
-> owner-approved memory revision -> later retrieval.

The identity boundary, explicit notes, ranked retrieval, graph and bounded council
exist as code. Live evidence collection, observed-outcome capture, lesson proposals,
semantic retrieval and a skill execution pipeline are future work in this design.

A serious decision should produce: recommendation, evidence/source dates,
assumptions, material alternatives, unresolved disagreements and what would change
the recommendation. Store these public decision records rather than hidden model
reasoning. A second model is useful only if its measured benefit warrants its
latency and quota. Council agreement alone is not a truth test.

## Storage model and process

Retention and meaning are separate dimensions: an episode can be short-lived or
permanent; a fact may expire tomorrow. Avoid one database for each memory lifetime.

| Data class | Contents and proposed rules | Current status |
|---|---|---|
| Working/session | Selected evidence and bounded temporary notes | Implemented |
| Semantic notes | Facts, preferences, lessons, decisions; owner, kind, source, revision, expiry | Implemented with explicit saves |
| Episodic outcomes | Request summary, action, observed result, failure, timestamp, evidence IDs; no secrets or full transcript by default | Proposed |
| Evidence | Source URI, retrieved time, valid time, content hash, owner/scope and verification state; source content treated as data | Proposed |
| Lesson proposals | Supporting episode IDs, suggested revision, pending/accepted/rejected state | Proposed; model cannot approve its own lesson |
| Graph | Same-owner notes with supports/contradicts/depends_on relationships | Implemented, user-declared |
| Procedural skills | Versioned code, permissions, tests, approved version and rollback pointer | Existing legacy forge requires integration review; not active self-upgrading brain |
| Large files | Encrypted objects plus metadata/references, never pasted wholesale into prompts | Proposed for mobile/sync |

Next schema migrations should add evidence and episode tables only when their
capture/retrieval workflow is implemented. Tests must cover changed facts, invalid
sources, retracted evidence and deletion of derived summaries/indexes. Avoid
permanent confidence numbers generated solely by an LLM; record evidence state
and observed evaluation results instead.

The laptop remains the authoritative writer initially. Later mobile edits should
be submitted as authenticated operations with expected revision and idempotency
ID. Reject revision conflicts for review rather than blindly taking the last
write. An offline mobile client can access only previously downloaded/decryptable
content; it cannot fetch a laptop-only file over a nonexistent connection.

## Oracle: use actual capacity, not an old tutorial

[Oracle's current Always Free resource documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
lists A1 allowance as 1,500 OCPU-hours and 9,000 GB-hours monthly, equivalent to
2 OCPUs and 12 GB for Always Free tenancies. It also documents home-region capacity
constraints and possible reclamation of idle instances. The tenancy console is
needed to establish this account's actual entitlement; do not assume 4 cores/24 GB
from older guides. Free compute is not a promise of GPU inference or availability.

Proposed split, pending resource and privacy choices:

- Laptop: native orb, identity/approval, private canonical data, local retrieval,
  offline commands and optional local inference after a hardware-fit test.
- Oracle VM: authenticated API gateway, bounded background jobs and mobile relay.
  Keep backup copies independent of the VM; do not make it the sole copy of data.
- Object storage: versioned encrypted exports and selected files with tested
  portable key recovery. Existing Windows DPAPI protection alone is not portable.
- Selected AI provider: opt-in inference with minimal approved context, provider
  timeout, request/token budget and clear failure. No silent cross-provider private
  data fallback. Provider keys remain server-side or in protected local storage.

Do not synchronize a live SQLite database through a cloud folder. Use consistent
exports and restore tests. Deploy no database port publicly. A VM budget/quota is
not an application spending cap: the model router must enforce its own request
budget and stop on rate-limit/quota failures instead of retrying indefinitely.
No deployment, remote backup or provider call was performed in this task.

## Delivery gates, in order

1. **Real conversation:** inventory provider names/models and Oracle VM resources;
   bind one explicitly selected model to the native brain and run public synthetic
   prompts. Pass timeout, offline, quota and cancellation checks. Do not claim
   personalized answers until identity/approval binding passes as well.
2. **Memory quality:** create an owner-approved synthetic question set covering
   Tamil/English paraphrases, changed facts, irrelevant notes and wrong-person
   access. Measure recall@6, stale/cross-person exposure, latency and cost. Compare
   current BM25+graph against embeddings+rank fusion before adopting the latter.
3. **Learning:** implement outcome records and reviewable lesson proposals; promote
   only approved proposals. Test failed tasks cannot silently become successful
   lessons and corrections invalidate derived context.
4. **Evidence and council:** add source retrieval with dates and document-instruction
   isolation; evaluate source support and unsupported claims. Keep bounded council
   for consequential/ambiguous requests rather than every greeting.
5. **Oracle/mobile:** authenticate, encrypt exports, prove restore with recovery
   material and simulate VM loss/network outage. Verify quotas before deployment.
6. **Skill evolution:** generate a proposed skill in isolation, run mocked tests,
   inspect permissions, activate a version and support rollback. A camera skill
   cannot silently add enrollment or recording simply because it generated code.

No additional API account is requested yet. The immediate missing information is
which providers are already configured and what Oracle VM actually exists.

## Research tooling provenance

Read the requested agent-reach skill and its search/web routing references. Its
agent-reach/mcporter CLI commands were not discoverable on this shell, so public
primary sources were read through the available web search tool. No social login,
cookie extraction or workspace credential upload was used. Agent-reach's version
check could not run without its CLI; no update was installed. Generated project
artifacts follow AGENTS.md and remain in the workspace for continuity.
