# Bounded public research — 2026-10-16

The owner asked for current, deeper web investigation, including evaluating actual
free-video options instead of repeating the first search result. This source change
is based on GitHub main `5d7efaac79781df6a67167cf45078b01b8a1ab34`. The owner explicitly
authorized direct main publication. No running service or device was changed.

## Source behavior

- `cloud/public_search.py` shares the existing search-only You.com MCP adapter.
  `brain/research.py` retains Tavily/hybrid opt-ins and wraps the configured adapter
  in the new public researcher. `desktop/app.py` on the pinned main already calls
  `default_researcher()`; no UI/launcher edit is required.
- `cloud/web_research.py` implements quick/smart/deep query/page/time/evidence caps,
  canonical deduplication, hostname diversity, adaptive discovery-based planning,
  source evidence types, quota accounting and a deterministic coverage notice.
  Deep planning receives discovery snippets before selecting targeted follow-ups.
  It is one bounded model planner, not a swarm or exhaustive crawler.
- `cloud/web_reader.py` reads public HTTPS text with robots-policy checks, validated
  global DNS answers and a pinned destination retaining TLS hostname validation.
  It refuses redirects, non-text/compressed/oversized content and unavailable policy.
  Unread pages remain unconfirmed snippets. It never executes site JavaScript.
- `cloud/evidence.py` carries the unchanged existing excerpt/citation/calculation
  implementation, re-exported through `brain/verification.py` for compatibility.
  New research additionally refuses search snippets as facts and requires citations
  on model inferences/suggestions. Source truth and semantic inference remain unproven.
- `brain/workflow.py` connects the bounded report to desktop research answers and
  checks context generation during retrieval. `cloud/mobile.py` supports the same
  research packet/cancellation contract without previous-chat context. Phone runtime
  provides explicit optional evaluation configuration; an unconfigured current-data
  request refuses before model inference. Ordinary phone prompts describe available
  research honestly. Stage timing adds only the fixed name `research` and duration.
- The three existing mobile setup/update helpers now ship the shared modules in
  their allowlists. They were reviewed/compiled, not executed on a host. Their
  historical deployment preconditions still apply; this is not a new release tool.

The [guide](../../docs/guides/LYA_WEB_RESEARCH.md) records budgets, configuration,
provider constraints and limitations. Existing voice/hearing, UI, startup, identity,
private storage and enrollment choices were not changed. Searches use only the
current public question; no stored private context or authenticated browser session
was added. Obvious private-query rejection is a heuristic, not a general data-loss
classifier. Public questions still leave the device for configured providers.

## Evidence

Final result: [145 passing checks](validation-published.json),
[complete log](validation-published.txt), [runner](run_checks.py).
Zero failures, errors or skips. Of these, 38 are new focused research cases and 107
are the previous selected regression cases. Counts overlap earlier runs and are not
added. Python 3.12/Linux only, fake providers and injected HTTPS transports,
synthetic passkeys, temporary encrypted/authentication stores and loopback HTTP.
The import-only DPAPI shim rejects operations; this is not Windows qualification.
Source hashes are recorded in the JSON. No live search/model calls were made.

New cases cover URL/DNS/TLS boundaries, robots rejection, redirect refusal, MIME and
byte caps, qualifier-preserving excerpts, concurrent daily quotas and rollover,
provider/planner failures, adaptive searches, page/snippet distinction, malformed
citations, private context, deadline/cancellation, disabled phone configuration,
phone/Desktop integration, context clearing and no retained research contents in
phone authentication storage.

Preserved earlier evidence:

- `regression-precheck`: all previous 107 checks passed during wiring.
- `validation`: 141 cases, one failure. Planner cancellation was swallowed because
  `InterruptedError` subclasses `OSError`. Added explicit propagation at search,
  planner and reader boundaries; then added direct regressions.
- `validation-cancel-fix`: 142 passed after that correction.
- `validation-final`: 144 passed after inter-stage cancellation and quick-mode checks.
- `validation-release`: 145 passed including accurate ordinary phone capability prompts.

Final checks also compile the changed Python modules and embedded deployment
program strings without running them, inspect packaging import closure, verify
source hashes against final evidence and run `git diff --check`. No unrelated
repository-wide test discovery or archived code was executed.

## What remains unqualified

Actual provider contracts/availability, source authority, model reasoning and
constraint coverage, pricing/terms accuracy, native Windows/iPhone behavior,
latency/quality/cost, host egress, current-host staging and deployment are pending.
The [live acceptance pack](acceptance-cases.json) is prepared but **not run**, as the
owner deferred live testing. Exact excerpt matching is not independent verification;
labelled inference can still be wrong. Automatic routing is a bounded English hint;
explicit prefixes are the reliable entry point. Public topic length is currently
300 characters, redirects/JavaScript/PDF/login pages are unsupported, and extraction
can miss qualifications outside selected text blocks.

Provider documentation checked on 2026-10-16 describes the keyless You.com free MCP
profile as evaluation access, 100 queries/day, without provider contents/research
tools; use beyond evaluation requires an API key. The local 40-attempt counter is
not an account entitlement or global billing check. No key, paid provider fallback,
subscription, production configuration, real enrollment or private-data export was
added. A production-compatible provider/allowance needs qualification before release.

Primary references: [You.com authentication](https://you.com/docs/using-the-api/authentication),
[You.com MCP](https://you.com/docs/agents/mcp-server),
[Anthropic research engineering](https://www.anthropic.com/engineering/multi-agent-research-system).
REA's previously read official skill routes ordinary repository builds through
normal source tools; no reverse-engineering engine or LYA runtime agent was added.
