# Free / zero-subscription inference candidates for T02 — researched 2026-09-18

**Status: documentation only.** No account was created, no API key was used, no
provider was called, no route was enabled and nothing was deployed. Every figure
below is quoted from the provider's own documentation on 2026-09-18 (or from a
dated community dataset where marked). Re-check each number in the owner's own
account before activation: free tiers change without notice.

Related: `review/2026-09-17-T02-backup/README.md` (T02 evidence and rollback),
`LYA_MODEL_STRATEGY.md`, `cloud/provider.example.json`.

## 1. Why the previous shortlist is out of date

| Previously assumed | Verified 2026-09-18 | Source |
| --- | --- | --- |
| Cerebras has a generous free tier | **No permanently free tier.** "Free Trial" = $5 credits, expires 30 days after grant, and a **verified payment method is required** before Playground/API access is active | Cerebras rate-limits FAQ |
| GitHub Models is a free option | **Retired 2026-07-30.** Playground, catalog, inference API and BYOK are gone for all customers | GitHub Docs |
| SambaNova has a free developer tier | **No free plan.** The entry plan says "Add a payment method and purchase credits to run your first requests" | cloud.sambanova.ai/plans |
| Hugging Face Inference Providers as a backup | Free accounts receive **$0.10/month** in credits; PRO gets $2.00/month. Effectively unusable as a daily backup | HF pricing docs |
| Mistral free tier | A restrictive "Free mode" exists, documented as for evaluation/prototyping only; phone verification to activate; free tier is opt-in for data training | Mistral help centre |
| Cohere free keys | Trial keys are **evaluation only**; terms prohibit production/commercial use | Cohere docs (via dataset) |

## 2. Ranked candidates for LYA

Constraints applied: public text only (private routes stay denied), OpenAI-compatible
`/chat/completions`, **8-second provider allowance inside an 18-second window with at
most 2 attempts**, a distinct pinned upstream, and no paid subscription.

| # | Provider | Endpoint | Free models worth using | Documented free quota | Card / phone | Data policy | Independent from Groq? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **W&B Serverless Inference** | `https://api.inference.wandb.ai/v1/chat/completions` | DeepSeek V4-Flash-0731, GLM-5.3-Flash, Nemotron 3.5 Lightning 30B-A3B, Qwen3.6-35B-A3B, MiniMax M3, gpt-oss-120b, Llama 3.3 70B; also Kimi K2.6/K2.7-Code, Nemotron 3 Ultra 550B, GLM-5.2, DeepSeek V4-Pro | Free plan default cap **$100/month** of serverless credits (stated as a **limited-time** offer); 402 when exhausted, 429 on concurrency | No card (W&B account + API key + project) | **Not stated** on the pages read — unverified | Yes — different host, many non-Groq model families |
| 2 | **Google Gemini API (AI Studio)** | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | Gemini 2.5 Flash / Flash-Lite, 2.5 Pro (limited); current 3.x Flash family | Free tier exists ("free input & output tokens"); exact RPM/RPD/TPM are shown only on the **AI Studio rate-limit page, per project** | No card, no phone | **Free-tier prompts/outputs may be used by Google to improve its products** (outside UK/CH/EEA/EU); paid tiers are not used for improvement | Yes |
| 3 | **Z.ai (Zhipu / GLM)** | `https://api.z.ai/api/paas/v4/chat/completions` | **GLM-4.7-Flash, GLM-4.5-Flash, GLM-4.6V-Flash — listed at $0 input/cached/output permanently** | Rate-limit page returned 404 on 2026-09-18; confirm in the console | No card, no phone | ToS forbids using it to develop/train competing models; general/commercial use otherwise unrestricted | Yes |
| 4 | **OpenRouter** (`:free` pool) | `https://openrouter.ai/api/v1/chat/completions` | 25 free IDs on 2026-09-18, incl. `nvidia/nemotron-3-ultra-550b-a55b:free`, `deepseek/deepseek-v4-flash-0731:free`, `qwen/qwen3.8-27b:free`, `z-ai/glm-5.2:free`, `google/gemma-4-31b-it:free`, `poolside/laguna-*:free`, `openrouter/free` | **20 RPM and 50 requests/day** free; **1,000/day** once ≥9–10 credits have been purchased all-time | No card, no phone | OpenRouter stores nothing unless you opt in; per-endpoint retention/training varies and is classified per endpoint; `provider.zdr: true` enforces zero-retention routing | Yes **only if the upstream is pinned** (see §4) |
| 5 | **Cloudflare Workers AI** | `https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions` | Free-tier-eligible models only (Llama family, Qwen3.8 27B, QwQ-32B). Kimi K2.6/K2.7-Code, GLM-5.2/5.3/5.3-Flash, DeepSeek V4 Flash/Pro **require a paid plan** | **10,000 neurons/day**, resets 00:00 UTC | No card, no phone | **Strongest policy found:** Cloudflare does not train on, share, or use your content to improve services without explicit consent | Yes |
| 6 | **Groq** (existing primary) | `https://api.groq.com/openai/v1/chat/completions` | `openai/gpt-oss-120b`, `qwen/qwen3.8-27b` | **30 RPM, 1,000 RPD, 8K TPM, 200K TPD** per model on the free tier | No card; **phone verification at signup** | Groq's own published data policy | n/a — this is the primary |
| — | Also-ran | Typhoon (free Thai 30B, usage data collected to improve the model), Poolside Laguna (free "for a limited time"), Upstage Solar Pro 4 (promo), AI Horde / Pollinations (crowdsourced, no SLA) | — | — | — | — | Not recommended for a dependable backup |

## 3. Latency reality check — "biggest" is not "best" here

`cloud/router.py` gives each provider **`min(8, remaining)` seconds** (line 147) inside
an 18-second window, and stops after **2 attempts**. Very large mixtures-of-experts are
the most likely to miss that deadline — exactly how both NVIDIA candidates failed
(`provider_unavailable` at 8,001 ms). Prefer low-active-parameter MoEs on a second
provider:

- Good bets: **Nemotron 3.5 Lightning (3B active / 30B)**, **GLM-5.3-Flash (18B / 320B)**,
  **GLM-4.7-Flash**, **DeepSeek V4-Flash-0731 (13B / 284B)**, **Qwen3.6-35B-A3B (3B active)**,
  **gpt-oss-120b**.
- Likely deadline misses: DeepSeek V4-Pro (49B/1.6T), Kimi K2.7-Code (32B/1T),
  Nemotron 3 Ultra (55B/550B), GLM-5.2 (40B/744B) — useful for a quality comparison,
  not for an 8-second failover.
## 4. Integration recipe — a single pinned route needs no code change

`cloud/router.py` limits `PROVIDERS` to `{groq, nvidia, huggingface, omniroute}`, and
`cloud/inference.py` only maps fixed endpoints for the first three. The **`omniroute`
slot is an operator-configured endpoint**, so a new provider rides it. Requirements
taken from `validate_config`, `upstream()` and `infer()`:

- `provider: "omniroute"`, `endpoint` must be **https**, path must **end with
  `/chat/completions`**, and must have no query, fragment or userinfo.
- `upstream_pinned: true` plus a distinct `failure_domain` label
  (`[a-z0-9_-]{1,40}`). `upstream()` returns that label, and it is the label that
  makes the route count as a separate failure domain from `groq`.
- `api_key`, `model`, `tasks`, `allow_private: false`, `max_tokens` 128–2048,
  `enabled: true`.
- Payload uses `max_tokens` for non-Groq providers; all candidates above accept it.

Example (server-side `provider.json`, mode 600, never committed):

```json
{
  "id": "wanb-backup",
  "enabled": true,
  "provider": "omniroute",
  "endpoint": "https://api.inference.wandb.ai/v1/chat/completions",
  "upstream_pinned": true,
  "failure_domain": "wandb",
  "model": "nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B",
  "api_key": "<PROTECTED>",
  "tasks": ["general", "research", "coding", "security", "council"],
  "allow_private": false,
  "max_tokens": 1024
}
```

A second route for Z.ai uses `endpoint: https://api.z.ai/api/paas/v4/chat/completions`,
`failure_domain: "zai"`, `model: "glm-4.7-flash"`.

**Not supported without a code change:** OpenRouter's per-request pinning
(`provider.only`, `allow_fallbacks: false`, `provider.zdr: true`). `infer()` builds the
payload without a `provider` object, so an OpenRouter route **cannot currently be
certified as a pinned upstream**. Either add that small payload extension, or declare
`failure_domain` honestly and treat independence as unproven. Also note `route_request`
stops after **2 attempts**, so a third configured route is never reached in one request.

## 5. Acceptance plan before enabling (T02 gate, unchanged)

1. Owner creates the account; the key stays in protected configuration (never in git;
   server file mode 600). No key was created or used during this research.
2. Run the eight synthetic rubric cases (`cloud/evaluate_models.py`) against the
   candidate — public prompts only, no private memory, identity records or files.
3. Repeat three short checks within the declared limits and record per-request wall time.
4. Stage a temporary two-route configuration, force the primary to fail, and prove the
   desktop -> SSH -> Oracle path reaches the backup with public fixtures.
5. Only then enable backup. Rollback: unset the session flag first, restore the
   protected prior server sources, disable the new route. Never reset usage counters
   or delete memory as part of rollback.

A mock pass is not a live pass, and HTTP 200 is not an accuracy pass.
## 6. Unverified / open items

- Exact fast-failover latency for each listed model in this environment (only a live
  synthetic request can establish it).
- Gemini free-tier per-model RPM/RPD/TPM (now visible only inside AI Studio) and which
  3.x models the free tier currently includes.
- Z.ai rate limits for the free Flash models (documentation page 404 on 2026-09-18).
- W&B: concurrency limits (documented only as a 429 message), the end date of the
  "$100/month, limited time" offer, the 2026-09-30 domain change, and the prompt
  retention/training policy.
- Whether each provider accepts LYA's exact payload shape (`max_tokens`, no tools,
  <=12 messages) — confirm by live synthetic test.
- Owner-account quota and billing status for every provider.

## 7. Sources (all fetched 2026-09-18)

- Cerebras rate limits / FAQ: https://inference-docs.cerebras.ai/support/rate-limits
- GitHub Models retirement: https://docs.github.com/en/github-models
- SambaNova plans: https://cloud.sambanova.ai/plans
- Hugging Face Inference Providers pricing: https://huggingface.co/docs/inference-providers/pricing
- Mistral API rate limits: https://help.mistral.ai/en/articles/698531
- Google Gemini rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Google Gemini pricing (free-tier data use): https://ai.google.dev/gemini-api/docs/pricing
- Google OpenAI compatibility: https://ai.google.dev/gemini-api/docs/openai
- Z.ai pricing: https://docs.z.ai/guides/overview/pricing
- Z.ai chat completions: https://docs.z.ai/api-reference/llm/chat-completion
- OpenRouter limits: https://openrouter.ai/docs/api_reference/limits
## 8. Method and limits of this research

- The `agent-reach` skill was invoked as requested. Its CLI (`agent-reach`,
  `mcporter`, `gh`, `yt-dlp`) is **not installed on this machine**, so research used
  the skill's Jina reader path (`https://r.jina.ai/<url>`) plus direct documentation
  fetches. No platform login, cookie or write operation was used. `agent-reach
  check-update` could not be run for the same reason.
- Lists here are **documentation evidence, not LYA test results.** No isolated check,
  live provider request, account quota reading or accuracy evaluation was performed.
- Free-tier terms change without notice; community-dataset rows are dated and were
  cross-checked against primary documentation where reachable.
## 9. Second pass (2026-09-18) — stealth models, specific model availability, extra gems

### 9.1 "Union Alpha" — what the news actually was

- **Union Alpha** (`stealth/union-alpha`, OpenRouter, released 2026-09-16) was a **stealth
  preview model** developed by **Unbiased**, later revealed as **Pareto**
  (`unbiased/pareto`). It was **free only during the stealth preview**, and OpenRouter's
  own page now states: *"The free stealth period has ended; use Pareto at
  https://openrouter.ai/unbiased/pareto."* 262K context, text+image in.
- Pareto's current price is **$2.50 / $7.50 per 1M tokens** (cache read $0.25/M),
  released 2026-09-17, one provider (Unbiased), 100.00% 3-day uptime, ~4.69 s P50
  latency, 37 tok/s.
- The **other** stealth model, **Ox Alpha** (`stealth/ox-alpha`, 1.0M context, released
  2026-08-20), was revealed to be **ZAI GLM-5.3-Flash**. Its free preview period is over too.
- Both stealth models state that **prompts and completions were retained by the provider**
  (not used for training).
- **Conclusion:** "Union Alpha gives unlimited free access" is a misreading of a
  **temporary, non-renewing stealth preview**. It is not a provider, not unlimited, and
  it has already ended. Do not plan T02 around it.

### 9.2 Cloaked/alpha models that are free right now — and why LYA should avoid them

OpenRouter currently lists free "cloaked" testing models (Sonoma Sky/Dusk Alpha,
Horizon Beta, Cypher Alpha, Polaris Alpha, Sherlock Think Alpha, Andromeda Alpha).
Their own descriptions say prompts and completions **are logged and may be used to
improve the model**, and some say "do not use for production or business-critical
systems". These are unsuitable for a privacy-conscious personal assistant, and they
disappear without notice. **Not recommended for LYA.**

### 9.3 DeepSeek "V4.3-Flash" does not exist

DeepSeek's own API documentation lists only two models:

| API model name | Actual version | Context | Off-peak / peak price per 1M (in / out) |
| --- | --- | --- | --- |
| `deepseek-flash` | **DeepSeek-V4.1-Flash** | 1M | $0.15 / $0.60 off-peak — $0.30 / $1.20 peak |
| `deepseek-v4-pro` | DeepSeek-V4-Pro-0813 | 1M | $0.66 / $1.98 off-peak — $1.32 / $3.96 peak |

- `deepseek-v4-flash` and `deepseek-v4-flash-vision-exp` are **retired names** that now
  route to V4.1-Flash.
- **DeepSeek has no free tier**; it needs a topped-up or granted balance (off-peak is
  half price; peak = 01:00–04:00 and 06:00–10:00 UTC weekdays).
- Free DeepSeek today: `deepseek/deepseek-v4-flash-0731:free` on OpenRouter ($0/$0), and
  DeepSeek V4-Flash-0731 inside **W&B's free $100/month** credits.

### 9.4 GLM-5.3-Flash — where it is free and where it is not

| Route | GLM-5.3-Flash status |
| --- | --- |
| Z.ai direct (`api.z.ai`) | **Not free** — $0.15 in / $0.50 out per 1M. Permanently free GLM models are **GLM-4.7-Flash, GLM-4.5-Flash, GLM-4.6V-Flash** |
| OpenRouter | **Not free** — `z-ai/glm-5.3-flash` $0.09 / $0.30 per 1M. Only `z-ai/glm-5.2:free` is a free variant |
| Cloudflare Workers AI | Hosted, but **requires a paid plan** |
| **W&B Serverless Inference** | **Effectively free** — `zai-org/GLM-5.3-Flash` is a generally available model covered by the free plan's $100/month credits |
| **Alibaba Cloud Model Studio** | **Free new-user quota** (Singapore region, ~1M tokens, 90 days) under `ZHIPU/GLM-5.3` |
- OpenRouter provider routing / pinning: https://openrouter.ai/docs/guides/routing/provider-selection
- OpenRouter data collection and ZDR: https://openrouter.ai/docs/guides/privacy/data-collection
- OpenRouter live free catalog (pricing 0/0 filter): https://openrouter.ai/api/v1/models
- Cloudflare Workers AI pricing: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Cloudflare Workers AI data usage: https://developers.cloudflare.com/workers-ai/platform/data-usage/
- W&B usage limits / free cap: https://docs.wandb.ai/inference/usage-limits
- W&B available models: https://docs.wandb.ai/inference/models
- W&B API base URL: https://docs.wandb.ai/inference/api-reference
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Community dataset used for the wide sweep (verified 2026-08-02/13/14):
  https://github.com/pacocartones/free-llm-api-hub (`collections/always-free.md`,
  `collections/openai-compatible.md`) and https://freellmapihub.com/

### 9.5 Additional free routes found in the second pass

1. **`openrouter/free` — Free Models Router (genuinely zero cost).** "The simplest way to
   get free inference… selects free models at random", filtered to models that support
   what the request needs (image understanding, tool calling, structured outputs).
   **28 free-variant models** in the router, 200K context, released 2026-02-01. Its own
   page states zero charge for prompt/completion tokens. Governed by the same free-model
   limits: **20 RPM / 50 requests per day** (1,000/day after ≥9 all-time credits).
2. **Alibaba Cloud Model Studio new-user free quota** — **~1,000,000 tokens per model**,
   valid **90 days** from activation, **per-model and non-transferable**; models with free
   quota include `qwen3.8-max`, `qwen3.8-flash`, **`deepseek-v4.1-flash`**,
   `deepseek-v4-pro-0813`, `glm-5.2`, **`ZHIPU/GLM-5.3`**, `kimi-k3`, `MiniMax-M2.5`.
   Singapore region only; the quota expires even if unused; turn on **"Free Quota Only"**
   to prevent automatic pay-as-you-go charges. Separately, **OAuth authentication gets
   2,000 calls/day free**, independent of the API-key token quota.
3. **W&B Serverless Inference** — $100/month free credit cap (recorded in §2).
4. **Public AI** (Switzerland, non-profit inference utility) — free access point for
   public/sovereign open models (Apertus 1.5, EuroLLM, ALIA) and an official Hugging Face
   inference provider. Free, but **not frontier-class**; its API docs did not load for
   verification, so treat as unconfirmed.
5. **`openrouter/pareto-code` — Pareto Router: conflicting evidence, treat as NOT free.**
   Its model page FAQ says the router's own price is zero, but the routing documentation
   says: *"The Pareto Router itself adds no fee. You pay only for the underlying model that
   handles the request."* Do not rely on it being free until tested.

**Rejected in this pass:** Chutes (no free tier — pay-per-token, optional $10/$20 per month
plans; `DeepSeek-V4-Flash-0731` at $0.44/$1.32 per 1M), Featherless AI ($25/month chat,
$50/month developer; no free tier, though it never stores prompts), Nebius Token Factory
($1 trial, card required), Upstage Solar Pro 4 and Poolside Laguna (limited-time promos),
AI Horde / Pollinations (volunteer capacity, no SLA).

### 9.6 Still unverified after this pass

- **Z.ai free-Flash rate limits** — the documented page could not be retrieved
  (`/guides/using-the-apis/rate-limits` and `/api-reference/rate-limit.md` returned no
  content; the console is client-rendered). Confirm inside the Z.ai console.
- **ModelScope API-Inference free daily quota** — page renders client-side only.
- **Public AI** API docs, and **W&B's** prompt-retention/training policy.
- Whether LYA's exact request payload is accepted by each route (live synthetic test).
- **Nothing here was tested in LYA, and no account, key or request was created or sent.**

- OpenRouter provider routing / pinning: https://openrouter.ai/docs/guides/routing/provider-selection
- OpenRouter data collection and ZDR: https://openrouter.ai/docs/guides/privacy/data-collection
- OpenRouter live free catalog (pricing 0/0 filter): https://openrouter.ai/api/v1/models
- Cloudflare Workers AI pricing: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Cloudflare Workers AI data usage: https://developers.cloudflare.com/workers-ai/platform/data-usage/
- W&B usage limits / free cap: https://docs.wandb.ai/inference/usage-limits
- W&B available models: https://docs.wandb.ai/inference/models
- W&B API base URL: https://docs.wandb.ai/inference/api-reference
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Community dataset used for the wide sweep (verified 2026-08-02/13/14):
  https://github.com/pacocartones/free-llm-api-hub (`collections/always-free.md`,
  `collections/no-credit-card.md`, `collections/no-phone.md`,
  `collections/openai-compatible.md`) and https://freellmapihub.com/

### 9.7 Second-pass sources

- Union Alpha: https://openrouter.ai/stealth/union-alpha
- Pareto (revealed): https://openrouter.ai/unbiased/pareto
- Ox Alpha (revealed as GLM-5.3-Flash): https://openrouter.ai/stealth/ox-alpha
- Free Models Router: https://openrouter.ai/openrouter/free
- Pareto Router (pricing conflict): https://openrouter.ai/openrouter/pareto-code and
  https://openrouter.ai/docs/guides/routing/routers/pareto-router
- DeepSeek models/pricing: https://api-docs.deepseek.com/quick_start/pricing
- Alibaba Cloud Model Studio free quota:
  https://www.alibabacloud.com/help/en/model-studio/new-free-quota (and
  https://www.alibabacloud.com/help/en/model-studio/models)
- Chutes pricing: https://chutes.ai/pricing
- Featherless pricing: https://featherless.ai/pricing
- Public AI: https://publicai.co/ (docs URL did not load)