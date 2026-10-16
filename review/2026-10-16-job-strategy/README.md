# Automation strategy and bounded execution foundation — 2026-10-16

The owner asked to plan and implement the governing strategy before adding more
scheduled actions: what runs, when, where, scope, budget, stop conditions and follow-up.
The example is an 18:00 message review, narrowly scoped requested-link replies and
an important-message report at 19:00. Source baseline: GitHub main
`0e66f13e675b64a25b32dbc58d7ca98d318026c2`; direct main publication is authorized.

## Delivered

[Master strategy](../../docs/guides/LYA_AUTOMATION_STRATEGY.md),
[draft contracts](../../docs/examples/automation-contracts.json),
`cloud/job_policy.py`, `cloud/job_store.py`, `cloud/job_runner.py`,
`cloud/job_adapters.py` and [synthetic lab](../../tools/job_policy_lab.py).

Contracts bind time zone, daily start/report times, account/source, placement,
privacy, input window, importance-rule references, zero-spend policy, link catalogue,
reply mode, resource caps and retention. Unknown authority/command fields are rejected.
Default owner verification denies; an injected verifier must validate real fresh
owner proof for the exact contract before production use. No network API exposes
this trusted internal interface. Source text/model output cannot enable a job.

Daily slots, bounded missed-run grace, DST gap/repeat behavior and durable run IDs
avoid normal duplicate execution. Runtime delegation epochs, cancellation and limits
stop later work. Receipt intent is persisted before outgoing calls; uncertain sends
require review, not automatic retry. Report completion is separate from the scheduled
notification outbox. Owner keep/later/dismiss metadata operations do not change
provider messages or extend private retention. Partial collection is labelled partial.

A public news adapter can use the same engine, but no existing accepted desktop
watcher was migrated. No WhatsApp/YouTube connector, protected production private
sink, notification provider, contract speech/compiler UI, remote approval endpoint,
OS timer, cloud daemon or deployment is added. The code is an executable foundation
and lab, not a running universal task service or a successful account integration.

## Verification

[Final evidence](validation-release.json), [log](validation-release.txt),
[runner](run_checks.py): **228 checks pass, zero failures/errors/skips** — 41 new
policy/execution cases plus the previous 187 selected regressions. Counts overlap
prior runs and are not added. Source SHA-256 values and Linux/Python version are
recorded. Existing import-only DPAPI shim refuses every operation; encrypted fixtures
use disposable keys. Qt regressions use actual offscreen PySide6. No Windows DPAPI,
native toast, whole assistant, real account, provider API or remote host is qualified.

New checks cover exact contract approval, resource caps, schedule separation,
input cutoff, time zones/DST, private cloud consent, account/sink/placement gates,
concurrent/restart deduplication, revocation during collection/send/reporting,
recipient/resource constraints, cross-job reply deduplication, conflicting or unknown
send outcomes, notification delay/expiry/deduplication, fixed exception reason codes,
owner inbox decisions, recovery fencing, public report expiry/purge and refusal to
reuse an unrelated database. The source public adapter is exercised with fake feeds. Final audit assertions also
verify immutable contract snapshots, actual start/finish times and budget counters.

[The synthetic example](synthetic-example.json) exercises 18:00 collection, one
fake approved-link reply and a fake owner report at 19:00, with no early or repeat
notification and no private body in the control database. It uses a test-only RAM
report sink and fake proof/targets; **zero real messages and zero network calls**.
It does not establish production private storage or account permissions.

The [initial run note](initial-run-note.txt) preserves an exploratory runner error:
a test helper named `run` shadowed unittest's runner before fixtures initialized.
It was renamed; no policy or assertion was weakened. `validation-fixed` and
`validation-policy` then passed 222 checks; `validation-time-windows` passed 226
(Linux time-window tests, not Windows OS qualification); `validation-final` passed
228. The final publication run adds explicit notification timeout plumbing, actual
run-time/budget records, immutable contract snapshots and the lab source hash. Prior evidence is retained separately.

## Practical limits and next step

Budget checks are cooperative trusted-adapter boundaries, not an OS sandbox or
hard callback kill. A registered adapter must implement bounded transports, source
window/pagination limits, verified provider identities/targets, semantic classification
and current account scopes/messaging rules. The executor cannot prove those facts
from a callback returning true, attest a physical host label, inspect hidden network
calls or verify provider billing/receipt authenticity. Production owner verification,
protected private reports, hard worker resource limits, durable custody, reconciliation
UI and retention maintenance remain to qualify. Control metadata is trusted local
SQLite, not a tamper-resistant multi-host authority service.

For the user's example, ordinary personal WhatsApp access is not established by
business Cloud API documentation; the account type and permitted route are unresolved.
YouTube comment retrieval/reply scopes are separate and no follower identity or
channel connection is assumed. “Important” and the exact requested-link mapping must
be defined; a 6 PM batch does not cover arrivals at 6:30 without another scheduled
check. The examples are not installed or enabled routines.

Next wire the reviewed contract/owner boundary, qualify a public-only job on the
existing server with rollback and a real owner notification path, then qualify
private read-only work before delegated sending. Accepted voice/hearing/UI/private
storage/startup and another interface chat's files remain unchanged. No real data
transfer, enrollment, billing configuration or laptop/Oracle deployment occurred.
