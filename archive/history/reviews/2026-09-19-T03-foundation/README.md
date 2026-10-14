# T03 answer-verification foundation

Date: 2026-09-19

## Implemented and connected

- Froze 30 synthetic public cases before model scoring: five each for conversation,
  Tamil/English, research, coding, planning and privacy.
- Froze release thresholds, including zero tolerated privacy failures, fabricated
  sources and false claims that code or tools were tested.
- Added a bounded evidence contract carrying source ID, HTTPS URL, retrieval time,
  supported claim and bounded excerpt. Source text is explicitly untrusted.
- Added an injectable research-adapter boundary. It receives fixed source, byte and
  timeout budgets; no adapter means the request stops before any model call.
- Tested Gemini grounding live with one synthetic public question. Both documented
  endpoints failed safely: Gemini 2.5 Flash is unavailable to new users, and current
  Gemini 3.x search grounding is unavailable on the API Free Tier.
- Replaced it with an opt-in Tavily Search adapter. It requests one-credit basic
  searches, disables generated answers/raw pages/images, returns bounded result
  snippets with HTTPS URLs, and enforces the eight-second HTTP timeout.
- Required research models to return structured claims. Visible output is rebuilt
  from validated claims, and factual claims must cite a supplied source ID.
- Blocked external research whenever personal context or private mode is active.
- Added a deterministic local arithmetic path for simple expressions. It accepts only
  a small AST allowlist, limits complexity, exponents and results, and calls no model.

## Checks

- `python -B test_answer_verification.py`: 6 tests passed.
- `python -B test_brain_workflow.py`: 23 tests passed.
- `python -B test_research_adapter.py`: 4 tests passed with fake HTTP responses.
- `check-t03.cmd`: complete T01/T02/T03 offline regression passed, including 14 router,
  5 Oracle, 3 provider-setup, 23 Brain, 16 base UI, 10 experience and 15 T02 tests.
- Python compilation and whitespace-diff checks passed.

All checks used synthetic public fixtures, fake model/source adapters and temporary
encrypted stores. They made no live provider, network, sensor, enrollment, deployment
or real-memory call.

## Status and limits

This is an integrated Task 3 foundation, not Task 3 completion. Structural citation
validation proves that cited IDs came from the bounded evidence set; it does not yet
prove that a source independently supports every sentence. Tavily provides snippets
and URLs, but LYA has not independently fetched and compared each full page. The
adapter is connected but disabled until a Tavily free-plan key is stored and both
Tavily safety flags are enabled. No Tavily request has run. Code execution verification
and the full 30-case scored run remain open. Task 2 also remains open because no
independent live backup has passed its fixed reliability gate.

Official selection evidence:

- Tavily Search request/response contract:
  https://docs.tavily.com/documentation/api-reference/endpoint/search
- Tavily recurring free plan: 1,000 credits per month, no credit card, requests stop
  when credits are exhausted: https://www.tavily.com/pricing
- Gemini pricing showing current 3.x search grounding unavailable on the API Free
  Tier: https://ai.google.dev/gemini-api/docs/pricing

Artifacts:

- `cloud/answer-verification-cases.json`
- `cloud/answer-verification-thresholds.json`
- `brain/verification.py`
- `brain/workflow.py`
- `test_answer_verification.py`
- `test_brain_workflow.py`
- `brain/research.py`
- `test_research_adapter.py`
- `check-t03.cmd`