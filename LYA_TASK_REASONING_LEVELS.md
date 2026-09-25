# LYA task reasoning levels

Updated: 2026-09-16. This file assigns LYA work to high, medium and low
reasoning levels. It complements [the ordered roadmap](LYA_TASK_ROADMAP.md) and
[the implementation checklist](LYA_IMPLEMENTATION_CHECKLIST.md); it does not
change their dependency order or mark any capability complete.

"Reasoning level" means the judgment needed for the work, not the value of the
person doing it. Use the lowest level that can safely complete a bounded piece.
Escalate when a task crosses a permission, privacy, security, architecture,
provider, encryption or data-loss boundary.

## Quick assignment table

| Task | Default level | Parts that may use a lower level | Mandatory escalation |
| --- | --- | --- | --- |
| T01 Baseline | Medium | Low: collect commands, format results, check paths | Unexpected failures, secret exposure or destructive recovery |
| T02 Provider backup | High | Medium: run approved fixtures; Low: catalog sanitized results | Route activation, privacy policy, failure-domain and cost decisions |
| T03 Answer verification | High | Medium: run frozen cases; Low: prepare public fixtures | Rubric design, source validation, security/privacy failures |
| T04 Trusted session | High | Medium: implement approved UI states | Authentication, approval binding, expiry and replay decisions |
| T05 Private memory | High | Medium: approved CRUD/UI plumbing; Low: synthetic notes | Encryption, migration, retention, isolation and recovery |
| T06 Council | High | Medium: run frozen plan cases | Seat design, budgets, evidence synthesis and truth claims |
| T07 File browser | Medium | Low: mockups, dummy files, accessibility checklist | High: path authorization, links/junctions and write operations |
| T08 Voice | Medium | Low: command phrases and manual result entry | High: authorization binding, recording/privacy and cloud fallback |
| T09 Recognition | High | Medium: consented UI implementation | Enrollment, biometric retention, thresholds and access decisions |
| T10 Backup/recovery | High | Medium: run an approved restore procedure | Encryption, keys, retention, schema compatibility and real upload |
| T11 iPhone access | High | Medium: implement an approved screen/protocol | Pairing, secure storage, sync conflicts, revocation and offline cache |
| T12 Action executor | High | Medium: implement a frozen low-risk tool contract | Side effects, approvals, retries, rollback and security scope |
| T13 Reusable skills | High | Medium: settings UI and approved workflow encoding | Generated code, permission changes, activation and provenance |
| T14 Release | High | Medium: repeat measurements/build approved package; Low: format report | Release scope, privacy/security sign-off and publication decision |

## High-reasoning work

Use the strongest available engineering/reasoning agent and require human review.
This work can cause privacy loss, unauthorized action, corrupted memory, false
claims or an unsafe release if the design is wrong.

### Tasks led at this level

- **T02 — Provider backup:** determine true upstream independence, privacy
  eligibility, time/token budgets, quota behavior and safe activation/rollback.
- **T03 — Answer verification:** design scoring, connect evidence to claims,
  resist instructions embedded in sources and decide when LYA must abstain.
- **T04 — Trusted session:** define identity, exact-action approval, expiry,
  revocation, replay prevention and rechecking after asynchronous work.
- **T05 — Private memory:** protect person isolation, encryption, migrations,
  retention, deletion, transaction integrity and private inference boundaries.
- **T06 — Council reasoning:** create genuinely distinct roles, enforce a total
  budget, expose disagreements and avoid presenting consensus as proof.
- **T09 — Recognition:** choose consent/retention rules, matching thresholds,
  uncertainty behavior and ensure face matching never becomes strong approval.
- **T10 — Backup and recovery:** design encryption/key recovery, snapshots,
  schema compatibility, retention and safe restore without damaging the original.
- **T11 — iPhone access:** design pairing, least-privilege credentials, sync,
  conflicts, revocation and honest offline-cache behavior.
- **T12 — Action executor:** validate tool calls, bind approval to parameters,
  manage side effects, cancellation, retry safety, verification and rollback.
- **T13 — Reusable skills:** prevent generated workflows from widening their
  authority, running before review or modifying core security controls.
- **T14 — Release decisions:** decide supported scope and evaluate unresolved
  security, privacy, data-loss and performance risks before publishing.

### High-level agent rules

- Read the relevant source end to end and trace every caller before editing a
  shared authorization, storage or routing boundary.
- Write the threat/failure cases before implementation and preserve deny-by-default.
- Require isolated checks plus separately labelled live/device evidence.
- Never activate a route, collect biometrics, upload private data, spend money or
  publish solely because an automated agent recommends it.
- Hand off a reviewable diff, evidence, unresolved risks and rollback instructions.

## Medium-reasoning work

Use a capable coding agent for scoped implementation whose architecture and
permissions are already decided. A high-level reviewer is still required when
medium work touches a high-level boundary.

### Tasks led at this level

- **T01 — Baseline:** inspect the checkout, run reviewed checks, exercise launch,
  cancellation and quit, then record a reproducible known state.
- **T07 — File browser:** build the native paged glass interface, background
  loading, previews, keyboard navigation and error states. Path authorization and
  any future write operations must be reviewed at the high level.
- **T08 — Offline voice:** connect the approved local speech model, indicators,
  stop behavior, device failures and typed-command parity. Recording policy,
  authorization and any network fallback require high-level decisions.

### Medium-level portions of other tasks

- Run a frozen provider/answer/council evaluation and collect metrics without
  changing its rubric, data policy or activation decision.
- Implement already-approved UI states, adapters, storage methods or tool schemas.
- Create synthetic fixtures, isolated tests and failure injection from a written
  acceptance specification.
- Run a documented restore, packaging or performance procedure in a disposable
  environment, without changing keys, retention or release scope.

### Medium-level agent rules

- Stay within the written contract; record ambiguities instead of redesigning it.
- Use fake credentials and temporary stores until the task explicitly reaches its
  authorized live/device stage.
- Do not turn a test-only adapter into production configuration.
- Stop and escalate if implementation requires new permissions, data collection,
  external transmission, destructive migration or a security tradeoff.

## Low-reasoning work

Use a fast/basic agent only for deterministic, reversible work with exact inputs
and expected output. No complete numbered production task is low reasoning.

### Suitable work

- Gather ten daily commands and expected responses using synthetic/public data.
- Create dummy folder trees, fake notes, fictional profiles and non-private test
  questions from a supplied template.
- Produce file-browser wireframes, light/dark variations and empty/loading/error
  state mockups without wiring them to real files.
- Transcribe provider name, official URL and published limit into a table without
  keys and without deciding whether the provider is safe or independent.
- Run an exact, reviewed offline command and copy exit status/results into a dated
  report. Never run commands marked LIVE or legacy/destructive.
- Check whether named files exist, validate Markdown links, format tables and verify
  every completion-report field is filled.
- Repeat approved UI screenshots or performance measurements under a fixed protocol;
  do not interpret them as a battery, security or release guarantee.
- Write user-facing wording from an approved behavior specification.

### Work forbidden at this level

- Choosing or activating providers, models, endpoints or fallback policy.
- Editing permission, authentication, identity, encryption, retention or migration code.
- Handling real API keys, SSH keys, private notes, audio, faces or visitor images.
- Approving model answers, citations, generated code or security conclusions.
- Executing tools with side effects, restoring production data or resolving sync conflicts.
- Marking tasks complete, changing acceptance thresholds or publishing a release.

### Low-to-medium escalation triggers

Escalate immediately if an instruction is ambiguous, a command fails unexpectedly,
real/private data appears, an external call is needed, a file would be overwritten,
or the expected result no longer matches the documented fixture.

## Recommended agent pipeline

For high-risk tasks, divide responsibility instead of asking one agent to do
everything:

1. **High:** define scope, architecture, threats, acceptance cases and rollback.
2. **Medium:** implement the approved contract and isolated tests.
3. **Low or medium:** run deterministic fixtures and organize safe evidence.
4. **High:** review the diff and failures, then decide whether a live check is ready.
5. **Human owner:** perform or authorize any remaining account, enrollment,
   private-data, device, deployment or publication step.

For T01, T07 and T08, medium can lead and request high review only at the stated
boundaries. For all other tasks, high reasoning leads from the beginning.

## Copy-ready assignments

### High

> Lead LYA task TNN at HIGH reasoning using LYA_IMPLEMENTATION_CHECKLIST.md and
> LYA_TASK_REASONING_LEVELS.md. Confirm dependencies, trace trust/data boundaries,
> define failure cases and preserve deny-by-default. Produce a reviewable design,
> implementation, evidence and rollback. Delegate only deterministic substeps.

### Medium

> Implement the approved MEDIUM-scope portion of LYA task TNN. Do not change its
> permission, privacy, storage, provider or release policy. Use temporary fixtures,
> complete the specified acceptance cases and escalate any boundary change.

### Low

> Complete only this LOW-scope deterministic LYA preparation: [exact deliverable].
> Use synthetic/public data and the supplied template. Do not access secrets,
> external services, private stores or production devices. Stop on ambiguity or
> unexpected output and return the artifact plus the command/result record.

Reasoning level never grants authority. The current user request and project rules
still determine whether a real external or sensitive action may occur.
