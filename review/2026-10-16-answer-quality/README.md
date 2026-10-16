# Answer context and evidence upgrade — 2026-10-16

The owner requested a more situational, honest LYA that can correct a false premise,
use relevant context and recommend practical next steps without blind agreement.
This candidate changes the answering source in an isolated checkout based on
GitHub main `945eeec364fa743ef56c1ec5276f06d4f581cd44`. It is not a claim that the
running laptop or Oracle service has been updated.

## Observed problem

Owner-pasted trial outputs showed an initially correct Vasko/orange answer, then
an incorrect Vasko/blue answer after correcting Neral to green. The production
phone path retained only two previous exchanges; desktop omitted chat history.
We did not capture the running app's provider request, so the exact cause of that
particular live failure remains unproven. Independent synthetic probes also
showed that word overlap admitted negated claims, swapped subjects and opposite
results as supported facts.

## Implemented

- `cloud/answering.py` supplies shared guidance for situational interpretation,
  subject-specific corrections, direct conditional answers, honest uncertainty,
  constructive disagreement and suggestions tied to the user's constraints.
- Desktop and phone admit only completed public exchanges. At most five exchanges
  are retained in RAM, under a 24,000-byte serialized-history budget. Full outgoing
  requests stay under 60,000 serialized bytes and twelve messages. Oldest complete
  pairs are removed; individual statements are never clipped to fit context.
- Desktop clears context on identity, idle, sleep/Stop and privacy transitions.
  Existing visitor-observation changes clear guest context without opening sensors.
  A context generation prevents late inference from resurrecting cleared history.
  Local owner-name substitutions are excluded from cloud history.
- Saved/private retrieval and private answers never enter public history. Existing
  private requests remain local-only, and private model turns still use fresh scoped
  evidence rather than prior private assistant replies. This does **not** implement
  full private conversation memory or cross-device shared memory.
- A bounded English recency/topic hint routes questions such as today's exchange
  rate to the existing research adapter, or returns an unavailable result. It is
  not a complete multilingual intent classifier. Phone search/tools stay absent.
- Research facts now require a complete matching excerpt, including qualifiers,
  and are visibly labelled source excerpts that are not independently verified.
  Paraphrases must be labelled inference. Generated source-summary metadata cannot
  substitute for the excerpt. Model-authored code/calculation execution status
  cannot become trusted test evidence. The internal `verified-research` route name
  is retained for compatibility; it is not a proof of truth.
- The three supported mobile staging/update helpers include the new shared module.
  None of those helpers was run against a host.

No model/provider, credential, output-token setting, voice, hearing, visual,
startup, permission or durable-storage configuration was changed. Ordinary
conversation still makes one model call per reply; existing opt-in council work
retains its prior call count. Longer input context can affect latency and token
usage. Battery and live performance were not measured.

## Verification

The final [validation](validation-final.json) and [test log](validation-final.txt)
record **107 checks passing**, zero failures/errors/skips, on Linux/Python 3.12.
Selection: existing answer verification, research adapters, desktop brain,
mobile session/voice/conversation/timing plus nineteen new context/evidence cases.
Fixtures use synthetic public questions, fake credentials, disposable encrypted
stores and loopback HTTP. Linux uses an import-only `win32crypt` shim that rejects
every DPAPI operation; fixtures inject disposable Fernet keys. This does not qualify
Windows DPAPI, native UI, iPhone, Oracle or a live provider.

The earlier [105-case result](validation.json) is retained separately; counts overlap
and are not added. An initial exploratory run had five errors because this isolated
snapshot lacked unchanged `mobile.html` and `ssh_session.py`; both were restored
from the pinned source before the passing runs. No assertion was weakened to hide
those errors. The old six-message phone bound was intentionally updated to twelve,
with new retention and byte-cap checks exercising the replacement contract.

Reproduce with the project's test dependencies:

```sh
python -B review/2026-10-16-answer-quality/run_checks.py --name validation-new
```

The runner refuses to overwrite earlier evidence. `--deps /absolute/test/deps`
can select an isolated dependency directory. The recorded run used fido2 2.2.1,
cryptography 50.0.2 and no live model calls. Source hashes are in the validation.

## Remaining acceptance

Run the [ten conversation scenarios](acceptance-cases.json) against the actual
configured model on desktop and phone, preserving exact replies, model identity,
errors and latency. Judge meaning, not just matching words. These cases are **not
run**. They cover the reported correction error, unknown facts without a hint,
warehouse relationships, realistic suggestions, false guarantees, scoped follow-ups,
Tamil/Tanglish, quoted instruction attacks, source freshness and context eviction.

Passing context-plumbing checks is not a measured improvement in model reasoning,
calibration or advice. The shared guidance remains model-dependent; labelled
inference may still be wrong. Quotation matching does not assess source reliability,
semantic truth or freshness, and stricter matching may reject useful paraphrases.
Older facts can fall outside the bounded context. Camera-off operation cannot
detect an unannounced person change. No comparable-to-ChatGPT score, perfect
accuracy, long-term memory or live deployment is claimed.

## REA use

Read the owner's pinned [REA skill](https://github.com/morluto/rea/blob/b8510ee00b7c4dc0624bed0e728649cf0606060f/.agents/skills/reverse-engineer-anything/SKILL.md).
It says to skip REA engine/readiness work for a complete source repository and to
use normal coding tools for builds. Followed that route. REA engine tools are not
exposed in this session; no diagnostic/setup or unrelated reverse engineering was
performed. The owner's Windows installation record is historical environment
evidence, not proof that this cloud session has those tools.


## Publication scope update — 2026-10-16

After automatic approval review rejected the initial GitHub upload for missing
explicit publication authorization, the owner explicitly requested this tested
change directly on main. The main update uses the freshly checked base commit
and an expected-head guard; no feature branch or draft PR is requested. Prior
review-package wording records the earlier state. Running Windows/Oracle code
is a separate release state and is not changed by a GitHub commit.

The [engineering research guide](../../docs/guides/LYA_ENGINEERING_METHOD.md)
records primary sources and a concrete next evaluation sequence. Runtime source
hashes still match the final 107-case result; only documentation was added in
this follow-up. No claim of live model-quality improvement is made.
