# LYA data, identity and answer routing — research decision, 2026-10-06

Status: researched proposal using current source and dated project evidence.
No production code/default, owner enrollment, private data migration, key read,
sensor capture, provider inference or deployment was performed. Only public
document research, a disposable fake-data benchmark and continuity artifacts.
The owner asked for the order, selected tools/platforms and structure before
building; recommendations below are not newly activated features.

## Recommended order

1. **Confirm the existing data contract and recoverability.** Keep the native
   encrypted store; map which active feature writes which record, distinguish
   legacy stores, and check backup/restore with fake records before touching real
   data. This foundation already exists, so do not rebuild it or move all files
   into a new service. A real off-device, verified recovery bundle remains an
   owner-operated acceptance step before entrusting valuable records.
2. **Finish actual device-owner registration/sign-in and protected approvals.**
   Reuse `desktop/registration.py` and `security/windows_consent.py`; current
   source has an in-process Windows verification path, so the historical blocked
   standalone helper is not proof that today's path fails. Verify one stable
   `person_id`, restart/sign-in, expiration, guest denial and revocation. Device
   registration does not require inventing a face/voice enrollment journey.
   Existing private-memory/tasks policy also requires exact-operation approval;
   admin registration alone does not bypass that gate. A trusted phone adapter
   and real approval round trip are still missing live acceptance. Leave
   biometric enrollment deferred until separately requested.
3. **Accept one complete personal-memory journey.** Verified owner + required
   approval -> explicitly save a harmless note -> restart -> retrieve -> correct
   -> forget -> prove guest isolation. Test recovery and stale indexes too.
   Fix the observed failed stage only; retain accepted hearing, voice and UI.
4. **Then refine answer routing and speed on the same pipeline.** Ordinary
   deterministic requests avoid inference; direct saved-fact recall avoids a
   generative model. Public requests use the existing public model/research
   route. Private context never takes public fallback. Benchmark natural intent
   variations and instrument capture, recognition, retrieval, provider time,
   rendering and first audio separately before changing accepted behavior.
5. **Add broader search/decision models only against measured failures.**
   Paraphrase recall may justify a small local semantic index; fuzzy tool intent
   may justify a Laya experiment. Neither is needed to create the owner record
   or organize encrypted notes. Public provider backup also needs real quality,
   quota and latency acceptance; adapters/templates alone are not accepted backup.

The storage design comes first, but collecting all real personal data before
identity/permission and recovery acceptance is not the next safe product step.

## Current source evidence

| Area | Current implementation | What this does not establish |
|---|---|---|
| Native chain | `desktop/experience.py` / `desktop/app.py` -> `brain/workflow.py` | Every owner interaction being accepted end to end |
| Personal records | `storage/store.py`: encrypted SQLite, local data root, atomic replacement, thread/process locking, scoped records | Recovery on a different Windows account or all legacy stores unified |
| Notes/search | `brain/notes.py`: explicit save/correct/forget, retention/revisions, FTS5 ranked retrieval, bounded one-hop relations | General semantic/paraphrase recall or an unlimited file knowledge base |
| Authorization | `security/policy.py`, `security/approval.py`, `Brain._authorize` | A role label or a model recommendation granting access |
| Admin flow | In-process Windows consent + device-admin profile/session code | Live owner sign-in today; no private profile was inspected here |
| Private action approval | Exact challenge adapter boundary; denies without verifier | Complete iPhone approval journey |
| Public model | Recorded Groq GPT-OSS 120B through opt-in Oracle SSH bridge; current source retains that split | Current deployment/accounts/quotas verified in this research |
| Private model | Loopback-only local client; recorded Qwen3 4B is provisional, not auto-started | Reliable low-load private generative answers on this laptop |
| Speech/camera | Accepted NVIDIA hearing/Amy output retained; local camera now owner-gated | Independent speech-provider outage coverage, biometric identity, live camera accuracy |
| Recovery | Selected-note archive and external portable-key/store bundle tools exist with fake-data evidence | A real verified off-device recovery copy or full cross-account restore |

Important current limitation: `Brain.respond` automatically attempts authorized
personal recall for a verified session before its generic model path. With no
live exact-operation approval adapter that branch can remain locked; with
private context the model path stays local. Public and personalized response
selection needs explicit acceptance before any routing refinement. Do not make
private recall automatic in cloud prompts to appear faster.

## Selected tools and platforms

| Responsibility | Use now / preserve | Deferred option and trigger |
|---|---|---|
| Windows UI/process | Existing Python + PySide6 | No second dashboard/framework |
| Owner authority | Existing Windows consent -> verified LYA session -> policy/required approval | Face/voice only after a separate enrollment contract |
| Hearing | Existing NVIDIA Parakeet TDT v2; NVIDIA-hosted Whisper model backup | A separately qualified provider if shared NVIDIA outage coverage is needed |
| Speaking | Accepted local Amy/Piper output | No change for this architecture review |
| Durable personal data | Existing authenticated whole-file encrypted SQLite | Client/server database only if remote multi-device concurrent writes actually require it |
| Search | FTS5/BM25 within that same encrypted file, scoped before presentation | Local embeddings/hybrid retrieval after paraphrase-quality and resource evaluation |
| Public answers | Existing Groq/Oracle route, one model per ordinary request | Independent free-eligible provider after actual acceptance and hard limits |
| Research | Existing bounded primary-source adapter and claim verification | More sources only when an accuracy benchmark demonstrates need |
| Private reasoning | Deterministic recall/calculation first; qualified local inference only on explicit need | Larger local models only after memory/latency/quality checks |
| Decision routing | Existing native rules/command registry | Laya as a measured classifier candidate; not an authority or answer model |
| Recovery | Existing encrypted portable bundle + verified independent copy | Cloud backup only with explicit destination/consent; no plaintext personal sync |
| Phone | Exact-request approval role | Multi-device replication is a separate design/acceptance stage |

Oracle is optional compute/transport here, not the source of truth for private
memory. The protected active provider configuration was not read. Preserve its
qualified model selection rather than replacing it from a public catalog.
Keep the existing shared project-root `.env` configuration for provider keys,
per the owner's rule; do not copy keys into conversational memory or the ledger.
An attempt/token cap is not itself a monetary cap: only verified free-eligible
routes with no paid fallback qualify for the owner's zero-cost policy.

### Jev versus Laya

Both return structured decisions rather than conversational answers or storage.
They could suggest a route; authorization remains native code.

- **Jev:** hosted text decision API. Its official model page lists input billing
  at $0.042 per million tokens, not an unlimited free deployment. No account
  entitlement or trial allowance was checked. Exclude it from the default
  zero-spend/private route. [Official introduction](https://docs.typesafe.ai/introduction),
  [official models/pricing](https://docs.typesafe.ai/models).
- **Laya:** open-source candidate for later local classification. Its own
  README reports near-chance base typed-decision performance and warns about
  overconfident probabilities and negation failures. Domain qualification,
  calibration and CPU/memory measurement must precede adoption; upstream GPU
  latency is not laptop latency. No package/model was installed.
  [Author repository and limits](https://github.com/NandhaKishorM/laya#honest-limits).
- **Jev Ultrafast:** a browser agent using Jev plus a text helper. It is not a
  memory backend or replacement for the conversational brain.
  [Maintainer repository](https://github.com/browser-use/jev-ultrafast).

Decision: use **neither as the default today**. Keep rules now; prefer evaluating
local Laya later if fuzzy routing is the demonstrated bottleneck and it beats
the existing path on held-out LYA cases within laptop resource limits.

### Storage alternatives researched

SQLite's own guidance favors device-local applications with low write
concurrency; FTS5 supplies indexed text search. LYA adds encryption around its
database; SQLite/FTS5 alone do not encrypt personal records.
[SQLite selection guidance](https://www.sqlite.org/whentouse.html),
[FTS5 documentation](https://www.sqlite.org/fts5.html).

Supabase is a potential future server/sync backend, not the default personal
vault. Its current free plan has finite database/file allowances and pauses
inactive projects after one week. Its docs recommend free-plan users export
their own off-site backups. Moving there would introduce network availability,
permission rules and replication work without fixing owner verification.
[Pricing](https://supabase.com/pricing),
[backup requirements](https://supabase.com/docs/guides/platform/backups).

Qdrant/FastEmbed is a candidate if semantic-retrieval experiments prove value;
it introduces embeddings/index lifecycle and needs resource/privacy checks.
It is not required for the current 2,000-note keyword-retrieval workload.
[Official semantic-search guide](https://qdrant.tech/documentation/fastembed/fastembed-semantic-search/).

DPAPI usually binds decryption to the Windows logon/computer. Therefore simply
copying `lya.db.enc` is not a portable recovery solution. Keep the current key
location and prove the independent recovery flow before any key migration.
[Microsoft DPAPI behavior](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata).

## Proposed data organization

One stable `person_id` owns related records; directories are not a permission
mechanism. Existing local runtime root is `%LOCALAPPDATA%/LYA` (unless explicitly
configured otherwise), separate from project source and model binaries.

| Data | Structure and handling |
|---|---|
| Profile/session | Identity/role/active record; expiring verified session, not an admin checkbox |
| Conversation | Bounded temporary context; no automatic archival of every utterance/answer |
| Saved fact/preference/lesson/decision | Explicit owner-requested note; owner, source, revision, timestamps, retention/expiry; current cap 2,000 notes/person |
| Task | Separate structured encrypted task record/status; task completion verified by its handler |
| Files/documents | Authorized encrypted content or scoped file reference; future chunk index links to source/version; no automatic disk crawl |
| Research evidence | URL/excerpt/retrieval time and claim status; distinguish evidence, inference and proposal; persistence is opt-in and needs its own schema |
| Learned workflow | Versioned reviewed definition, allowed tools, tests and rollback; not executable because a model generated it |
| Camera/audio | Transient by default; no auto-memory/image uploads from this plan |
| Secrets | Existing credential configuration/protected vault; excluded from ordinary notes/indexes/logs |
| Audit | Minimal action/outcome metadata; no private prompt, biometric, key or raw recording |

Profiles, notes, tasks, approvals and bounded recall have code. Future document
chunks, persistent evidence and learned workflows are a **target schema**, not
claimed integrations. Existing key supports new and legacy protected locations;
do not move/delete either without recovery evidence. Whole-file transactions
still deserialize the DB in RAM, so this is a bounded personal store, not a
large-media or high-concurrency server design. Existing search-schema migration
requires explicit opt-in after verified backup; no real migration was performed.

## Answer and saving patterns

See [pipeline.mmd](pipeline.mmd). It is a proposed control pattern mapped to
existing modules, not proof that every live acceptance gate passed. Import traces
from `desktop/experience.py` and `brain/workflow.py` were checked; dynamic imports
need the manual source review used here.

1. Capture the complete request and reject uncertain/truncated hearing.
2. Select the candidate intent; apply session/privacy/permission rules before
   private retrieval or execution. A classifier never grants authority.
3. Use only relevant, current, person-scoped context; exact recall can return
   saved records without a language-model call. Keep private data out of public
   inference and external research. Private speech still requires text if
   the current accepted local recognizers cannot handle it reliably.
4. Run a bounded local tool, a single public model, or an explicitly selected
   evidence-backed research/complex-decision path. No council on every turn.
5. Check actual tool results, source support, revision/expiry, session changes
   and cancellation; ask for clarification or abstain when evidence is missing.
6. Display/speak through the existing interface. A generated answer is not a
   new fact and is never automatically permanent memory.
7. Only an explicit save/correct request crosses the write gate: validate ->
   atomic encrypted transaction plus matching index update -> return record
   confirmation. Forget removes the active record/index; older backups need
   separate retention handling, not a false promise of universal erasure.

Fast does not mean routing every question through more models. Correctness
comes from scoped facts, explicit sources, verified tools and abstention.

## Fresh measurement and proposed acceptance budgets

The previously reviewed `review/2026-09-24-brain-strategy/bench_retrieval.py`
was rerun unchanged in an isolated process, using a disposable Fernet key and
temporary encrypted SQLite files. Five warm reads per dataset:

| Notes | Median | Maximum |
|---:|---:|---:|
| 100 | 2.05 ms | 2.19 ms |
| 1,000 | 4.13 ms | 4.77 ms |
| 2,000 | 6.48 ms | 7.39 ms |

[Saved aggregate result](retrieval-benchmark.txt). This proves only retrieval
of one planted matching fact in the synthetic indexed fixture. It excludes
recognition, approval, model/network delay, cold startup, simultaneous writes,
legacy migration, paraphrase quality and sustained full-app CPU/RAM/power.
No guarantee of 6.48-ms recall for arbitrary real data.

Proposed gates, not current live timings:

- Indexed synthetic recall p95 <50 ms at the existing 2,000-note cap, plus a
  representative correctness suite including paraphrases/missing/expired facts.
- Zero unauthorized reads/writes, wrong-person disclosures or accepted stale
  actions in the security regression cases; critical failure blocks release.
- At least 95% correct route-or-clarify decisions on a held-out natural English
  intent set, with no negated/private commands executing through uncertainty.
- Measure recognized-text visibility separately from model completion/first
  audio. Set their budgets from an owner-accepted baseline; do not lower the
  accepted slow-speech pause to disguise inference delay.
- Wrong-passphrase/corrupt-backup failures preserve existing stores; restore
  must reproduce notes, corrections, expiry, index and permissions before use.
- No paid fallback, unbounded retries, continuous unrequested perception or
  silent personal-data transmission. Verify current account allowance before
  activating any additional provider.

## Research method and remaining limits

Agent Reach's documented Jina public-reader route fetched the author Laya
repository and TypeSafe introduction; web browsing checked the listed primary
official sources. `agent-reach`, `mcporter` and `gh` remain unavailable on PATH,
so CLI doctor/update checks were not possible. No install, login, browser cookie,
private account or key action was used. Ignore independent marketing mirrors
that present themselves as official TypeSafe/Laya services.

Research and a fresh synthetic retrieval benchmark are complete. Live admin,
phone approval, portable recovery, private generative quality and current
provider redundancy remain unverified. Immediate next development scope:
**storage/recovery baseline verification, then device-admin/approval acceptance,
then one saved-note end-to-end journey**. No new biometric setup or runtime
change is authorized by this research report alone.
