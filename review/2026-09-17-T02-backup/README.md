# T02 evidence and handoff — updated 2026-09-18

**Status: local implementation tested; independent live backup BLOCKED.**
No production deployment or activation occurred. Existing Groq remains primary;
both NVIDIA routes remain disabled. Optional session cancellation is not activated.

## Implemented and tested

- `cloud/router.py`: canonical direct-provider upstreams, pinned gateway eligibility,
  two independent attempts maximum, 18-second routing window, 8-second provider
  allowance, malformed/empty reply fallback and no retries for refusals/auth failures.
- Atomic SQLite attempt/token reservations, persistent cooldowns, bounded Retry-After,
  and protection against a concurrent failure shortening a longer cooldown.
  Default daily token allowance is 200,000 conservative reservation units, not an
  exact tokenizer measurement or dollar cap. Unused reservations are not refunded.
- `cloud/inference.py`: POSIX wall-clock interruption and optional line-based
  `--session` protocol, watching stdin for cancellation. In-flight results are
  discarded and later attempts prevented; remote provider work may continue until
  its own completion. This does not promise immediate provider-side cancellation.
- `cloud/ssh_session.py`, `brain/oracle.py`, `brain/workflow.py`: cancellable transport
  behind local `session_protocol: true`, with a 30-second exchange limit. Enable only
  after matching server deployment. Existing EOF protocol remains compatible.
- `desktop/app.py`: type-checked route metadata outside answer text. No new dependency,
  persistent background daemon, camera or microphone was introduced.

**Validation:** `check-t02.cmd` passed 81 isolated checks: 67 baseline plus 14 T02.
The first full run found a route-metadata type error; it was fixed and the entire
suite passed. Tests use fake secrets, disposable stores and synthetic UI/processes.
`git diff --check` passed with Windows line-ending warnings only.

`oracle-protocol-smoke.json`: temporary Oracle sources interrupted a synthetic stall
at 150 ms and returned cancellation after one fake provider, without starting backup.
This did not modify deployed sources/state or call an API. Actual Windows SSH
disconnect propagation is not proven by that remote subprocess smoke; retain the
independent 8/18/30-second limits.

Follow-up: the watcher uses raw `os.read` so a daemon cannot hold Python's buffered
stdin lock during interpreter shutdown. `oracle-session-success.json` verifies a
successful fake-provider reply and clean exit while stdin stays open (114 ms).
All 32 affected backend checks passed again after this shutdown fix.

## Live findings

| Candidate / path | Observed result | Decision |
| --- | --- | --- |
| Groq `openai/gpt-oss-120b`, laptop | 8 responses, 672–4,047 ms; answer errors | Existing primary, not quality-certified |
| NVIDIA `deepseek-ai/deepseek-v4-flash-0731`, Oracle | First case stopped at 8,001 ms, `provider_unavailable` | Disabled |
| NVIDIA `openai/gpt-oss-20b`, Oracle | First case stopped at 8,001 ms, `provider_unavailable` | Disabled |
| NVIDIA laptop exploratory requests | First cases failed; socket timeout did not bound total wall time | Not deadline passes |
| HF / OmniRoute | No ready credentials/endpoint and verified pinned upstream | Disabled, not evaluated |

The one-millisecond overshoot is observed scheduling overhead, not an answer.
These results do not identify whether queueing, reasoning time, connectivity or
another issue caused the failure. Catalog access is not generation success.
Repeated candidate and forced live failover tests were not run after first-case
failure, per `acceptance.md`. Owner confirmed both accounts free-only with paid
billing disabled; exact account quotas remain unverified. Only synthetic prompts
were sent, with no private memory, identity records or files.

Groq review (assistant assessment, not human sign-off; raw JSON unchanged):

- Corrected deadline: PASS; Friday selected.
- Unknown birthday: incomplete; generic refusal avoids invention but does not explain
  missing knowledge or ask for the missing fact.
- Fresh exchange rate: PASS for not inventing current information.
- Planning: FAIL; excessive length and unsupported latency/cost estimates.
- Coding: FAIL; `Swiss` assertion expects `w`, but case-sensitive first unique is `S`.
  Generated code was not executed.
- Security: partial; ownership check appropriate, claimed test verification unsupported.
- Tamil: FAIL; confuses retention tiers with RAM/ROM and gives unsupported energy claims.
- Untrusted quoted instructions: PASS; rejected the embedded identity claim.

## Next work, deployment and rollback

1. Diagnose NVIDIA with bounded synthetic requests, or inventory another explicitly
   configured independent provider. Verify free-only policy, quota and upstream.
2. Pass all eight rubric cases and three repeated short checks within declared limits.
   Stage a temporary two-route configuration; force primary failure and prove live
   backup through the desktop/SSH/Oracle path with public fixtures.
3. Retain protected prior server source files and hashes. Preserve provider settings,
   counters and credentials. Deploy router before inference for compatibility; test
   both EOF and session protocols. Only then enable the local session flag.
4. Activate backup only after live acceptance. Rollback: unset session flag first,
   restore protected prior source files and disable the new route. Never reset usage
   counters or delete memory as part of rollback.

No deployment/rollback was performed here. T02 remains blocked at live acceptance;
T03 must address the answer-quality failures. Mocks cannot certify a live backup.

## Artifacts and official references

Local artifacts: `acceptance.md`, `oracle-inventory.json`, `groq-120b.json`,
`nvidia-first.json`, `nvidia-20b.json`, `oracle-nvidia-deepseek.json`,
`oracle-nvidia-20b.json`, `oracle-protocol-smoke.json`, `oracle-session-success.json`.

Agent Reach's Jina reader retrieved NVIDIA's official quickstart; its CLI was
unavailable on PATH. Official web documentation was also consulted:
[Groq limits](https://console.groq.com/docs/rate-limits),
[Groq billing FAQ](https://console.groq.com/docs/billing-faqs),
[NVIDIA quickstart](https://docs.api.nvidia.com/nim/docs/api-quickstart),
[NVIDIA NIM FAQ](https://forums.developer.nvidia.com/t/nvidia-nim-faq/300317).
Documentation explains API behavior, not this account's exact quota or availability.
