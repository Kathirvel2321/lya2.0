# Free-first hybrid research routing

Date: 2026-09-20

## Decision and implementation

- Selected You.com's keyless MCP `you-search` profile for ordinary public research.
  The current official allowance is 100 searches per day without signup or an API
  key. LYA requests snippets only and caps the result at six HTTPS sources, 8,000
  evidence bytes, a 128 KiB response and an eight-second request.
- Kept Tavily as an optional critical-search supplement. It is called only when the
  user explicitly begins a query with `critical research:` or `important research:`
  and the Tavily key plus both existing safety flags are present. Normal search never
  spends a Tavily credit.
- Critical mode uses Tavily first, then uses the remaining deadline and source budget
  for the free provider. Duplicate URLs are removed and source IDs are rebuilt.
- Enabled only the non-secret free-research flag in the ignored local `.env`. No new
  credential was added, printed or copied into documentation.
- Installed Agent Reach 1.5.0 in `C:\Users\kathirvel\.agent-reach-venv`, outside the
  workspace. Its safe diagnostic reports four healthy channels: Jina webpages, RSS,
  V2EX and basic Bilibili search. YouTube has an active `yt-dlp` backend with a missing
  Node-runtime configuration warning. GitHub and Exa remain off because `gh` and
  `mcporter` are not installed; no `--system` changes were authorized or made.
  ScrapeGraphAI and SearXNG were not added: the former adds browser/LLM weight, while
  the latter needs a maintained server.

## Evidence and checks

- A direct keyless MCP contract call returned six structured sources.
- The actual `YouSearchMCP` adapter then returned three bounded sources for the
  synthetic query `official Python documentation`; no private text or key was sent.
- `agent-reach doctor --json` verified the channel states above, and
  `agent-reach check-update` confirmed v1.5.0 is current.
- Seven fake-HTTP policy/parser checks pass, including proof that ordinary searches
  make zero Tavily calls and only an explicit critical prefix enables that route.
- `check-t03.cmd` passed the full offline T01/T02/T03 regression: 14 router, 5 Oracle,
  3 provider setup, 23 Brain, 16 base UI, 10 experience, 15 T02, 6 verification and
  7 research-adapter checks (99 checks total).

## Limits and next gate

The free MCP profile is an external service with a daily quota and no availability
guarantee. Search snippets are untrusted evidence and do not prove full-page support.
The Brain still blocks research in private or person-scoped context and rejects
unknown source IDs. Task 3 remains in progress until semantic source-to-claim checking,
isolated code verification and the frozen 30-case score pass.

Official sources:

- You.com free MCP profile and 100-query daily limit:
  https://you.com/docs/build-with-agents/mcp-server
- You.com MCP wire format and structured search results:
  https://you.com/docs/capabilities/mcp-server-for-web-search
- Exa recurring no-card free credits: https://exa.ai/pricing
- SearXNG JSON search API: https://docs.searxng.org/dev/search_api
- Agent Reach installation and upstream-tool model:
  https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
- Tavily recurring free plan: https://www.tavily.com/pricing

Artifacts:

- `brain/research.py`
- `test_research_adapter.py`
- `check-t03.cmd`
