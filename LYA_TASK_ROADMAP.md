# LYA ordered delivery tasks

Execution guide: [LYA_IMPLEMENTATION_CHECKLIST.md](LYA_IMPLEMENTATION_CHECKLIST.md)
contains the developer handoff, steps, acceptance cases and reporting templates.
Assignment guide: [LYA_TASK_REASONING_LEVELS.md](LYA_TASK_REASONING_LEVELS.md)
separates high, medium and low reasoning work and defines escalation boundaries.

Planning date: 2026-09-15. This is the current execution order, refining the older
rebuild plans without replacing the product vision. Status is based on recorded
checks, not a fresh live-provider or hardware test. No deployment or data collection
is authorized merely by appearing in this plan.

## Starting point

- Implemented and previously live-tested: native typed panel -> brain -> Oracle ->
  Groq public-text answer. Only one dependable active provider is recorded.
- Implemented and isolated-tested: routing rules, encrypted scoped memory,
  retention, small knowledge graph and council orchestration. These do not prove
  a real authenticated private-memory journey or reliable council answers.
- Latest UI check: 16 tests passed. Original orb stays default; new GLB artwork is
  optional because short measurements showed higher CPU. Battery use is unmeasured.
- Open: evidence verification, independent backup, trusted session/phone binding,
  live offline wake, consented recognition, mobile access and safe tool execution.
- We are extending the verified core. Existing legacy modules are candidates for
  review, not proof that a capability works. No overall completion percentage yet.

## How to use this list

Follow the numbered integration order. Preparation can run in parallel as listed
below. Finish a task's acceptance checks before advertising it as working. If an
external prerequisite is missing, record the blocker and do independent preparation;
do not quietly remove privacy or quality requirements to continue.

Every completed task must record: changed files, checks and results, manual evidence
when relevant, known limitations, rollback, and next step in `lya-project-brain.md`.
Use temporary storage and fake credentials for automated tests. Keep real secrets,
faces and private runtime data out of this plan, screenshots and source control.

## 01 — Establish the release baseline

**Status:** complete on 2026-09-16; see
`review/2026-09-16-T01-baseline/README.md`. **Depends on:** nothing.
**Outcome:** we can reproduce the current app before changing its brain.

Work:
- Record the current Git diff and classify existing changes; do not overwrite them.
- Verify the documented `.cmd` launch, panel, typed command, cancel, sleep and quit.
- Confirm which interpreter/configuration is selected without displaying secrets.
- Define a reusable acceptance checklist and record the first baseline results.
- Confirm runtime data and credentials are excluded from ordinary source backups.

**Done when:** a repeatable launch/command/cancel/quit check has an evidence file;
known failures are listed; restart and rollback instructions are clear. This is
not permission to publish the repository or upload the entire project folder.
**Where:** `launch-lya.cmd`, `desktop/README.md`, a dated `review/` baseline report.
**Owner can prepare now:** ten commands you actually want to use every day.

## 02 — Make inference failure and backup dependable

**Status (2026-09-19):** the bounded router and pinned OpenRouter adapter pass
offline checks. Direct NVIDIA Nemotron 3.5 Lightning failed the eight-second gate
from laptop and Oracle. OpenRouter provider pinning is live-verified, but Nemotron became slow/truncated and
DeepSeek on OpenInference repeatedly missed the first-case deadline. An independent
live backup has not passed; no production activation. Evidence:
`review/2026-09-17-T02-backup/README.md`, `review/2026-09-19-nvidia-lightning/README.md`
and `review/2026-09-19-openrouter-live/README.md`. **Depends on:** 01.
**Outcome:** a slow, unavailable or quota-limited provider cannot trap LYA.

Work:
- Inventory configured provider names, exact endpoints, model IDs and actual
  upstreams using safe summaries. Resolve the unidentified gateway before use.
- Check account access, remaining quotas and data-handling settings at execution
  time. An API key or catalog listing alone does not establish a usable service.
- Evaluate one independent backup against the same synthetic tasks as Groq.
- Check timeout, HTTP 429, bad output, cancellation and exhausted-budget behavior.
- Prevent gateways from retrying the same upstream as an apparent independent backup.
- Preserve private-context denial; add transparent selected-route/failure messages.
- Keep explicit request/token limits and a verified no-paid-use policy for the
  owner's zero-subscription budget. Attempt limits alone are not spending caps.

**Done when:** two independent routes pass the agreed task set and repeated latency
checks, a synthetic primary failure reaches the backup, total work remains bounded,
and all-unavailable returns an honest error. Otherwise mark backup blocked.
**Where:** `cloud/router.py`, `cloud/inference.py`, `brain/oracle.py`,
`cloud/evaluate_models.py`, `LYA_MODEL_STRATEGY.md`, dated evaluation reports.
**Owner can prepare now:** provider/account inventory with exact service URLs and
free-limit screenshots that exclude secrets. Keep keys in protected configuration.

## 03 — Verify answers before presenting them as established facts

**Status (2026-09-20):** implementation and assistant scoring are complete; owner
review remains. The latest selected answers score 143/150, meet every frozen category
threshold and have zero critical privacy, source-fabrication or false-test failures.
Coding remains labelled proposed without trusted test evidence, sensitive content
fails closed, and research facts require direct citation support. All 106 offline
T01-T03 checks pass. See `review/2026-09-20-T03-evaluation/README.md`.
**Depends on:** 01; integrate after 02, but fixture preparation continues now.
**Outcome:** LYA distinguishes evidence, calculations, proposals and uncertainty.

Work:
- Build 30 reviewed acceptance cases: conversation, Tamil/English, factual research,
  coding/debugging, planning and privacy/refusal boundaries (five per category).
- Write expected facts or a scoring rubric before running the candidates.
- Connect an explicitly selected research tool for requests requiring current facts;
  preserve source URL, retrieval date and the claim each source supports.
- Treat instructions in fetched pages as untrusted content; they cannot grant tools
  or access to private memory. Check citations actually support the answer.
- Check deterministic calculations with a bounded computation path. Review code and
  run relevant tests in isolation before claiming that proposed code works.
- Show a concise rationale, missing evidence and disagreements; do not present
  hidden model reasoning or council agreement as verification.

**Done when:** critical privacy/source-fabrication failures are zero in the fixture
set; publish per-category results, unresolved failures and scope. A passing fixture
set is not a guarantee of universal accuracy. Set the release quality threshold
before evaluating; never lower it just to label a model ready.
**Where:** `brain/workflow.py`, a dated `review/` answer-evaluation pack.
**Owner can prepare now:** real-looking but non-private questions and trusted answers.

## 04 — Bind a trusted session and exact-action approval

2026-09-20: exact approval and first-admin registration contracts are fake-tested.
Registration can issue a bounded session, but the live Windows Hello adapter remains
pending. See review/2026-09-20-T04-admin-registration/README.md.


**Status:** real desktop remains guest. **Depends on:** 01–03.
**Outcome:** personal access comes from verified identity, not a name or orb color.

Work:
- Trace every UI/brain/tool entry through one authorization path.
- Define guest, owner and delegated-person permissions with concrete examples.
- Implement and test session expiry, lock, user change and profile revocation.
- Bind strong approval to the exact action, person, parameters and expiry; prevent
  replay or using approval for a different operation. Build with fake adapters first.
- Establish the phone/OS-backed verification adapter and test its actual supported
  iPhone flow before enabling sensitive access. No custom improvised authentication.
- Keep private data locked when verification is unavailable. Face matching later
  may personalize low-risk interactions but cannot replace this approval path.

**Done when:** guest-denial, approval expiry/replay, identity changes during a request
and lock-on-return checks pass, followed by the actual-device approval journey.
The owner requested enrollment setup on 2026-09-20. Synthetic foundation work is
authorized; real capture must still occur through the visible consent screen.
**Where:** native session integration and existing authorization modules, `brain/workflow.py`.
**Owner can prepare now:** a fictional role/permission table; no real biometric data.

## 05 — Complete the private memory lifecycle

**Status (2026-09-20):** scoped encrypted storage is isolated-tested; verified
personal inference now chooses the local client directly and approval requires
literal True. See `LYA_STORAGE_SECURITY_PLAN.md`. Real authenticated journey pending.
**Depends on:** 04; requires an eligible local/private inference path if a model
will read private notes. Do not relax cloud denial to make this pass.
**Outcome:** save, recall, correct and forget work for the verified person only.

Work:
- Reuse the existing SQLite/encryption foundation; inspect migration compatibility.
- Verify working context (one request), session notes, short-term (7-day default),
  longer-term (90-day default), user-chosen expiry and permanent-until-deleted notes.
- Retain source, owner, revision and expiry. A model answer is not automatically a fact.
- Test correction, duplicate labels, expiry during inference, crash/restart and
  relationships removed on deletion. Separate each person's retrieval scope.
- Explain where local data lives, how it is protected and what deletion can/cannot
  remove. Handle keys separately from ciphertext backups.
- Evaluate local inference on measured laptop resources only if needed; until then,
  deterministic authorized memory commands must work without a cloud model.

**Done when:** a verified user's save -> restart -> recall -> correct -> expire/delete
journey passes and another user cannot retrieve it; failures do not corrupt storage.
**Where:** `storage/store.py`, `brain/notes.py`, `brain/knowledge.py`, `brain/workflow.py`.
**Owner can prepare now:** fake notes with expected lifetime and correction examples.

## 06 — Make important-plan council useful and bounded

**Status:** orchestration exists; diverse live quality not established.
**Depends on:** 02–05, especially evidence verification.
**Outcome:** important plans receive a checked second perspective without wasting
multiple calls on ordinary conversation.

Work:
- Define when the user explicitly requests a council and when to offer one.
- Give planner, critic and verifier distinct responsibilities and shared evidence.
- Use eligible independent routes where available; disclose limited diversity.
- Set total time/token/attempt budgets, cancellation and partial-failure handling.
- Return a recommendation, evidence, tradeoffs, unresolved disagreements and next
  action. Council output never grants permission or automatically becomes memory.

**Done when:** a deliberately flawed plan is challenged, unsupported claims are
flagged, unavailable seats are disclosed and the task respects its total budget.
**Where:** `brain/council.py`, `brain/workflow.py`, evaluation fixtures.
**Owner can prepare now:** three project decisions with constraints and success criteria.

## 07 — Build the practical read-only floating file browser

**Status:** current view reads a few allowlisted project documents.
**Depends on:** 04–05; visual prototypes can start now.
**Outcome:** 'show my saved file' presents the right permitted item in compact glass.

Work:
- Add explicit folder selection, progressive listing, search, breadcrumb/back,
  keyboard navigation and understandable empty/error states.
- Enforce permitted roots after path resolution, including shortcuts/reparse paths.
- Load thumbnails/content lazily with size limits; keep requests off the UI thread.
- Start read-only. Add file edits/moves/deletes only as separately scoped capabilities.
- Keep role-specific locations separate and support cancellation/stale-result rejection.

**Done when:** a permitted file is found/opened, a forbidden path is denied, a large
fixture folder remains responsive and cancelled results do not reopen the panel.
**Where:** `desktop/app.py`, `desktop/layout.py`, file capability and isolated fixtures.
**Owner can prepare now:** sketches and a folder of dummy filenames/documents.

## 08 — Add offline wake and accessible voice commands

**Status:** voice bridge exists; whisper.cpp remains the selected offline ASR and
sherpa-onnx is selected for VAD/speaker identity. Runtime/model benchmarking and the
actual-device journey remain pending. See `LYA_CAMERA_VOICE_DECISION.md`.
**Depends on:** 01, 04, 07. Do not wait for face recognition to test voice.
**Outcome:** wake -> panel -> supported command -> stop works without the internet.

Work:
- Verify local speech-model availability and microphone permissions; install only
  the selected compatible model when implementing this milestone.
- Provide explicit listening/muted/error indicators and a reliable stop command.
- Test wake phrase, common commands, noise, accents, device unplug and false wakes.
- Keep command recognition separate from authorization and provider availability.
- Preserve keyboard/text alternatives; test hands-free selection, back and cancel.

**Done when:** an actual-device offline test completes the supported command journey,
stop releases recording, false-wake results are documented and idle CPU is measured.
Cloud reasoning may remain unavailable offline; LYA must say so clearly.
**Owner can prepare now:** wake phrases and 15 spoken-command examples, as text.

## 09 — Add consented recognition and person profiles

**Status:** owner requested setup; synthetic registration foundation passes. OpenCV
YuNet + SFace are selected for CPU face recognition and sherpa-onnx for speaker
identity; pinned model acquisition, adapters and real-device tests remain pending.
See `LYA_CAMERA_VOICE_DECISION.md`. **Depends on:** 04–05, 08.
**Outcome:** known people receive appropriate greetings and separate data access.

Work:
- Review model/license compatibility and camera performance before selecting it.
- Implement visible bounded capture, uncertainty handling and guest fallback.
- Add enrollment, removal and role changes through verified owner operations.
- Agree consent/retention before collecting any real template or visitor thumbnail.
- Test changing lighting, camera failure, unknown people and mismatches; recognition
  remains approximate and cannot grant confidential access by itself.

**Done when:** the explicitly authorized real-device journey passes, uncertain faces
remain guests, capture stops, deletion works and separate-person access tests pass.
**Owner can prepare now:** consent wording and fictional screen flows, not recordings.

## 10 — Prove encrypted backup and recovery

**Status (2026-09-20):** selected-note recovery core and native UI/file path are
implemented. Twelve core tests and ten UI/file tests pass, including an actual
temporary archive restored into a fresh local key. Real owner binding, real key
custody, clean-device drill and cloud transport remain pending; this task is not
complete. See `review/2026-09-20-recovery-interface/README.md`.
**Depends on:** 05 and working key-management decisions.
**Outcome:** losing a process or disk does not silently lose the approved memory/files.

Work:
- Specify exactly what is backed up, excluded, retained and deleted; no whole-.env
  upload or indiscriminate project-folder sync.
- Make a transaction-consistent encrypted snapshot, checksum and version manifest.
- Handle recovery keys separately, including recovery if Windows-bound keys are lost.
- Verify current Oracle capacity/quotas and storage pricing before remote activation.
- Restore into a clean temporary environment; test interruption, corruption and
  incompatible schema versions. Never overwrite the sole working database to test.

**Done when:** a sample backup restores correctly on the intended recovery path;
corruption fails safely; the owner has understandable recovery instructions.
**Where:** new dated restore evidence; reuse reviewed storage/backup components only.
**Owner can prepare now:** a list of essential data categories and acceptable loss window.

## 11 — Provide paired iPhone access and explicit offline behavior

**Status:** not implemented end to end. **Depends on:** 04, 05, 10.
**Outcome:** selected saved files/notes are accessible when away from the laptop.

Work:
- Choose the phone client after a small actual-iPhone feasibility test; document
  background, offline-cache and authentication limits before building the full UI.
- Define what may sync, encrypted transport/storage, device pairing and revocation.
- Distinguish a cloud-held copy from a file that exists only on a powered-off laptop.
- Provide an explicit encrypted offline-cache choice for selected content.
- Define conflict handling, revision checks, deletion propagation and stale warnings.
- Test laptop-off, cloud-off, phone-offline, lost-device revocation and reconnect.

**Done when:** a paired phone reads an intentionally synced sample while the laptop
is off; an unpaired/revoked phone is denied; an offline phone reads only cached data
and clearly reports unavailable items. Cloud access requires connectivity.
**Owner can prepare now:** five mobile journeys and which sample items need offline access.

## 12 — Add a bounded action executor

**Status:** model advice is not an execution engine. **Depends on:** 03–05, 07, 10.
**Outcome:** LYA carries out a small set of requested tasks and verifies the result.

Work:
- Register each tool's input schema, permissions, allowed targets, timeout,
  cancellation, output checks and rollback where possible.
- Start with reading an allowed file, opening an approved application and producing
  a draft in a designated folder. Add risky actions separately after review.
- Keep webpage/file instructions and model output unable to widen authorization.
- For coding, work in an isolated checkout, show the diff and run relevant checks.
- For security work, require explicit authorized target/scope and evidence; never
  treat a general 'hacking' capability as permission to operate on arbitrary systems.

**Done when:** each initial tool succeeds on its fixture, denies out-of-scope input,
can stop and reports success only after checking the actual result.
**Owner can prepare now:** three exact tasks with input, expected output and boundaries.

## 13 — Learn reusable workflows and appearance preferences

**Status:** planned. **Depends on:** 03, 05, 12; camera examples also require 09.
**Outcome:** a request can become a tested, versioned reusable skill or setting.

Work:
- Reuse existing tools/settings first. Draft a workflow with required permissions.
- Test using fixtures, show the result, activate within the user's authorized scope
  and retain a version with rollback. Reject unreviewed permission/core changes.
- Store validated preferences/lessons with provenance, correction and forgetting.
- For shared video references, extract useful layout requirements, preview settings
  and support undo. Do not continuously watch the phone to discover preferences.
- Distinguish remembering a workflow from retraining a model or simulating a human brain.

**Done when:** one benign workflow runs correctly after restart, fails safely when
a prerequisite is missing, and can be disabled/reverted; one theme change can undo.
**Owner can prepare now:** a permission-compatible reference and a specific desired behavior.

## 14 — Measure, harden and package the first everyday release

**Status:** ongoing checks; final release pending. **Depends on:** included release tasks.
**Outcome:** a small, honest supported feature set can be used daily.

Work:
- Measure laptop idle/active CPU, memory, startup, response latency and battery over
  meaningful intervals. Keep comparable original/new orb runs and record conditions.
- Test long sessions, sleep/resume, internet failure, provider failure, disk-full,
  interrupted writes and clean shutdown; define measurable release budgets first.
- Review dependencies, secret handling, permissions and update/rollback behavior.
- Package the verified app and recovery instructions. Publish a working/limited/
  unavailable capability list based on evidence, not presence of source files.
- Keep enrollment, provider activation and release publication as explicit runtime
  operations; planning alone does not perform them.

**Done when:** included feature journeys pass the release checklist on target devices,
critical failures are resolved and rollback is demonstrated. An earlier typed-only
preview can ship with voice/camera/mobile clearly excluded; do not wait for every
ambitious feature to provide a useful, truthful release.

## Work you can start now without waiting

Suggested owner work area: `planning/owner-inputs/`. Create only public or synthetic
material here. Do not put API keys, real personal notes or faces in this folder.

| Priority | Deliverable | What to include | Helps task |
| --- | --- | --- | --- |
| A | `daily-commands.md` | 10 commands, expected answer/action, failure behavior | 01, 03, 12 |
| B | `provider-inventory.md` | Service name, exact URL, upstream if known, free limits; no keys | 02 |
| C | `answer-cases.md` | Questions, checked answers/sources, Tamil/English examples | 03 |
| D | `file-browser-design.md` | Small glass layout, back/search/empty/loading states, light/dark versions | 07 |
| E | `sample-data/` | Dummy files and notes with example expiry/correction | 05, 07 |
| F | `roles-and-phone.md` | Fictional role table; five phone/offline journeys | 04, 09, 11 |
| G | `skill-examples.md` | Three useful workflows, permissions, success and undo | 12, 13 |

If you want to code independently, start a separate branch for a visual prototype
using dummy data. Coordinate ownership before editing `desktop/app.py`,
`brain/workflow.py`, `storage/store.py` or cloud routing, so concurrent work does
not overwrite changes. Bring back the deliverable path, what changed and what you
tested. The orb is usable already; more 3D detail is optional, not the next blocker.

## The next focused session

Complete task 01's baseline, then implement/evaluate task 02. If exact backup
provider details are missing, prepare task 03's evaluation fixtures and record
that task 02 remains blocked. Do not claim backup is complete from a mock test.
No automatic background work or recurring task is scheduled by this document.
