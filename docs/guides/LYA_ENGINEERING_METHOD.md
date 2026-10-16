# Engineering LYA with evidence

Research date: 2026-10-16. These recommendations apply public engineering
practices to this project's current state. They are not a ranking of developers,
a promise that any product can be built, or a claim that LYA has frontier-model
reasoning. The source code, model, tools, operating constraints and evaluation all
contribute to the result.

## What the primary sources support

| Source | Supported practice | Application to LYA |
| --- | --- | --- |
| [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents), 2024-12-19 | Begin with simple, composable patterns; add orchestration when its value is demonstrated. | Keep ordinary answers to one model call. Compare more elaborate reasoning against a baseline before adopting it. The article flags some tooling details as dated; this recommendation uses its engineering principle. |
| [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), 2026-01-09 | Build cases from real failures, evaluate outcomes, separate capability and regression suites, repeat stochastic trials and inspect transcripts. | Turn the crate error into a repeatable scenario. Keep plumbing tests separate from live answer scoring. Review meaningful correctness rather than only keyword matches. |
| [Anthropic: Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents), 2025-09-29 | Context is finite; select relevant information and manage it throughout a task. | Budget recent dialogue and retrieved records. Check what actually reached the model. A larger history cap alone is insufficient. |
| [DORA: Trunk-based development](https://dora.dev/capabilities/trunk-based-development/), accessed 2026-10-16 | Integrate small changes frequently, run fast automated checks and repair or revert broken builds promptly. | The owner chose direct updates to main. Use a tested, bounded commit with an expected-head guard; preserve a known rollback point. A long-lived feature branch is not required for this choice. |
| [Google SRE: Canarying releases](https://sre.google/workbook/canarying-releases/), accessed 2026-10-16 | Reproducible builds, small releases, controlled exposure, outcome measurement and rollback reduce release risk. | A GitHub commit and a running release are different states. Qualify one device/session first, with a reversible release, before wider use. |

## A practical sequence for each change

1. **Write the observable outcome.** Example: after changing Neral from blue to
   green, Vasko remains orange. Include one case where the information is absent
   and the correct behavior is to say it is unknown.
2. **Record constraints before proposing architecture.** For LYA these include
   accepted voice/UI, public/private routing, available budget, laptop resources,
   phone limitations and the currently configured model. Missing facts remain
   unknown; they must not be converted into assumptions about free services.
3. **Find the failing layer.** Inspect transcription, admitted context, retrieved
   evidence, route, model output, validation and presentation independently. If the
   original assignment was never sent, replacing the model is not a demonstrated
   fix. If correct context was sent and the model still confuses subjects, evaluate
   model/prompt alternatives against that same case.
4. **Run the smallest experiment that can disprove the hypothesis.** Change one
   major variable at a time, keep the input and model configuration comparable,
   and use a clean session for every trial. Include successful old cases and new
   challenging cases. Keep some paraphrases and renamed entities out of tuning.
5. **Inspect artifacts, not assurances.** A claimed tool action needs trusted
   execution evidence. A citation needs a supporting passage and source review.
   An exact quote establishes quotation identity only. A model agreeing with
   another model is not independent verification.
6. **Keep the useful change and rerun the affected regressions.** Measure answer
   quality, latency and resource/call usage separately. A slightly better answer
   may be unacceptable if it violates the project's budget or privacy boundary.
7. **Commit a small known change to main, then qualify a release.** Use the actual
   current main as parent, refuse a moved head, and preserve unrelated work. Revert
   with a new commit if needed; do not rewrite shared main history.
8. **Add the failure to the permanent test set.** Periodically refresh challenging
   cases so the system cannot appear to improve merely by memorizing a tiny suite.
   Use synthetic fixtures and owner-provided examples; this plan adds no automatic
   collection of personal conversations.

These steps are a repeatable development process. The failure to avoid is changing
prompts repeatedly without a baseline, cause hypothesis or acceptance criterion.

## What is already built and what is still missing

| Layer | Current evidence | Next useful proof |
| --- | --- | --- |
| Shared public context and guidance | Implemented; 107 selected synthetic checks, including 19 new checks, pass. | The actual model receives and correctly uses the intended context on both production clients. |
| Corrections and missing facts | Guidance and context plumbing exist; live owner-pasted trial previously failed. | Repeated trials of correction, unrelated-subject preservation and unknown-fact abstention. |
| Source support | Complete-excerpt identity blocks the three demonstrated word-overlap contradictions. | Trusted-source selection, freshness and human review of inference quality. |
| Good suggestions | Prompt asks for goals, constraints, alternatives and a principal tradeoff. | Human-scored suggestions on realistic problems, including cases requiring disagreement or clarification. |
| Model selection | Existing provider/model choices are preserved. | A comparison using the same cases and budgets; no model replacement is justified solely by model size or branding. |
| Private/shared memory | Existing privacy controls remain; the new public history excludes private replies. | Previously planned authenticated memory integration and separate acceptance. Five public exchanges are not durable shared memory. |
| Running product | Git source can be updated independently of the Windows/Oracle installations. | Tested build identity, actual desktop/iPhone behavior, release status and a working rollback. |

The next decisive work is a small live evaluation of the configured model and
production route. More architectural components alone do not establish progress.

## Initial live experiment

Use the [acceptance pack](../../review/2026-10-16-answer-quality/acceptance-cases.json).
Begin with correction, unknown fact and business relationship cases. Run each
three times in fresh sessions on each client, within a declared call/token/time
budget. This is a proposed first screen, not statistical proof of reliability.
Expand the suite after it can diagnose failures; the remaining seven scenarios
include Tamil/Tanglish and adversarial instructions. Do not silently spend beyond
configured free allowances to complete the matrix.

For each trial record only synthetic prompts, visible answers, model/provider
identity when actually known, client/release identity, route, latency and errors.
Do not request or retain hidden chain-of-thought. A missing measurement is null,
not zero; an unrun case is NOT RUN, not PASS.

| Dimension | Passing example | Failure example |
| --- | --- | --- |
| Correctness | Vasko remains orange. | Vasko becomes blue without a new assignment. |
| Uncertainty | Merin's colour was not supplied. | A plausible colour is invented. |
| Situation | A manufacturer paying for storage is the warehouse's customer for that service. | Incoming goods alone determine vendor status. |
| Advice | Explains a decision using stated time and budget constraints. | Recommends unaffordable training or invents resources. |
| Instruction following | Explains only the requested second point. | Repeats the entire previous comparison. |
| Honesty and boundaries | Distinguishes available evidence and proposed actions. | Claims browsing, saving or execution that did not occur. |

The owner and developer review meaning against these criteria. Optional automated
grading must be checked against human judgments before it controls releases. A
single average score must not hide fabricated execution, privacy failures or the
specific correction regression.

For a fair comparison preserve baseline and changed outputs, including all failed
trials. Report counts by scenario and client. Small samples are a way to locate
problems, not to advertise near-perfect accuracy. Tokens, latency, memory and
battery measurements must come from the relevant running environment.

## Boundaries of this work

This guide is research and a project-specific method. It does not deploy software,
start paid APIs, enable telemetry, change the accepted interface, add autonomous
training or grant private data access. A model's reasoning limits cannot be erased
by a stronger-sounding system prompt. Specialized excellence on demonstrated tasks
is a realistic target; guaranteed mastery of every task is not.
