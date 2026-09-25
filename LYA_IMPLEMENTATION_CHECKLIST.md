# LYA implementation checklist and developer handoff

Updated: 2026-09-16. This is the execution companion to [the roadmap](LYA_TASK_ROADMAP.md).
Read [the project brain](lya-project-brain.md) first: newer evidence may change the starting point.
Task checkboxes are work to perform, not claims of completed implementation.
Use [the reasoning-level guide](LYA_TASK_REASONING_LEVELS.md) to assign high,
medium and low work without giving a lower-level agent security decisions.

## Start any task here

1. Read `AGENTS.md`, the latest brain ledger, this introduction and the selected task.
2. Inspect current source and Git diff. Preserve pre-existing changes and private data.
3. Claim one task ID and its files. Confirm dependency evidence before integration.
4. Implement the smallest useful change. Existing legacy modules require inspection, not blind reuse.
5. Test with fake credentials, synthetic identities and temporary stores first.
6. Run device/live checks only within applicable authorization. A mock pass is not a live pass.
7. Save safe evidence in a NEW `review/YYYY-MM-DD-TNN-description/` directory.
8. Update the brain ledger and affected guides with changes, results, limitations and next step.

Do not guess endpoints, entitlements, credentials, authentication or retention preferences.
Record the exact missing input and continue independent fixture work. Routine code choices
can be made and documented. Existing owner authorization applies; this document itself does
not authorize enrollment, real data upload, paid services or deployment.

Use these statuses: planned, building, isolated-tested, live-tested, blocked, deferred, complete.
Complete means all mandatory acceptance cases passed and the handoff is recorded.
Report each case as PASS, FAIL, BLOCKED or NOT RUN, with an evidence path.

## Boundaries that every task must preserve

- Native PySide6 remains the primary UI. Slow work stays off the UI thread.
- Original orb stays default; model artwork is optional. Battery impact is unmeasured.
- Names, orb colors and model output grant no authority. Default session is guest.
- Private cloud routes remain denied until an eligible policy/path is explicitly established.
- Enrollment is deferred until the owner requests setup. Do not collect faces/audio for fixtures.
- Never print or commit secrets, private notes, biometric data or active configuration.
- Do not overwrite real stores for testing or put recovery keys beside ciphertext backups.
- Model output is advisory until validated; it cannot authorize itself or become memory automatically.
- Do not replace the project with another framework, install every repository or add a graph server by default.

## Existing source map

All paths below are relative to this repository. Confirm current contents before editing.

| Area | Starting files and symbols |
| --- | --- |
| UI | `desktop/app.py`: Desktop, Crystal; `desktop/layout.py`; `desktop/check_ui.py` |
| Launcher | `launch-lya.cmd`, `desktop/README.md` |
| Brain | `brain/workflow.py`: Brain.respond, bind_session, _authorize, Answer, LocalModel |
| Providers | `brain/oracle.py`: OracleModel.invoke; `cloud/router.py`: route_request; `cloud/inference.py` |
| Evaluation | `cloud/evaluate_models.py`, `cloud/probe_models.py` are explicit LIVE utilities |
| Permissions | `security/policy.py`: Session; `security/escalation.py` is an integration candidate |
| Memory | `storage/store.py`, `security/vault.py`, `brain/notes.py`, `brain/knowledge.py` |
| Council | `brain/council.py`: deliberate; distinguish older entry points |
| Files | `skills/files.py`: FolderBrowser is paged metadata navigation, not a finished desktop view |
| Voice | `audio/voice.py`: wake_loop, process_utterance; native voice bridge in desktop/app.py |
| Identity | `vision/identity.py`, `vision/face_auth.py`, `security/enroll.py` |
| Phone | `skills/phone.py`: legacy candidate, not proof of working iPhone integration |
| Skills | `skills/forge.py`, `skills/governor.py`, `skills/guardian.py`: review before reuse |

## Environment and verification

Run from the repository root in PowerShell:

```powershell
Get-Location
git status --short --branch
git diff --stat
Test-Path .\.venv-ui\Scripts\python.exe
.\.venv-ui\Scripts\python.exe --version
```

Previously isolated checks are below. Read the scripts and changed imports first.
Run separately so temporary vault state cannot leak between suites. Do not run blanket
legacy test discovery: some older tests touch real stores or external services.

```powershell
.\.venv-ui\Scripts\python.exe -B test_router.py
.\.venv-ui\Scripts\python.exe -B test_oracle.py
.\.venv-ui\Scripts\python.exe -B test_provider_setup.py
.\.venv-ui\Scripts\python.exe -B test_brain_workflow.py
```

Review `desktop/check_ui.py` before using it: its main entry writes QA artifacts.
Direct new outputs to a fresh dated folder instead of overwriting existing evidence.
Offscreen font setup may require explicitly loading Segoe UI; record test setup.
Do not change product fonts simply to compensate for a test environment.
`cloud/evaluate_models.py` makes real calls and consumes quota; it is not an offline test.

## Integration sequence

| ID | Task | Prerequisites | Independent preparation |
| --- | --- | --- | --- |
| T01 | Baseline | None | Daily commands |
| T02 | Backup provider | T01 | Account inventory, fake failures |
| T03 | Answer verification | T01; T02 for multiple providers | Rubrics, source fixtures |
| T04 | Trusted session | T01, T03 | Role table, fake approval |
| T05 | Private memory | T04 | Temporary-store lifecycle tests |
| T06 | Council | T02-T05 | Flawed-plan fixtures |
| T07 | Files | T04-T05 | Dummy-data glass prototype |
| T08 | Voice | T01, T04, T07 | Command grammar, simulated events |
| T09 | Recognition | T04-T05, T08, enrollment request | Synthetic embeddings, consent UX |
| T10 | Recovery | T05 | Dummy snapshot/restore |
| T11 | iPhone | T04-T05, T10 | Device feasibility and UX |
| T12 | Executor | T03-T05, T07, T10 | Fake tool contracts |
| T13 | Skills | T03, T05, T12 | Workflow drafts |
| T14 | Release | All features included in release | Measurement protocol |

Preparation can run earlier. Production integration must not pretend dependencies passed.

## T01 - Reproduce the baseline

**Status (2026-09-16): complete.** Evidence:
[`review/2026-09-16-T01-baseline/README.md`](review/2026-09-16-T01-baseline/README.md).
Owner test instructions and visual flow: [`LYA_TEST_GUIDE.md`](LYA_TEST_GUIDE.md).

**Outcome:** a repeatable known state before changing the brain.
**Read:** launcher, desktop README, current app worker/cancellation flow and latest ledger.
**Inputs:** current checkout/environment; ten public or deterministic daily commands.
**Scope excludes:** provider changes, sensors, enrollment and deployment.

- [x] Record revision, branch and pre-existing modified/untracked paths without secret contents.
- [x] Confirm interpreter and documented launcher exist; diagnose a missing dependency narrowly.
- [x] Review and run relevant isolated baseline checks; record existing failures honestly.
- [x] Launch `launch-lya.cmd` once after quitting only the instance under test.
- [x] Try `brain help`, `who am i`, `brain status` and supported local commands.
- [x] Exercise panel close/reopen, cancel, sleep and quit. Check late output cannot reopen a dismissed panel.
- [x] Record any authorized live cloud test separately from offline startup evidence.
- [x] Write recovery instructions that preserve unrelated changes.

**Acceptance cases:** A: native panel opens and accepts input. B: session reports guest
truthfully. C: cancellation suppresses stale output. D: quit ends processes started by
this test. E: environment and all check outcomes are recorded.
**Blocker handling:** missing interpreter/configuration means diagnose first, not mass installation.
**Deliver:** baseline report, command/result table, failure list, safe rollback instructions.

## T02 - Dependable independent model backup

**2026-09-19 evidence:** bounded routing and the exact-model, pinned-upstream OpenRouter
adapter pass offline checks. Direct NVIDIA Nemotron 3.5 Lightning failed the deadline
from laptop and Oracle. OpenRouter provider pinning was then verified live, but both
pinned free candidates failed the latency/completion gates. Deployment, forced live
backup and a passing independent route remain pending. T02 is not complete. See
`review/2026-09-17-T02-backup/README.md`, `review/2026-09-19-nvidia-lightning/README.md`
and `review/2026-09-19-openrouter-live/README.md`.

**Outcome:** provider failure ends in a bounded fallback or a clear error.
**Read:** model strategy, cloud README, oracle/router/inference and their isolated tests.
**Inputs:** exact service URL, model ID, upstream identity, current account access and limits.
**Scope excludes:** private upload, arbitrary gateways, paid upgrades and model training.

- [x] Inventory relevant configuration names/readiness only; never print key values.
- [ ] Verify candidate endpoint/model/account availability from authoritative sources at implementation time.
- [x] Group routes by actual upstream: direct Groq and a gateway using Groq are one failure domain.
- [x] Define attempts, token allowance, total deadline and allowed data class before calling.
- [x] Add fake timeout, 429, malformed/empty reply, cancellation and all-down cases.
- [x] Verify persistent counters/cooldowns and no attempt after the total deadline.
- [x] Verify private input never reaches an ineligible primary OR backup.
- [x] Run bounded synthetic live evaluation for one candidate under applicable authorization.
- [x] Review answer correctness and latency, not HTTP completion alone.
- [ ] Activate only a passing route; exercise the desktop-to-Oracle path with synthetic public input.

**Acceptance cases:** A: independent backup succeeds after simulated primary failure.
B: all-down returns an honest error. C: private route denial holds. D: total budget and
counters hold across invocations. E: repeated live candidate checks and full-path check
pass the predeclared limits. Mock failover alone cannot complete this task.
**Blocker handling:** unknown gateway/upstream, quota or billing policy keeps that route disabled.
**Deliver:** comparison, sanitized config structure, fake/live results and secure rollback plan.

## T03 - Verify answer claims

**2026-09-20 status:** implementation and assistant review are ready for owner
confirmation. A conservative source-support gate rejects unsupported factual words
or numbers. Coding answers remain explicitly proposed unless trusted test evidence
exists. Sensitive and cross-person requests fail closed, and stable hardware and
zero-spend plans use bounded local responses. All 106 offline checks pass. The final
30-case selection scores 143/150 and meets every frozen category threshold with zero
critical failures. It is assistant-scored, so independent owner review remains open.
Evidence: `review/2026-09-20-T03-evaluation/README.md`.

**Outcome:** evidence, uncertainty and proposed code are distinguishable.
**Read:** Brain.respond, Answer and previous live-model evaluation failures.
**Inputs:** 30 reviewed fixtures: five each conversation, Tamil/English, research,
coding, planning and privacy boundaries. Freeze quality thresholds before scoring.
**Scope excludes:** perfect-accuracy claims and unrestricted execution of generated code.

- [x] For each case define ID, prompt, data class, expected facts, forbidden claims and rubric.
- [x] Include unknown answers, missing evidence and misleading-source instructions.
- [x] Specify source ID, URL, retrieval time, supported claim and bounded excerpt.
- [x] Define and mock an injectable research adapter; absence blocks before model use.
- [x] Bound source count and bytes and pass a fixed deadline to the adapter.
- [x] Connect an opt-in read-only adapter that enforces the HTTP deadline and fails closed; live acceptance remains pending.
- [x] Keep source instructions untrusted: they cannot grant permissions or retrieve private notes.
- [x] Check that citations support associated claims; label inference and uncertainty. The current deterministic gate is conservative; human review still handles difficult paraphrases.
- [x] Never say generated code works without trusted test evidence; unverified code remains a labelled proposal. Unrestricted generated-code execution stays excluded.
- [x] Return conclusion, brief rationale, evidence and missing facts, not hidden reasoning as proof.
- [x] Record quality and latency separately per category; preserve failed and rate-limited runs.

**Acceptance cases:** A: invented source fails. B: unsupported claim is removed/labelled.
C: source instructions cannot widen access. D: code gets no success claim without checks.
E: zero critical privacy failures; predeclared category thresholds met with failures visible.
**Blocker handling:** unavailable research adapter means live research blocked; fixture work can continue.
**Deliver:** case pack, evidence contract, scored results, limits and integration changes.

## T04 - Trusted session and approval

2026-09-20: exact-approval and first-admin registration foundations are fake-tested.
Session issuance is implemented behind the registration contract; live Windows Hello
and device integration remain pending. See review/2026-09-20-T04-admin-registration/README.md.


**Outcome:** private operations require verified identity and exact-action approval.
**Read:** `security/policy.py`, `security/escalation.py`, Brain.bind_session/_authorize.
**Inputs:** role/action table, chosen phone/OS verifier, fake approval adapter for development.
**Scope excludes:** face enrollment, improvised cryptography and production approval bypasses.

- [ ] Map each entry point to its permission; unknown capabilities deny by default.
- [x] Define trusted session ID, person ID, role, expiry and active-profile validation.
- [x] Clear temporary context on identity change, lock, expiry and revocation.
- [x] Bind each approval to person, unique challenge, exact action/parameters, expiry and single consumption.
- [x] Test a fake adapter before connecting a real supported phone/OS mechanism.
- [x] Recheck identity before accessing data and before presenting delayed results.
- [ ] Run authorized actual-device verification separately; unavailable verification leaves private work locked.

**Acceptance cases:** A: typed admin name grants nothing. B: expired/replayed approval fails.
C: changed parameters invalidate approval. D: changed identity suppresses old output.
E: revoked profile is denied. F: actual-device verification works before private access is enabled.
**Blocker handling:** unresolved verifier means fake integration only; never ship `approve=lambda: True`.
**Deliver:** permission matrix, adapter contract, entry-point map, tests and device evidence.

## T05 - Private memory lifecycle

**Outcome:** scoped save, recall, correct, expire and forget survive restart safely.
**Read:** `storage/store.py`, `security/vault.py`, `brain/notes.py`, `brain/knowledge.py`, workflow guide.
**Inputs:** verified-session adapter, fake Alice/Bob, disposable key/store and controllable clock.
**Scope excludes:** auto-saving conversations, new database server and private cloud fallback.

- [ ] Inspect schema/migration behavior; use additive changes and old-schema fixtures where needed.
- [ ] Preserve owner, kind, source, revision, retention and expiry per record.
- [ ] Check request context and session notes clear on their documented boundaries.
- [ ] Exercise short 7-day, long 90-day, explicit timezone-aware expiry and permanent-until-deleted notes.
- [ ] Require explicit save/correction; correction must not silently reset retention.
- [ ] Scope retrieval/graph endpoints to one person and exclude expired/credential records.
- [ ] Check duplicate labels, stale search after correction, linked deletion and expiry during inference.
- [ ] Inject failed writes and restart temporary storage to verify transaction consistency.
- [ ] Keep deterministic memory commands usable without a model; private model-assisted answers require an eligible route first.
- [ ] After authorization setup, demonstrate the real lifecycle with non-sensitive sample content.

**Acceptance cases:** A: Bob cannot retrieve Alice notes. B: expired notes never reach inference.
C: correction removes stale search results. D: deletion removes relationships. E: valid notes survive restart.
F: failed write leaves a valid store. G: private cloud denial remains intact.
**Blocker handling:** unclear encryption/migration means no production-store operation.
**Deliver:** schema delta, lifecycle results, retention examples and separate real-session evidence.

## T06 - Bounded council reasoning

**Outcome:** important plans receive useful criticism without unlimited calls.
**Read:** `brain/council.py` deliberate, workflow, routing and T03 evidence contract.
**Inputs:** eligible routes; three flawed plans with known errors; fixed total budget.
**Scope excludes:** claiming same-model repetition is independent confirmation.

- [ ] Preserve council permissions and explicit trigger; routine conversation stays inexpensive.
- [ ] Give planner, critic and verifier distinct responsibilities and the same scoped evidence.
- [ ] Declare actual provider/model diversity and unavailable seats.
- [ ] Budget every call including synthesis; stop further calls on cancellation or identity change.
- [ ] Present recommendation, evidence, alternatives, disagreements and missing facts.
- [ ] Keep results advisory and unsaved unless separately requested and authorized.

**Acceptance cases:** A: known contradiction surfaced. B: unsupported consensus not called fact.
C: failed seats disclosed. D: total time/attempt/token budget respected. E: cancelled result suppressed.
F: decision quality meets the predeclared T03 rubric.
**Blocker handling:** one provider can offer perspectives but cannot be labelled an independent council.
**Deliver:** seat specifications, scored fixtures, budget results and limitations.

## T07 - Floating read-only file browser

**Outcome:** permitted files appear in a responsive compact glass panel.
**Read:** `skills/files.py` FolderBrowser, native worker/layout and policy.
**Inputs:** explicit approved root; dummy nested/Unicode/empty/large/unreadable folder fixtures.
**Scope excludes:** file deletion/move, launching executables and whole-disk indexing.

- [ ] Use an explicitly approved root; the browser's home-directory default is not authorization.
- [ ] Connect paged listing to a background worker with loading, empty and error states.
- [ ] Tie breadcrumbs, selection, back and pagination to current request state.
- [ ] Resolve and check paths at use time; reject outside-root links/junctions and stale selections.
- [ ] Add bounded read-only previews for declared file types; cap bytes and handle decoding failure.
- [ ] Label search scope; start with current-folder search rather than implicit recursive scanning.
- [ ] Preserve cancellation, stale-result rejection, keyboard focus and light/dark readability.

**Acceptance cases:** A: allowed file previews. B: outside-root traversal denied.
C: back stays within root. D: large listing remains bounded/responsive. E: removed/unreadable file
shows recoverable error. F: cancelled panel stays closed. G: keyboard-only journey works.
**Blocker handling:** undefined roots/types means dummy-data prototype only.
**Deliver:** preview/root contract, fixture checks, synthetic screenshots and timing results.

## T08 - Offline wake and voice commands

2026-09-21: whisper.cpp remains selected for offline transcription; sherpa-onnx is
selected for VAD and speaker identity. A sensor-free probe confirms OpenCV/NumPy/
sounddevice but sherpa-onnx and all pinned biometric models are still missing. See
`LYA_CAMERA_VOICE_DECISION.md`; installation and device testing remain open.

**Outcome:** actual laptop wake, command and stop operate without network transcription.
**Read:** `audio/voice.py` wake_loop/process_utterance and desktop voice bridge.
**Inputs:** compatible offline model, microphone, text grammar and authorized device session.
**Scope excludes:** hidden recording and automatic online speech fallback.

- [ ] Verify model/dependency versions and local path before installation or capture.
- [ ] Exercise fake readiness/error/transcript events through native dispatch.
- [ ] Enforce offline mode and show listening, mute and failure indicators.
- [ ] Keep one bounded recording stream; typed and spoken commands share permissions.
- [ ] Test stop while listening/speaking, permission denial, unplug and repeated start/stop.
- [ ] Run actual offline commands; record success, missed wake and false-wake counts without retaining private audio.
- [ ] Measure idle CPU and sleep/resume behavior; preserve text/keyboard fallback.

**Acceptance cases:** A: wake opens panel offline. B: supported local command succeeds.
C: stop releases recording. D: no online transcription. E: unplug recovers.
F: false/missed wake counts and conditions are documented, not claimed perfect.
**Blocker handling:** missing model/device or capture authorization leaves fixture testing only.
**Deliver:** setup/model guide, command grammar, device results and resource measurements.

## T09 - Consented recognition and profiles

2026-09-20: owner requested primary-admin enrollment. Synthetic registration and
encrypted storage contracts pass; no real camera/microphone capture has occurred.

2026-09-21: OpenCV YuNet + SFace were selected for the laptop's CPU camera path.
OpenCV 5.0 already exposes the required APIs. Exact model artifacts, hashes,
adapters, capture controls and local calibration remain pending. Face/voice cannot
authorize protected actions; Windows Hello PIN remains the trusted checkpoint.

**Outcome:** approximate personalization, guest fallback and separate person data.
**Read:** `vision/identity.py`, face-auth/enrollment code and foundation decisions.
**Inputs:** explicit enrollment request, participant consent, camera and agreed retention.
**Scope excludes:** silent surveillance or confidential access granted by face match alone.

- [ ] Verify selected embedding model/license/dependency compatibility.
- [ ] Test synthetic embeddings and profiles with temporary encrypted storage first.
- [ ] Implement visible bounded capture and no-face/multiple-face/uncertain-match handling.
- [ ] Require verified owner operations for enrollment, role changes and removal.
- [ ] Agree purpose, retention and deletion before retaining visitor thumbnails.
- [ ] Test lighting changes, uncertainty and spoof attempts only with authorized participants.
- [ ] Release camera reliably and preserve stronger verification for private operations.

**Acceptance cases:** A: uncertainty means guest. B: capture visibly ends.
C: naming a person cannot escalate privileges. D: forgotten profile stops matching.
E: person separation holds. F: measured mismatches and conditions are reported.
**Blocker handling:** no enrollment request/consent means no real collection; this gate remains deferred.
**Deliver:** synthetic tests, consent/retention specification and safe device results without biometrics.

## T10 - Encrypted backup and recovery

**Outcome:** approved data can be restored without risking the sole working copy.
**Read:** storage/vault key and transaction behavior; inspect `brain/sync.py` before reuse.
**Inputs:** backup inclusion list, retention, loss window and recovery-key strategy.
**Scope excludes:** raw project/.env sync and restore testing over the production database.

- [ ] Separate source code, private runtime records, approved files and credentials in the backup specification.
- [ ] Produce a transaction-consistent snapshot with version, creation time, checksum and safe key reference.
- [ ] Use maintained authenticated encryption; never store recovery keys next to backups.
- [ ] Prove the intended recovery path: Windows-account-bound keys alone do not prove recovery on another device.
- [ ] Verify current remote quotas/costs and upload authorization before real backup activation.
- [ ] Restore synthetic data into a fresh directory and compare revisions, relationships and expected content.
- [ ] Inject interruption, corruption, wrong/missing key and incompatible schema; retain the last good copy.
- [ ] Define retention and how deletions affect backups; state forensic-erasure limits.

**Acceptance cases:** A: restored fixture matches. B: wrong key/corruption fails safely.
C: failed backup preserves good copy. D: intended recovery target works.
E: evidence has no plaintext secrets/private records.
**Blocker handling:** unresolved recovery key means backup incomplete even if upload succeeds.
**Deliver:** backup format/policy, restore guide and simulated disaster results.

## T11 - Paired iPhone access

**Outcome:** intentionally synced content is available away from the laptop.
**Read:** T04 approval/T10 recovery contracts; inspect legacy `skills/phone.py` before reuse.
**Inputs:** actual iPhone, verified client feasibility, approved sync scope and pairing mechanism.
**Scope excludes:** exposing full-server SSH credentials or promising internet-free remote retrieval.

- [ ] Prototype actual-device secure storage, authentication and cache behavior before choosing a full client.
- [ ] Record current platform background limits and alternatives with evidence.
- [ ] Bind least-privilege device credentials to a verified person and revocation mechanism.
- [ ] Define revision, conflict and deletion rules before implementing synchronization.
- [ ] Sync only selected content over authenticated encrypted transport.
- [ ] Distinguish laptop-only, cloud-held and phone-cached copies visibly.
- [ ] Test laptop off, server down, phone offline, reconnect and revoked device.
- [ ] Define offline cache expiry/reauthentication: a disconnected device cannot instantly learn remote revocation.

**Acceptance cases:** A: paired phone reads synced fixture with laptop off.
B: unpaired access denied. C: server rejects revoked device. D: offline access limited to selected cache.
E: edits/deletes reconcile per policy. F: unavailable content explains the reason.
**Blocker handling:** unverified client or scope means feasibility prototype only.
**Deliver:** device feasibility record, pairing/sync specification and connectivity test matrix.

## T12 - Bounded action executor

**Outcome:** requested supported actions execute within scope and report verified results.
**Read:** policy, workflow, command handlers and legacy governor/guardian/forge before reuse.
**Inputs:** three initial tools: read allowed file, open approved app, write draft in a designated folder.
**Scope excludes:** arbitrary shell execution, automatic deployment or unscoped security operations.

- [ ] Define each tool's ID, argument schema, permission, target scope, timeout and result checks.
- [ ] Separate model proposals from validated execution; reject unknown tools/arguments.
- [ ] Recheck identity/approval immediately before side effects and bind exact parameters.
- [ ] Implement fake tools for partial failure, cancellation and duplicate request tests.
- [ ] Bound retries; do not repeat non-idempotent actions blindly after a timeout.
- [ ] Exercise actual initial tools only within authorized scope and verify produced results.
- [ ] Log safe outcomes/artifact references, excluding secret arguments.
- [ ] Require explicit target authorization for security work; a skill name grants no authority.

**Acceptance cases:** A: valid fixture succeeds. B: unknown/out-of-scope tool denied.
C: parameter changes invalidate approval. D: cancellation stops later steps.
E: partial success is reported accurately. F: success depends on actual observed outcome.
**Blocker handling:** unclear target/action authorization means prepare a concrete proposal first.
**Deliver:** tool contracts, fake/real evidence, retry rules and rollback instructions.

## T13 - Reusable skills and appearance learning

**Outcome:** tested workflows/preferences persist with versioning and undo.
**Read:** T12 tool contracts, memory retention, existing forge/theme handlers.
**Inputs:** one benign workflow and one explicitly shared visual reference.
**Scope excludes:** automatic core rewriting, model training or continuous phone watching.

- [ ] Translate request into available tools/settings; reuse capabilities before generating code.
- [ ] Define version, prerequisites, parameter schema, required permissions and success checks.
- [ ] Save draft inactive; validate with dummy inputs and the bounded executor.
- [ ] Preview concrete behavior and activate within applicable owner authorization.
- [ ] Store approved version/provenance; keep credentials/private inputs outside skill definitions.
- [ ] Test restart, disable, update and rollback; block silent permission expansion.
- [ ] Implement style changes through bounded settings where possible and demonstrate undo.
- [ ] Distinguish validated lessons from unverified facts; support correction/forgetting.

**Acceptance cases:** A: skill works after restart. B: missing prerequisite fails safely.
C: disabled version cannot execute. D: update cannot silently widen authority.
E: appearance change can undo. F: saving generated code never executes it automatically.
**Blocker handling:** unavailable tool is a prerequisite to build, not a capability to invent.
**Deliver:** versioned example, permission manifest, fixture results and rollback demonstration.

## T14 - Measured release and packaging

**Outcome:** a clearly scoped everyday release with verified behavior.
**Read:** reports for every included task, desktop QA and current dependency files.
**Inputs:** explicit release scope, target hardware, performance budgets and recovery evidence.
**Scope excludes:** declaring all planned features complete or publishing without authorization.

- [ ] List included/excluded features and required evidence for each.
- [ ] Define CPU/memory/startup/latency/cancellation budgets before measurement.
- [ ] Record hardware, OS, power mode, brightness, background load and network/model route.
- [ ] Measure distributions and repeated runs, not only best results.
- [ ] Compare orb variants under matched workloads; use meaningful battery intervals, not paint-time inference.
- [ ] Test long sessions, sleep/resume, provider failure, disk-full and interrupted writes with safe fixtures.
- [ ] Review dependency licenses, credential handling, logs and update permissions.
- [ ] Package without developer secrets, SSH keys or private runtime stores.
- [ ] Verify clean install, upgrade and rollback in disposable storage.
- [ ] Write accurate supported/limited/unavailable release notes and obtain any still-required publication authorization for the completed artifact.

**Acceptance cases:** A: all included journeys pass. B: no unresolved critical privacy/data-loss failure.
C: predeclared performance limits met or scope reduced explicitly. D: install/rollback works.
E: package excludes credentials/private material.
**Blocker handling:** repair or exclude failing feature; an earlier typed-only preview may ship with limits stated.
**Deliver:** artifact path/hash, release checklist, performance report and recovery guide.

## Open decisions: never fill these with guesses

| Decision | Needed by | How to resolve | Until resolved |
| --- | --- | --- | --- |
| Exact backup service/upstream | T02 | Owner inventory plus current official/account evidence | Route disabled |
| Quality/latency limits | T02-T03 | Define from use cases before evaluation | Exploratory results only |
| Phone/OS verifier | T04 | Actual-device feasibility and reviewed authentication design | Fake adapter; guest lock |
| Private inference route | T05 | Measured local option or explicitly eligible provider policy | Deterministic memory only |
| Approved folders | T07 | Owner selects scope | Dummy fixture browser |
| Offline speech model/device | T08 | Local inspection and authorized device check | Typed commands |
| Enrollment/visitor retention | T09 | Owner setup request and consent | No collection |
| Recovery keys/retention/loss window | T10 | Owner needs and tested recovery design | No real backup activation |
| iPhone client/sync scope | T11 | Device prototype and owner choices | Fixture prototype |
| Action scope/permissions | T12-T13 | Concrete request and tool policy | Inactive draft |
| Release budgets/distribution | T14 | Baseline measurements and chosen scope | No readiness claim |

## Ready-to-copy task assignment

> Work on task TNN in LYA_IMPLEMENTATION_CHECKLIST.md. Read AGENTS.md and
> lya-project-brain.md first. Confirm prerequisites from evidence and inspect current
> source/diff. Preserve unrelated changes. Implement only the selected task scope.
> Use fake credentials and temporary stores for tests. Record missing inputs rather
> than inventing endpoints, permissions or features. Complete its acceptance cases,
> save safe dated evidence, update the brain ledger, and report changes, limitations,
> rollback and the next step. Distinguish isolated tests from real integration checks.

Replace TNN and add the developer name, owned files and any specific runtime
authorization. This prompt alone does not authorize enrollment, uploads or deployment.

## Ready-to-copy completion report

```text
Task ID/title:
Developer/date:
Status: planned/building/isolated-tested/live-tested/blocked/deferred/complete
Starting revision and pre-existing changes:
Dependency evidence paths:
Owned files and changed files:
Decisions and reasons:
Implemented behavior:
Acceptance case ID | PASS/FAIL/BLOCKED/NOT RUN | evidence path:
Commands/environment:
Live/device checks, separate from mocks:
Quality/performance results and measurement limits:
External calls/data/deployment involved (safe summary only):
Rollback/recovery:
Unresolved question and exact missing input:
Next smallest step:
Brain ledger updated:
```

Identify acceptance cases by task and letter, such as T05-C. The report must cover
all cases, including failures and checks not run. A source file existing is not evidence
that its feature works. A future output path is not evidence until the artifact exists.

## Independent owner work and avoiding conflicts

You can immediately prepare daily-command examples, fake notes, file-browser screens,
provider names/URLs without keys, and phone journeys. Keep these under a proposed
`planning/owner-inputs/` folder using the filenames listed in the roadmap.
A dummy-data visual prototype can start before authentication, but must stay labelled
as a prototype until integrated and tested against the real permission boundary.

Coordinate ownership before concurrent editing of `desktop/app.py`, `brain/workflow.py`,
`storage/store.py` or routing files. Use separate branches/checkouts where practical;
review each diff and integrate in dependency order. Do not duplicate production secrets
or runtime stores into every checkout. Preserve other workers' uncommitted changes.

This checklist does not launch background work. It makes tasks independently understandable;
it does not remove dependencies or guarantee that no future clarification will be needed.
