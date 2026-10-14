# T02 acceptance contract — 2026-09-17

Existing 8-case rubric: `cloud/model-evaluation.json`. No private information is
sent. Owner confirmed Groq and NVIDIA accounts are free-only, paid billing disabled.
This attestation permits bounded synthetic generation, not paid upgrades.

Before promotion: all eight rubric cases reviewed PASS, zero invented verification
or private-data boundary failures, each call within 8 seconds on the Oracle host;
three repeated short factual checks pass on each candidate. Forced primary outage
must reach an independently hosted live backup within 18 seconds of routing;
whole SSH exchange stays within 30 seconds. A failed call stops that candidate's
case pack. Do not promote from catalog presence or HTTP success alone.

Current laptop runs were exploratory using the existing rubric and 8-second socket
timeout. A socket timeout is not a whole-request deadline; their measured wall
times are retained. These results cannot be relabelled as hard-deadline passes.

Offline checks must cover: rate-limit cooldown/restart, empty/malformed output,
refusal with no fallback, auth/input failure, all-down, shared upstream, private
denial, cancellation before/between attempts, late results, reservation/deadline
race, daily token/attempt caps including concurrent reservations, and sanitized
metadata. Remote smoke tests exercise POSIX alarm and cancellation over stdin.

No quota or cost number is inferred from a model catalog. Account caps are not
queried by the existing catalog API. Local conservative token reservations and
attempt caps limit work; billing-disabled accounts enforce the owner's no-paid-use
condition. Private context remains denied; unknown gateways remain disabled.
