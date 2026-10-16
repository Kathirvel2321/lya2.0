# LYA public web research

Source implementation dated 2026-10-16. GitHub source publication and deployment
are separate. The running laptop/Oracle service has not been changed by this work.

LYA can collect several search results, read bounded public text pages, and answer
from a source packet. Deep mode uses discovery snippets to plan targeted follow-up
searches. Every research answer shows the number of search attempts, pages actually
read, evidence types and retrieval gaps. A search snippet is not a page read.

## Requests and budgets

| Request | Search query attempts | Page attempts | Retrieval budget | Extra model calls |
| --- | --- | --- | --- | --- |
| `Quick search: public question` | Up to 1 | Up to 1 | 8 seconds | None before synthesis |
| `Search: public question` / `Smart search: ...` | Up to 2 | Up to 3 | 18 seconds | None before synthesis |
| `Deep research: public question` | Up to 3 | Up to 6 | 35 seconds | Up to 1 discovery-based planning call |

The existing explicitly configured critical-provider path can make two provider calls
for its first query; both reserve the local counter. Other queries make one provider
call each. These are ceilings, not minimum coverage or answer-latency guarantees. The final
model answer and optional voice have separate existing budgets. Deep planning
consumes the retrieval budget. OS DNS resolution and some blocking network stages
cannot be preempted exactly at that deadline. Cancellation is checked between
stages and read chunks; socket calls have bounded timeouts. No background crawling.

Use a focused topic of at most 300 characters after the mode prefix. Longer topics
are refused before searching, rather than silently dropping constraints. A plan's
individual search terms can be up to 400 characters. Results are deduplicated by
canonical URL, with common tracking query parameters removed. Selection admits at
most two URLs per hostname and six sources overall; subdomains and copied articles
are not independent corroboration.

`Give free alternative websites for creating videos` and some English recency/
recommendation patterns also trigger smart research. These hints are not a complete
multilingual intent classifier. For predictable routing, use an explicit mode
prefix followed by a public question in the desired language. Voice uses the same
recognized text route; no UI/voice configuration changed.

## What happens

1. Admit only the current public question. No saved/private context or previous chat
   history enters the search, planner or research synthesis path. Desktop rejects
   research with private/saved context. Phone remains a public conversation route.
2. Reserve search attempts in a local SQLite daily counter before calling the
   configured search adapter. Failed calls count. The default cap is 40 attempts
   per UTC day per counter; the counter stores only dates and counts. This is not a
   provider-wide quota or billing/account entitlement check.
3. Search from distinct useful angles. Deep mode's optional planner sees the initial
   discovery snippets as untrusted data and proposes at most two additional searches.
   Invalid/unavailable planning falls back to bounded query expansion with a notice.
4. Prioritize some documentation/pricing/terms URL paths, then read selected pages.
   A URL path is only a ranking hint; it does not establish source authority.
5. Supply source IDs, URLs, retrieval timestamps, short passages and evidence types
   to the answer model. For product research, ask it to distinguish ongoing free
   plans from trials, credits, watermarks, export restrictions and permitted use.
6. Validate answer shape/citations. A `fact` must copy one complete page passage
   exactly and cite that page. Search snippets cannot be rendered as facts. Inferences
   and suggestions must cite known sources and are visibly labelled. Unknown answers
   can explicitly abstain. Invalid answers are refused instead of replaced by a
   confident unsupported fallback. A deterministic coverage notice follows the answer.

The renderer checks provenance and excerpt identity, not semantic truth. Inference
and recommendation quality still depends on the model, source quality and retrieved
coverage. It cannot mechanically prove a paraphrase, reconcile every contradiction,
verify a page's ownership, or establish the best option on the whole internet.
An exact quotation can itself be wrong or outdated. Retrieval time is not a page's
publication/update date. Pricing pages vary by region and may omit restrictions.

## Reader boundaries

The reader uses public HTTPS only, with normal certificate validation. It rejects
credentials in URLs, unusual ports, local/non-global addresses and DNS answers
containing any non-global address. It connects to a validated IP while retaining
the original TLS hostname, avoiding a second DNS lookup at connection time.

It requests robots policy first and obeys `can_fetch`; 404/410 means no available
robots file. Unknown/failed policy is a partial result. Current page and robots
redirects are refused because redirected origins need a fresh policy check. Pages
requiring login, cookies, JavaScript, PDFs, compression or challenge handling remain
unread. No account creation, authenticated browser session, executable site code,
forms, purchases or files are handled.

Each page is capped at 192 KiB; robots text at 32 KiB. HTTP requests are capped at
twice the page-attempt budget. Visible HTML text excludes script/style/navigation
and similar regions. Up to three whole text blocks form a passage of at most 900
characters; individual blocks are never clipped to quote away a trailing condition.
This is a small extractor, not a complete browser. Important qualifiers in other
blocks, tables or images may still be missed. Failed reads stay explicitly labelled
as unconfirmed snippets. Evidence packets have an 8,000-byte UTF-8 cap.

## Configuration and release

Desktop keeps its existing opt-ins: `LYA_FREE_RESEARCH_ENABLED=1` selects the keyless
You.com evaluation search adapter. The existing optional Tavily adapter still
requires `LYA_TAVILY_RESEARCH_ENABLED=1`, `LYA_TAVILY_FREE_ONLY=1` and its configured
key. An explicitly prefixed `critical research:` / `important research:` query can
use that existing Tavily path; normal searches do not switch to it on failure.
The shared researcher now wraps the configured adapter and stores the attempt
counter at the existing data directory's `research-usage.sqlite`.

Phone runtime adds an optional `/etc/lya-connect.json` entry:

```json
{"public_research": "keyless_evaluation"}
```

This is an additional entry in the existing configuration, not a replacement
configuration. Absent/false keeps phone research unconfigured. An unconfigured
current-research request is refused before model inference. Unknown profile names
fail startup rather than selecting another provider. No configuration was activated
by this source change. Three existing staging/update allowlists now include the
shared modules; those historical helpers have separate preconditions and were not
executed. A live release requires an appropriate current-host staging/release check.

You.com's documentation checked on 2026-10-16 describes its keyless free MCP profile
as **evaluation** access: 100 daily queries with search/discover, without contents
or research tools, and directs use beyond evaluation to an API key. LYA implements
its own public text reading; it does not acquire provider extraction/research
entitlements. This is not a commitment of unlimited free production browsing.
No account, key, subscription or paid fallback was added. Existing provider quotas,
model allowances, outbound connectivity and applicable usage terms must be qualified
before a production release; a free-only flag does not inspect billing eligibility.

## Evidence and next acceptance

The [dated report](../../review/2026-10-16-web-research/README.md) contains isolated
checks and an unrun live acceptance pack. Tests use injected providers/transports,
fake passkeys and temporary stores. They do not qualify real search contracts,
provider availability, semantic answer quality, native devices or Windows DPAPI.

Next, qualify the configured provider and actual model against the owner's video
research request, inspect cited pricing/terms manually, and measure helpfulness,
missed restrictions, uncertainty, search counts and latency. Release source to a
host only with the relevant runtime setup and rollback evidence. Private browsing,
shared durable memory, arbitrary browser automation and exhaustive crawling are
outside this implementation.

Primary technical references checked 2026-10-16:

- [You.com authentication and evaluation profile](https://you.com/docs/using-the-api/authentication)
- [You.com MCP server](https://you.com/docs/agents/mcp-server)
- [Anthropic research engineering](https://www.anthropic.com/engineering/multi-agent-research-system)

The research engineering article informed adaptive discovery, bounded effort and
explicit provenance. This implementation is a bounded single-researcher pipeline;
no multi-agent quality result from that article is claimed for LYA.
