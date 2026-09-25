# LYA model strategy and controllable reasoning workflow

## Update — 2026-09-19: independent backup and private local model

- **Public primary:** Groq `openai/gpt-oss-120b` remains the only active cloud route.
- **OpenRouter candidates:** the adapter accepts only an exact `:free` model, pins the upstream with gateway fallback disabled, requests routing metadata and verifies the selected provider. Live synthetic checks rejected both tested routes: NVIDIA Nemotron 3 Ultra became slow and truncated, while DeepSeek V4 Flash on OpenInference repeatedly missed the first-case deadline. Both remain disabled. OpenRouter is public-data only; its free pool is rate-limited and not a production SLA.
- **Direct NVIDIA candidate:** `nvidia/nemotron-3.5-lightning-30b-a3b` failed the first case at the eight-second deadline from both laptop and Oracle, even with thinking disabled. It remains disabled.
- **Private local route:** official Qwen3 4B Q4_K_M is the best tested fit currently installed on this 8 GB laptop. It runs via CPU-only llama.cpp and keeps prompts on loopback. It scored 5 pass, 1 partial and 2 fail, so it is provisional for secret conversation and cannot be called excellent for coding, Tamil or important decisions without T03 verification.

OpenRouter or any hosted API must never receive secret/private content. The local route fails closed. Research/model pages used for this decision: [OpenRouter free models](https://openrouter.ai/collections/free-models), [OpenRouter pricing](https://openrouter.ai/pricing), [OpenRouter privacy](https://openrouter.ai/privacy), [NVIDIA Nemotron 3.5 Lightning](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b), and [Qwen3 4B GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF).

## Live update — 2026-09-14, after credentials were saved

Public-text `openai/gpt-oss-120b` through Groq is now active on Oracle and selected
by the native desktop. An actual Qt-worker request returned a correct synthetic
answer through that complete path. Private context is denied by all cloud routes.
The cloud-text footer makes the connection visible; restart LYA to select it.

The original shortlist below is historical. NVIDIA's current
[DeepSeek V4 Flash 0731 page](https://build.nvidia.com/deepseek-ai/deepseek-v4-flash-0731)
and authenticated catalog confirm `deepseek-ai/deepseek-v4-flash-0731`, replacing
the earlier DeepSeek V3.2 candidate in our disabled template. Catalog visibility
did not establish usability: generation timed out from the laptop and Oracle.
[NVIDIA GPT-OSS 20B](https://build.nvidia.com/openai/gpt-oss-20b) answered a simple
test but failed later latency checks. Its route remains disabled too. There is
currently **one active provider**, not a dependable working independent backup.

Groq's account also lists [Qwen 3.8 27B](https://console.groq.com/docs/model/qwen/qwen3.8-27b),
but our comparison stopped at HTTP 429; it is not activated. The NVIDIA Nemotron
candidate timed out and a listed Mistral endpoint returned 404. We have stopped
expanding the active lineup based solely on catalogs or published benchmarks.

**Accuracy is not solved:** eight completed GPT-OSS 120B evaluation responses
included unsupported architecture claims and a faulty generated code assertion.
Stronger system instructions did not eliminate these failures. Model proposals
remain advisory; no generated deployment scripts/security code were installed.
The purely computational coding samples were reviewed before isolated execution.

See [live evidence and limitations](review/2026-09-14-live-models/README.md).
The protected active configuration has a 100-attempt daily cap, a 2048-token
completion cap, and no private-memory destination. The attempt cap is not a dollar
cap. Full account billing/quotas and future private-data policy still need review.

Current verification: 41 isolated checks passed, a real native desktop request
passed, and private-route denial passed. Voice, identity and storage replication
were not activated. The earlier pending-credential sections below record the
preceding stage and are superseded by this live update.

Research and implementation: 2026-09-14. Owner clarified **Groq**, not xAI Grok.
The aim is a dependable assistant that can change providers without changing its
identity, permissions or memory rules. We have not established a universal best
model, and no model-quality benchmark has been run on the owner's accounts.

## Recommended starting lineup

| Job | Candidate | Why evaluate it | Gate before activation |
|---|---|---|---|
| General reasoning, planning, advisory security and council | `openai/gpt-oss-120b` through Groq | Reasoning and structured-output capabilities; existing Groq code path | Account model access, quota, output budget and Tamil/English evaluation |
| Independent provider backup | `deepseek-ai/deepseek-v3.2` through NVIDIA | Different model family and hosting provider; NVIDIA catalog listing | Actual API access, hosted-service terms, latency and quality checks |
| Coding, debugging and recreating interfaces | `Qwen/Qwen3-Coder-480B-A35B-Instruct` through a verified hosting provider | Coding-specialized model published by Qwen | Determine an available provider/model ID; run repository tests on generated changes |
| Optional fast, low-complexity conversation | A smaller Groq model after catalog verification | Reduce latency and quota consumption if measured quality is adequate | Do not add another route until it improves the benchmark |
| Future images/video | A separately evaluated multimodal model | Text-only routing does not add vision | Camera authorization, supported image protocol and visual accuracy tests |

These are shortlist decisions, not claims that all three accounts work or that
these are the newest/best models globally. The Qwen route is not enabled or placed
in the runnable template because its hosting provider is not verified. The NVIDIA
route is also a disabled candidate. A model's public catalog listing does not
prove this account can invoke it or that sufficient free credits exist.

Primary sources:

- [Groq GPT-OSS 120B capabilities](https://console.groq.com/docs/model/openai/gpt-oss-120b)
  document text reasoning and tool/structured-output support. These capabilities
  do not enable LYA tools automatically or establish its answer accuracy.
- [NVIDIA DeepSeek V3.2 catalog](https://build.nvidia.com/deepseek-ai/deepseek-v3_2/deploy)
  identifies the candidate; [NVIDIA's FAQ](https://docs.api.nvidia.com/nim/docs/product)
  describes hosted endpoints for prototyping. Treat the API catalog as a resource
  requiring entitlement/terms verification, not guaranteed permanent production
  capacity. This is not installing NVIDIA inference on the Oracle ARM CPU.
- [Qwen's model card](https://huggingface.co/Qwen/Qwen3-Coder-480B-A35B-Instruct)
  describes coding specialization and long-context/tool support. Published model
  benchmarks are not measurements of this LYA workflow or hosting provider.

## Provider, model, gateway: different responsibilities

- A model produces an answer. A provider hosts a model. A gateway forwards a
  request to one or more providers. Having five gateways does not mean having
  five independent sources of uptime or expertise.
- [Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/index)
  can select an upstream automatically or accept an explicit provider suffix.
  LYA requires a pinned provider suffix for this route. HF-to-Groq and direct
  Groq must share the same failure domain; they are not independent backups.
- [HF pricing](https://huggingface.co/docs/inference-providers/pricing) currently
  lists $0.10 monthly credits for free users, subject to change. This is useful
  for experiments, not a budget for an always-on assistant.
- [OmniRoute](https://www.omniroute.online/) is a gateway with its own routing.
  We must verify the owner's actual installation/version, endpoint and upstream
  policy. Nested automatic fallback can multiply attempts and cross privacy
  boundaries. LYA requires an explicitly pinned upstream declaration; gateway
  settings must make that declaration true. It cannot prove a third party's
  behavior from a model name or self-reported response alone.
- "Tokenroter" is still unidentified. No endpoint or model inventory is guessed
  and no credential is sent to a similarly named service.
- Groq generally does not retain inference content by default, with documented
  exceptions and optional zero-data-retention controls. Verify actual account
  settings; do not describe it as an unconditional privacy guarantee.
  [Groq data handling](https://console.groq.com/docs/your-data)

## What LYA controls

The stable executive workflow is: identify user -> check permission -> interpret
task -> retrieve scoped evidence -> select eligible model route -> produce an
answer or proposal -> check evidence/identity/cancellation -> return result ->
explicitly save an approved correction or lesson.

We control task rules, prompt versions, context selection, tool permissions,
retention, provider policies, budgets and acceptance tests. These changes shape
behavior; they do not give us arbitrary control of third-party model weights or
guarantee obedience through prompting alone. The code must enforce permissions.

Task classification currently uses inspectable keyword rules for general,
coding, research, security and council. It is a starting heuristic, not a trained
intent classifier. Every route declares supported tasks; no eligible route means
an explicit error. A research-classified request still does not run web research.

The model proposes; a separate future executor must validate and execute tools.
Coding requires tests and review. Interface recreation requires visible-reference
inspection and UI checks. Security work requires target scope and evidence. No
tool executor, scanning service, remote command skill or autonomous self-modifying
code is enabled by this routing change.

## Implemented backup behavior

`cloud/router.py` and `cloud/inference.py` implement:

1. Filter enabled routes by task and private-context approval.
2. Require declared upstream failure domains; avoid trying the same domain twice.
3. Atomically reserve a daily attempt from SQLite. Attempts include failures and
   persist across SSH processes. Default is 100/day UTC; configurable up to 1,000.
4. Try at most two eligible providers. Each call gets at most eight seconds of
   socket timeout within an 18-second routing window. Desktop SSH timeout is 30
   seconds. These are bounded application controls, not a remote-compute SLA;
   socket timeouts are not guaranteed whole-request wall-clock limits.
5. On timeout/unavailability, 408, 429 or selected 5xx, cool down the upstream and
   try an eligible independent backup. Cooldown is 60 seconds for 429, otherwise
   30 seconds; it is not a substitute for the provider's actual quota reset.
6. Do not fail over for invalid credentials, bad input, filtered/refused content,
   malformed output or a truncated completion. A refusal expressed in normal text
   is a valid response, not a routing failure to bypass.
7. Return a safe route ID and attempt count alongside successful text. No prompt,
   credential or model reasoning is stored in the router's state database.

Privacy defaults are restrictive: unspecified sensitivity is private; routes need
`allow_private: true` for private context. Brain marks requests with authenticated
personal context as private. Public means no private context was retrieved by
Brain; it is not a detector that proves user-typed text contains no sensitive data.
The current desktop stays a guest until real identity/approval binding is ready.

Provider adapters support Groq, NVIDIA, HF chat and an explicitly configured
OmniRoute chat endpoint. Custom endpoints require HTTPS, except explicit loopback
HTTP for a local gateway. Redirects are rejected to avoid forwarding credentials
to a different endpoint. Remote configuration is trusted operator input, never
derived from a retrieved document or model output.

Council still uses three perspectives plus synthesis. Routing may change providers
on failures, but it does not deliberately assign independent models to seats yet.
There can be up to eight attempts for a full four-call council request. Agreement
is not verification. Deliberately diverse seats are a separate evaluation gate.

The counter is an attempt cap, not a dollar cap. Model prices, completion budgets,
provider account spending limits and possible gateway-internal attempts must all
be checked before enabling paid routes. A provider outage still does not protect
against an Oracle outage or lost internet. Local implemented commands remain the
degraded mode; a local generative fallback has not been installed or benchmarked.

## Current evidence and deployment

- 13 router tests, 5 bridge tests and 20 brain tests passed: **38 targeted checks**.
  They use fake providers, temporary state and mocked SSH/network. Tests include
  concurrent budget reservation, cooldown persistence, wrong-privacy denial,
  failure-domain deduplication, deadline/attempt caps and context classification.
- Real Oracle smoke check passed with synthetic primary failure and backup success.
  Earlier backend preserved as `inference.before-router.py`. `router.py` and the
  updated inference script are deployed, but there is no active provider file.
- The template `cloud/provider.example.json` has every route disabled, empty API
  keys and private context disallowed. It is not an enabled production configuration.
- `cloud/probe_models.py` found no usable Groq, NVIDIA or HF credentials in known
  project/environment settings. Therefore no authenticated catalog was retrieved
  and no live generation request was made. Keys may exist elsewhere in the owner's
  accounts; this result is limited to the inspected configured locations.
- `diagrams/13-provider-routing.mmd` validated with no errors/warnings. The Mermaid
  import trace also confirmed inference -> router. The diagram describes tested
  code paths and explicitly marks live-provider verification pending.

## Next acceptance gates and storage order

1. Identify protected credential locations, the actual OmniRoute endpoint and
   Tokenroter's exact URL. Verify provider model catalogs, entitlement and limits.
2. Run the synthetic rubric in `cloud/model-evaluation.json` against accessible
   candidates. Record model/version/provider/date, pass/fail, answer support,
   p50/p95 latency, token use and errors. Select routes from results, not slogans.
3. Set private-data destinations and spend limits explicitly; only then enable
   the tested primary and an independent backup and connect the desktop.
4. Add research tools and a scoped executor with validation/rollback. Compare
   diverse council seats against a single good model before paying for every seat.
5. Then extend the existing memory system with evidence records, episode outcomes
   and reviewable lesson proposals; preserve owner, source, validity time, expiry
   and correction lineage. Never auto-promote model guesses to permanent facts.
6. Prove encrypted backup restore and mobile offline behavior separately. Existing
   laptop encrypted memory and graph remain in place; they were not rebuilt here.

The brain is not finished merely because routing works. These are the remaining
gates to the user's all-round assistant, with model failures now explicitly handled.

Research tooling: used the requested agent-reach skill/references. Its CLI and
mcporter were unavailable on this shell, as was the version-check command. Used
built-in web access to primary sources; no plugin update, social login or cookie
access. Project artifacts follow AGENTS.md continuity rules.
