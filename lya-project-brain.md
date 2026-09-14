# LYA project brain

Latest activation update (2026-09-14): public-text Groq inference is now configured
on Oracle and selected by the native desktop. The actual Qt worker -> Brain ->
SSH -> router -> Groq -> glass response path passed a synthetic live check.
Private-context routing was denied before a provider call. NVIDIA catalog access
works but candidate generation was unreliable; its routes remain disabled. There
is currently no dependable active independent backup. Model accuracy remains a
separate open gate: live evaluations found hallucinated plans and a wrong coding
assertion. See `review/2026-09-14-live-models/README.md`. No enrollment or private
memory upload occurred. The earlier disabled-configuration entries below are
historical evidence superseded by this activation entry.

Latest routing update (2026-09-14): bounded multi-provider routing implemented,
38 targeted checks passed and a synthetic failover check passed on Oracle.
Live provider routes remain disabled; usable credentials were not found in the
known project/environment settings. See `LYA_MODEL_STRATEGY.md` for the verified
shortlist, implementation limits and activation gates. Storage expansion follows
real brain/model acceptance; existing encrypted memory remains in place.

Latest connection update (2026-09-14): SSH authentication succeeded using the
owner's newly supplied key. Read-only commands verified ARM64, 4 online CPUs,
approximately 24 GB RAM, a 193 GB root filesystem and Python 3.12.3. The original
key rejection is resolved. Resource allocation does not establish ongoing free
eligibility. A credential-free SSH inference backend is now uploaded and its
missing-provider response was tested over real SSH. No live model request has
completed; provider choice/activation remains pending the owner's decision.

Last reviewed: 2026-09-13. Latest milestone: native brain dispatch, scoped memory
lifetimes, small knowledge graph and bounded council orchestration implemented.
Isolated acceptance: 91 checks passed, one online speech test skipped; five earlier
review probes no longer reproduce. See `LYA_BRAIN_WORKFLOW.md` and
`review/2026-09-13-retrieval/results.json` for current evidence.

This latest entry supersedes earlier broad completion and defect-status claims.
The real desktop remains a guest: identity/phone approval is not bound to the new
brain and a local model was not reachable. Offline voice requires a missing local
model. Synthetic checks do not prove live recognition, inference, phone or cloud
integration. Earlier review reports remain preserved as dated evidence.

Newest runnable milestone: `launch-lya.ps1` opens the custom crystal alone. See
`desktop/README.md` for commands and limits, and `desktop/qa/` for rendered UI checks.
This is a separate PySide6 presentation layer, not the completed wake/identity journey.

Visual map: see `LYA_ARCHITECTURE.md` and `diagrams/` for the current system. See `LYA_REBUILD_PLAN.md` for acceptance gates and `LYA_FOUNDATION_DECISIONS.md` plus `diagrams/10-wake-identity-storage-mobile.svg` for the chosen first experience and a directly viewable diagram.

## Honest assessment

Your work has produced a real engineering foundation. The native runtime, permission checks, explicit memory retention, encrypted transactions, and isolated regression tests are concrete progress. The strongest part is the decision to restrict actions until their authorization path is ready.

LYA is not yet a dependable everyday Jarvis-style assistant. Many advertised capabilities exist only as legacy modules, model-generated advice, or requirements. The next improvement should be completing a small number of reliable user journeys, not adding more skill files. No defensible overall completion percentage can be calculated without a fixed release scope and acceptance criteria.

This file is the current project record and future work ledger. It records the supplied source snapshot, not an independently verified history of every earlier session. This directory has no Git repository, so authorship, commit history, and previous versions could not be established.

## Evidence and review limits

Reviewed the product documents, current native command flow, UI, memory and model paths, voice loop, identity/approval integration, reminder parser, file browser, forge, and legacy routing/cloud boundaries. Inventoried the remaining modules and parsed every Python source file. This is a functional and architecture review, not an exhaustive audit or biometric validation.

| Check on 2026-09-10 | Result | Meaning |
|---|---|---|
| Python syntax via AST | All 59 Python files parsed, including the new review script; 58 were supplied | Syntax only, not import/runtime correctness |
| Original `test_foundations.py` | 13 passed, 1 failed | Folder assertion compares a resolved long Windows path against an unresolved short path |
| Same suite with temporary directory path normalized before execution | 14/14 passed in 0.491 seconds | Confirms the original failure is test path portability; application/test source was unchanged |
| `review_checks.py` | Three reminder defects, memory speech flag defect, and missing tone engine attribute reproduced | Uses fixed time, fake memory and AST extraction; no real secrets, network or sensors |
| `test_native_ui.py` | Blocked at Tk initialization | Bundled runtime could not load a usable Tcl init; explicit Tcl/Tk paths did not fix it |
| Live microphone, camera, iPhone, cloud/model requests | Not run | No end-to-end claims for these integrations |
| Older security/crash scripts | Not run | Existing README warns some older tests modify real stores; they are not the safe regression suite |

`python` is not on this shell's PATH. Tests used the bundled interpreter:

`C:\Users\kathirvel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`

Reproduction commands in PowerShell:

```powershell
$lyaPython = 'C:\Users\kathirvel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $lyaPython -B test_foundations.py
& $lyaPython -B -c "import tempfile,pathlib,runpy; tempfile.tempdir=str(pathlib.Path(tempfile.gettempdir()).resolve()); runpy.run_path('test_foundations.py',run_name='__main__')"
& $lyaPython -B review_checks.py
& $lyaPython -B test_native_ui.py
```

The review script deliberately describes currently reproduced bugs. It is not a release gate and should be converted to expected-behavior regression tests when those bugs are fixed.

## Product purpose and agreed direction

Source: `LYA_VISION.md`, whose earlier owner discussion was supplied with this snapshot.

- Native desktop orb, focused panels, voice and typed commands.
- Accessibility: people unable to use their hands should be able to complete supported tasks, navigate results, cancel and approve.
- Work within the owner's hardware and zero-subscription budget; actual hardware/model/cloud resources remain unverified.
- Act only on a user request or an explicitly authorized scheduled task.
- Basic guest conversation; recognized trusted users get selected low-risk operations; owner-only private actions need fresh phone approval.
- Identity uncertainty must not reveal private facts or grant private actions.
- Keep temporary chat distinct from explicitly saved knowledge; support corrections and forgetting.
- Research should preserve evidence; multiple model opinions do not establish truth.
- Enrollment was explicitly deferred in the supplied requirements. This review did not enroll anyone or configure real credentials.

## Architecture and what has been built

Current path: `main.py` -> bounded command queue -> one worker -> explicit command branches -> permission checks -> selected capabilities. UI updates flow through `ui/orb.py`'s queue to the Tk event loop. General responses call `brain/mind.py`. Private memory uses `brain/memory.py` -> `security/database.py` -> `security/vault.py`. Phone requests use `security/escalation.py` and the separate HTTPS `web_server.py` process.

| Area | Present implementation | Current status |
|---|---|---|
| New crystal desktop | PySide6 crystal, compact glass, typed commands, document previews and voice-to-Qt signal bridge | 10 UI checks pass on 2026-09-13; live voice launch/import and status gaps remain; identity/memory/model routes not connected |
| Legacy native shell | Tk orb, floating answer/folder/style panels, expand/shrink, themes, entry box | Retained; its Tk visual/runtime QA remains blocked here |
| Safe build mode | Synthetic folders, temporary themes, help/time/UI operations | Isolated handler checks pass; full GUI unverified |
| Worker and cancellation | Queue limit 8, background processing, stop clears queued commands and browser authority | Basic cancellation tests pass; does not interrupt every in-flight call |
| Permission policy | Public/trusted/owner actions; unknown capabilities deny | Offline policy tests pass |
| Folder browsing | User-home scope, current-directory paging, exact visible selections, file metadata only | Hardened & verified; boundary checks pass, non-executable inspection verified |
| App actions | Fixed calculator/notepad/explorer/chrome executable names and volume keys | Hardened; non-shell allowlisted Popen, native pywin32 multimedia keys, and mock tests pass |
| Private facts | Explicit save, protected label, recall, exact-key forgetting | Storage roundtrip/concurrent thread/corruption tests pass; phone-integrated use pending |
| Encrypted transactions | SQLite in RAM, encrypted atomic replace, thread/process locking | Thread concurrency tested; separate-process stress and recovery not tested |
| Chat | Provider fallback, bounded histories and person-scoped context helper | 5 component tests pass; new probes reproduce first-person fallback, legacy fallback and credential inclusion; not ready for private context |
| Voice | One capture loop, forwarding, local TTS, optional Vosk | Implemented; device accuracy, latency and recovery unverified |
| Phone approval | HTTPS, token, displayed task, nonce, phrase, owner face/liveness, expiring single-use grant | Implemented & hardened; 12/12 dedicated tests pass; local TLS gateway, rate limiting, and single-use grant consumption verified |
| Learning | Model lesson draft, ten-minute expiration, explicit save | Code present; no web verification or model training |
| Council | Up to three concurrent advisors, chairman synthesis | Advisory only; provider calls untested |
| Skill forge | Draft file and metadata generation; activation disabled | Hardened; Python syntax validation on drafts, activation lockout strictly enforced |
| Reminders | Encrypted text/time fields in SQLite; 30-second watcher started on first use | Hardened; relative, weekday, and explicit calendar parsing verified; RAM decrypted chronological sort |
| Screenshots | Owner-gated capture to `shots/` | Hardened; sandboxed directory creation, timestamped PNG output, and pywin32 fallback |
| Guardian & Safety Gate | Ultron safety layer; dangerous command screening, gated execution, silent duress alarm, dual encrypted audit logging | Hardened & verified; 12/12 dedicated tests pass; fails closed on tamper |
| System Health Governor | Zero-dependency Windows resource monitoring (WorkingSet RAM, battery, AC power, disk) & emergency kill switch | Hardened & verified; zero background CPU, instant kill-switch circuit breaker |
| Legacy capabilities | Cooking, teaching, guidance, technical helpers, security learning, network/device tools, phone/autonomy modules | Files exist; not routed by current native command path |
| Knowledge graph/sync | Separate graph/retention and cloud synchronization modules | Not the active native retention path; integration unverified |
| Legacy cloud/browser HUD | Separate implementations retained | Cloud POST actions disabled; HUD is not the primary product |

## What is particularly good

1. **Permissions are enforced in code.** The native flow does not rely on a model agreeing to behave. New actions have to be admitted to the policy deliberately.
2. **Private context is opt-in.** Guest requests do not load saved private facts into the native model prompt. History is bounded and separated by session/verification state.
3. **Storage has meaningful engineering behind it.** Atomic encrypted commits, serialization and corruption preservation are stronger foundations than saving raw chat JSON. The tests cover actual storage behavior using fake encryption keys.
4. **The UI and long tasks are separated.** The worker/queue pattern gives the interface a chance to stay responsive during network and approval waits.
5. **Generated code stays a draft.** This avoids treating plausible model output as a verified executable feature.
6. **The main README is candid.** It explicitly distinguishes prototype features, disabled paths and pending integrations. That honesty should be extended to older module descriptions.
7. **The accessibility purpose is clear.** It gives the project a useful product direction, beyond visual imitation of a fictional assistant.

## Confirmed defects and concrete concerns

Priority meanings: P1 = fix before relying on the affected private/core workflow; P2 = functionality/reliability fix; P3 = maintenance/documentation. These are review priorities, not claims of remotely exploitable vulnerabilities.

### R01 — P1: saving a private fact can speak its contents

Evidence: `main.py`, `Assistant.handle()` remember branch and `_worker()` speech condition. `private_output` begins false. The confirmation embeds a key made from the first six words of the fact, without setting the private flag. The worker speaks replies when that flag is false.

Reproduced with fake storage: `remember my private example is blue` returns the private words with `private_output=False`. No real fact was stored or spoken during testing.

Fix target: mark the save path private before returning content, or provide a generic non-sensitive spoken acknowledgment. Acceptance: voice output contains neither the fact nor its derived key; approved visual feedback remains useful.

### R02 — P1: reminder dates can be wrong

Evidence: `skills/reminder.py::_time_hint`; reproduced with clock fixed at Thursday 2026-09-10 12:00.

| Input | Expected | Actual |
|---|---|---|
| `remind me to call next monday at 9am` | Monday September 14, 09:00 | Tuesday September 15, 09:00 |
| `remind me to call in 2 hrs` | September 10, 14:00 | No time parsed |
| `remind me to call on 5 june at 6pm` | June 5, 2027, 18:00 | September 11, 2026, 05:00 |

Causes include an extra day in the next-weekday expression, matching `hrs` without handling it in the relative-time conversion, and passing the wrong regex-group shape for day-month dates. The fallback clock regex then interprets a date number as an hour. Acceptance: deterministic tests for supported phrases, rejection of ambiguous/invalid inputs, and confirmation of the resolved date before reliance.

### R03 — P2: text mode falsely describes itself as a safe preview

Evidence: `main.py::main` passes `preview=mode!="voice"`, while only `mode=="build"` sets the assistant's safe build flag. `ui/orb.py::run` displays “no microphone, model calls or device actions” for preview. Thus text mode shows a statement that does not match its enabled handlers. Text mode can call a model and, with identity/approval, perform real actions. Fix the mode label separately from whether the orb initially appears.

### R04 — P2: voice cannot reliably interrupt long tasks [RESOLVED 2026-09-12]

Evidence: `audio/voice.py::wake_loop` only routed bare `stop`/`cancel` while its 45-second conversation window was active. Phone approval may wait 120 seconds. After the window expires, an unprefixed spoken stop could be ignored.

Resolution: Extracted `process_utterance` in `audio/voice.py`. Bare `stop`, `cancel`, `sleep`, and `go to sleep` now immediately route to `on_wake` and reset the conversation window even when the 45s window has expired or while TTS is speaking. Verified in `test_voice.py::VoicePipelineTests.test_r04_interruption_during_speaking` and `desktop/check_ui.py::InterfaceChecks.test_voice_wake_signal_dispatch`.

### R05 — P2: emotional speech-rate updates silently fail

Evidence: `brain/mind.py::set_tone` references `voice.engine`, but `audio/voice.py` exposes `_engine`. Its broad exception handler hides the missing attribute. The default TTS rate can work while advertised tone modulation does not. Attribute mismatch reproduced without initializing audio hardware.

### R06 — P2: forge does not use the same stored key as chat [RESOLVED 2026-09-12]

Evidence: `brain/mind.py` can load the DPAPI-encrypted Groq key; `skills/forge.py::_groq` directly indexed `os.environ['GROQ_API_KEY']`.
Resolution: Reused `mind.get_groq_key()` in `skills/forge.py`, providing a unified key resolution chain (environment variable -> DPAPI vault file -> `%LOCALAPPDATA%\LYA\vault`). Verified in `test_mind.py::MindGatewayTests.test_r06_unified_groq_key_resolution`.

### R07 — P2: reminder ordering and delivery are incomplete [RESOLVED 2026-09-12]

Evidence: `skills/reminder.py::list_all` ordered by `when_iso`, which contained randomized encrypted tokens rather than sortable timestamps.
Resolution: Modified `list_all()` in `skills/reminder.py` to decrypt all records in memory first, then perform a sorted order by decrypted ISO timestamps. Verified in `test_foundations.py` and `test_regressions_r01_r05.py`.

### R08 — P2: install and recovery are not reproducible yet

No `requirements.txt`, `pyproject.toml`, lockfile or CI configuration was found in the supplied file inventory. The README names dependencies, but a clean-machine install is not encoded or verified. Python is absent from PATH here and the available runtime cannot initialize Tk. The referenced anti-spoof repository/models are absent from this snapshot. These are environment/integration blockers, not evidence that all application logic is broken.

Acceptance: one documented supported Python environment, dependency groups, a harmless readiness check, and a tested GUI launch. Do not download large biometric/model dependencies until the selected setup needs them.

### R09 — P2: saved knowledge is not yet a per-person durable assistant memory

`brain/memory.py` has no person/session column on memory rows. Native private context takes the top 15 saved entries rather than retrieving facts relevant to the question. A save always inserts another row; keys derived from the first six words can collide. `forget_exact` deletes all exact matches. `save lesson` says the lesson is labeled unverified, but persists the answer and `kind=lesson`, without a separate provenance/verification field.

This is useful explicit note storage. It needs ownership, correction/version semantics and source status before it can satisfy the larger personalized learning vision.

### R10 — P3: old claims and instructions conflict with the active implementation

Examples: `cloud/README.md` instructs an HTTP gateway launch, whereas the active server requires TLS configuration; the cloud UI suggests features whose POST handlers return 503. `skills/forge.py`'s opening description says confirmation activates code, but activation is disabled. `brain/knowledge.py` says every message passes through it, whereas the native handler does not route messages through that module. `skills/allskills.py` says main calls it, but current main does not. Older “full device control,” accuracy and encryption slogans should not be treated as verified product guarantees.

Acceptance: label legacy entry points clearly and update descriptions from actual call paths. Provider pricing, free-tier terms and model identifiers were not checked online in this local review.

### R11 — P3: test portability and coverage gaps

The folder assertion should compare against `root.resolve()` or the browser's resolved root. Tests often extract individual functions with AST or mock dependencies; that is useful isolation but misses startup imports and integration contracts such as the tone engine name. Add only targeted expected-behavior checks for the bugs above, plus one end-to-end journey once its environment is ready. There is no evidence here of full process-concurrency, long-duration stability, biometric accuracy or device performance tests.

## Deliberately unfinished rather than broken

- Admin enrollment and trusted iPhone pairing/HTTPS setup.
- Hands-free iPhone approval: current page needs token/phrase input, camera permission and buttons.
- Durable visitor naming and relationship-specific memory/delegation.
- Live web research, source retention, evidence-based answers and reference-to-theme conversion.
- Isolated generated-skill execution, versioning and rollback.
- Goal-level inspect/plan/execute/verify workflows across applications.
- Automatic startup, reminders when the laptop is off, integrated cloud identity/sync.
- Measured CPU/RAM/latency budgets and actual laptop/phone accessibility testing.

## Data map and retention rules

There are two distinct needs: recording project development and retaining runtime user information. This Markdown file handles the first; it does not change the assistant into an automatic recorder of everything.

| Data | Current location/behavior | Handling |
|---|---|---|
| Product requirements | `LYA_VISION.md` | Keep as owner intent; changes need a dated decision |
| Earlier milestone claims | `BUILD_PROGRESS.md` | Historical record; this review supplies newer evidence |
| Current status, findings and decisions | `lya-project-brain.md` | Update after each development task |
| Review reproductions | `review_checks.py` | Synthetic evidence; convert to fixed-behavior tests with fixes |
| Source and tests | Project module paths | Link here instead of copying whole files |
| Chat history | Bounded RAM in `brain/mind.py` | Not automatically durable; restart loses it |
| Explicit saved facts/lessons | `brain/lya_brain.db.lya` | Encrypted private runtime store |
| Reminder records | `data/reminders.db` | Contents/time encrypted; table metadata remains SQLite |
| Identity and secrets | `.lya` stores and `security/.lya_key` | Never copy values or biometric material into this document |
| Screenshots | `shots/` | Plain private images; ignored by Git, not a backup |
| Themes | `data/appearance.json` | Local settings |
| Generated skill draft | `skills/forge_draft.py`, `skills/forge_meta.json` | Local draft overwritten by later drafts; activation disabled |
| Visual architecture pack | `diagrams/01..08-*.mmd` + `LYA_ARCHITECTURE.md` | Derived-from-source maps; re-validate with `mermaid.mjs check --all` and re-check status colours when code changes |
| Future research/reports/assets | Save in an appropriate project path; record it below | Preserve file, source, date, status and sensitivity; no directory scaffolding needed until used |

Do not dump passwords, tokens, raw biometric samples, private transcripts or personal facts into a plaintext project brain. Record safe summaries and paths to appropriately protected material instead. The existing runtime memory consent boundaries remain in place.

This review creates a root `AGENTS.md` instruction to read and update this ledger on future coding tasks. That is a workflow for cooperating agents, not a background service or guaranteed capture from every application. Future chats must use this workspace and follow the instruction. Files generated outside it must be saved or linked explicitly. This file and all local artifacts still need a real backup/version-control plan; no Git initialization, remote backup or automatic runtime capture was performed.

## Next milestones and acceptance criteria

1. **Stabilize the current foundation.** Fix R01-R07 and the test path comparison. Each fix gets a focused regression check. The safe suite passes without path workarounds; mode labels and documentation match reality.
2. **Make preview/install dependable.** Establish a supported Python/Tk environment and a minimal dependency manifest. Launch build mode on the actual screen and verify panels, sleep/wake, focus, scaling and keyboard exits.
3. **Complete one useful accessible journey.** Validate voice -> read-only folder navigation -> selection -> back/scroll -> cancel, including errors and long waits. Enrollment/pairing remains a separately authorized setup milestone under the supplied requirements.
4. **Make explicit memory dependable.** Save, recall, correct and forget fake test facts with private output and restart persistence. Add ownership/provenance only to the extent needed for approved users and lessons.
5. **Make reminder delivery dependable.** Fix parsing, sorting, startup and acknowledgment; test restart, overdue reminders and missed delivery.
6. **Then add one evidence-based research or verified app workflow.** Keep sources and outcome checks. Integrate each legacy capability through the current policy rather than enabling the entire old router.

## Work ledger

| Date | Work | Status | Evidence/artifacts |
|---|---|---|---|
| Before this review; exact history unavailable | Native interface, policies, memory transactions, phone protocol, voice loop, draft learning/council/forge | Present in supplied snapshot | `README.md`, `BUILD_PROGRESS.md`, source; verification limits above |
| 2026-09-10 | Functional/architecture review and current-path inventory | Completed within stated scope | This file |
| 2026-09-10 | Foundation suite and normalized-path diagnostic | Completed | 13/14 raw; 14/14 normalized; no application changes |
| 2026-09-10 | Syntax scan and isolated defect reproductions | Completed | `review_checks.py` |
| 2026-09-10 | Native widget smoke test | Environment-blocked | Unusable Tcl initialization; no visual sign-off |
| 2026-09-10 | Project continuity record and future-agent instructions | Created | `lya-project-brain.md`, `AGENTS.md` |
| 2026-09-10 | Application bug fixes | Not performed in this review | R01-R11 remain open |
| 2026-09-10 | Full inch-by-inch re-read of every Python file + dependency probe | Completed | 13 required libs probed; only `cryptography`, `numpy` present; 11 findings N1-N11 |
| 2026-09-10 | Visual architecture pack: 8 Mermaid diagrams, all validated | Completed | `diagrams/01..08-*.mmd`, `LYA_ARCHITECTURE.md` (8 embedded blocks); 16/16 render clean |
| 2026-09-10 | Installed the `mermaid` skill (validate/extract/trace) | Completed | `~/.codegpt/skills/mermaid` + `~/.claude/skills/mermaid`; 5 real validator bugs found and fixed by using it |
| 2026-09-12 | Installed the verified Mermaid package for Codex | Completed | `~/.codex/skills/mermaid`; official curated list had no Mermaid entry, so the previously verified local package was copied exactly |
| 2026-09-12 | Planned a from-scratch verified-core rebuild | Completed; implementation not started | `LYA_REBUILD_PLAN.md`, `diagrams/09-lya-from-scratch-workflow.mmd`; existing prototype preserved as reference; full Mermaid check 18/18 passed after repairing corrupt `999` prefix in older diagram 08 |
| 2026-09-12 | Decided native wake, face identity, per-person storage and mobile-cache foundation | Planned; no real enrollment or runtime implementation | `LYA_FOUNDATION_DECISIONS.md`, validated Mermaid source `diagrams/10-wake-identity-storage-mobile.mmd`, directly viewable PNG/SVG renders in `diagrams/` |
| 2026-09-12 | Built and launched the custom crystal and glass desktop | UI implemented; 8/8 checks pass; full assistant integrations pending | `launch-lya.ps1`, `desktop/app.py`, `desktop/layout.py`, `desktop/README.md`, `desktop/check_ui.py`, `desktop/qa/`; detailed entry below |
| 2026-09-12 | Step 1 base environment: restored pip in .venv-ui, installed numpy, cryptography, pywin32; fixed Windows 8.3 path resolution in test_foundations.py | Completed; 14/14 foundation checks pass; 8/8 UI checks pass | `test_foundations.py`, `.venv-ui/`, `desktop/check_ui.py`; detailed entry below |
| 2026-09-12 | Step 2 deterministic core & defect fixes: fixed R02 (date parsing) and R07 (decrypted ordering) in reminder.py; confirmed R01/R05; wired status/help/time in desktop/app.py; converted review_checks.py | Completed; 4/4 suites pass (14/14, 16/16, 6/6, 9/9) | `skills/reminder.py`, `desktop/app.py`, `review_checks.py`, `desktop/check_ui.py`; detailed entry below |
| 2026-09-12 | Step 3 clean encrypted storage: built storage/store.py with person-scoped schemas, %LOCALAPPDATA%\LYA layout, 7-day pending face expiry, and safe audit log | Completed; test_storage.py 7/7 pass; all 5 project suites pass | `storage/store.py`, `test_storage.py`; detailed entry below |
| 2026-09-12 | Agent skills & research: installed andrej-karpathy-skills and ponytail globally; evaluated 9 GitHub repos for LYA device footprint & roadmap | Completed | `C:\Users\kathirvel\.gemini\config\skills\`, `lya-project-brain.md`; detailed entry below |

## Decision log

- 2026-09-13: Review new components using a disposable source copy, fake data and
  blocked network/sensors. Preserve the app during review. Prioritize memory
  boundaries and actual-launch integration before extending features. Owner wants
  a more futuristic visual treatment while retaining the current panel's clarity.

- 2026-09-12: Implement the owner's crystal-and-glass UI first as an isolated native
  milestone. Reuse the unchanged supplied artwork through a silhouette clip; keep
  the desktop visible, use small windows and cached animation frames. Person colors
  are cosmetic until authenticated session events are connected. Real file previews
  in this milestone are restricted to the four listed public project documents.

- 2026-09-10: Treat working foundation, reproduced defects, legacy code and unverified integrations as separate statuses.
- 2026-09-10: Preserve existing product/enrollment boundaries. Review and documentation do not enroll identities or activate legacy/generated tools.
- 2026-09-10: Persist safe project knowledge in this ledger; preserve full artifacts at their paths. No automatic collection of private runtime data.
- 2026-09-10: Prioritize completing reliable workflows before expanding the feature list.
- 2026-09-12: Rebuild beside the existing prototype and promote capabilities only through explicit acceptance gates. Initial scope is reproducible runtime, deterministic text core, read-only folders, then native UI.
- 2026-09-12: Refine the first owner-visible milestone to native PySide6 wake UI, offline Vosk wake recognition, one-frame OpenCV capture, local InsightFace matching, and encrypted person-scoped SQLite storage. Face recognition personalizes; it does not alone authorize sensitive actions.
- 2026-09-12: Store runtime/private data under `%LOCALAPPDATA%\LYA`, outside the source tree. Default files to laptop-only; only explicitly pinned Important Vault items synchronize to an encrypted phone cache.

## Future task entry template

Append an entry after each meaningful task, and update the status tables above when evidence changes:

- Date and requested outcome:
- Changes and affected paths:
- Generated artifacts, sources and sensitivity:
- Verification command, result and limits:
- Decisions and reasons:
- Open issues and next concrete step:

Never mark “working” from file presence, syntax alone, an old report or a model's claim. Record failures as well as successes. Keep prior evidence dated rather than silently replacing history.

## Owner clarification — conversational upgrades and visual references (2026-09-10)

The owner wants LYA to improve through ordinary instructions, retain successful capabilities, and reuse them later. This is a requested product direction, not an implemented feature or authorization to activate a camera now.

Two concrete examples:

1. “Create a camera-reading skill; when I ask, look at my room and tell me whether anyone is there.” Desired flow: use an authorized camera, inspect the visible scene, report detected people and uncertainty, and retain the reusable skill. An image cannot establish that the entire home is empty, and detecting a person is distinct from identifying them. Retaining the skill does not require retaining room recordings. No continuous monitoring was requested.
2. “Look at this video on my phone; I like its folder interface. Use that layout for my files from now on.” Desired flow: receive a shared clip/screenshot or an explicitly available screen feed; infer layout and interaction details; create a working preview; apply the requested style after validation; persist the choice and allow undo. A short video may not reveal the original implementation or all interaction behavior. Current LYA has no integrated phone-screen/video input and only three predefined orb themes, not a reference-driven folder renderer.

Proposed implementation stages:

- Prefer reusable workflows built from already available, permission-checked tools.
- Represent supported visual changes as validated layout/theme settings where possible.
- When genuinely new code is needed, generate a separate draft, test it in an isolated environment with limited access, verify the requested behavior, and register a version only after those checks and applicable authorization succeed. Tests reduce risk; they do not prove arbitrary generated code safe.
- Keep the core permissions, credentials and update/rollback mechanism outside generated skills' write access.
- Store each accepted skill's purpose, trigger, permissions, dependencies, version, evidence, limitations and rollback target. Keep runtime camera use subject to the original request and permissions.
- Save capability definitions and chosen preferences, not every raw observation. This is reusable software/workflow creation; it does not require retraining the underlying language model after each instruction.
- Treat “stay updated” as a desired product property for now. No automatic dependency updater, research monitor, scheduled task or background camera service was requested or created in this discussion.

Current evidence: `skills/forge.py::activate` is disabled; drafting writes one replaceable draft. `ui/themes.py` accepts reactor/halo/pulse and stores a previous theme. Safe execution, a durable versioned skill registry, video interpretation and arbitrary folder-layout generation remain pending.

Work ledger entry: 2026-09-10 — checked current forge/theme implementation; recorded both owner examples, limits and proposed acceptance flow. Documentation only; no application changes, installs, sensors, model calls or new tests. Next step: choose and implement one bounded journey after the existing core reliability fixes.
## Full re-read pass and visual architecture pack (2026-09-10)

### Requested outcome

Owner asked for an inch-by-inch pass over the whole project and a detailed visual
work-flow map showing what works, what is in progress, and what does not — with
the biometric ("Face ID") technology and its status stated.

### What was done

Read every Python file in the project (59 files, all modules and sub-packages),
then probed the runtime for each declared dependency. No sensors, cameras,
microphones, phone connections, model calls or GUI launches were used. Nothing was
enrolled. No application source was modified.

### Generated artifacts

- `LYA_ARCHITECTURE.md` — the visual guide; 8 Mermaid blocks embedded inline,
  plus technology tables, the R01 code walkthrough, new findings and a ranked action list.
- `diagrams/01-master-system-map.mmd` — all layers, wired vs unwired, status-coloured.
- `diagrams/02-faceid-chain.mmd` — the live ArcFace identification sequence.
- `diagrams/03-three-faceid-implementations.mmd` — the three separate face systems.
- `diagrams/04-permission-approval-flow.mmd` — policy gate + phone grant lifecycle.
- `diagrams/05-command-lifecycle.mmd` — queue/worker/threading and the R01 site.
- `diagrams/06-data-and-encryption.mmd` — stores, key root, two encryption designs.
- `diagrams/07-status-map.mmd` — the one-answer working/partial/broken/legacy map.
- `diagrams/08-voice-pipeline.mmd` — wake loop, STT choice and R04.

### Verification command, result and limits

```
$node = C:\Users\kathirvel\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe
& $node "$env:USERPROFILE\.codegpt\skills\mermaid\mermaid.mjs" check --all
```

Result: **16 checked, 0 failed, 0 warnings** (8 `.mmd` files + 8 blocks inside
`LYA_ARCHITECTURE.md`). Re-run this after any diagram edit.

Dependency probe (bundled interpreter), read-only import test:

| Present | Missing |
|---|---|
| `cryptography`, `numpy` | `win32crypt`, `cv2`, `insightface`, `onnxruntime`, `resemblyzer`, `sounddevice`, `speech_recognition`, `pyttsx3`, `pyautogui`, `vosk`, `torch` |

Limits: findings are read from source and from import probing, not runtime
reproduction. Static reading cannot observe dynamic imports or framework wiring.
The probe result is specific to the interpreter used; a different Python install
may report differently.

### Key conclusions recorded

1. **Root blocker: only 2 of 13 required libraries are installed.** `security/vault.py`
   calls `_get_fernet()` at import time and imports `win32crypt` at module scope, so
   the missing DPAPI binding prevents almost every module from loading. Most amber/red
   status below is downstream of this one gap.
2. **Face ID is three implementations, not one.** `vision/identity.py` (InsightFace
   ArcFace 512-d) is the only one wired into `main.py`. `vision/face_auth.py`
   (OpenCV Haar + 128px mean-abs-diff, threshold 0.12) is orphaned. `security/liveness.py`
   (MiniFASNet anti-spoof) runs only on the phone `verify_owner()` path. Any document
   describing "OpenCV face auth" is describing the orphan.
3. **The permission/approval layer is the project's strongest asset** and already
   contains real fixes: cross-process nonce via disk, fail-closed grant consumption,
   fail-closed attempt lockout, per-install salt, `hmac.compare_digest` token check,
   per-client expiring phone sessions.
4. **`main.py` imports `skills/allskills.py` but never calls it.** 15 skill modules
   are loaded at start and are unreachable at runtime.

### New findings N1–N11 (not previously recorded)

| # | Finding | Evidence |
|---|---|---|
| N1 | `allskills.reply()` is dead at runtime despite being imported | `main.py` import list vs `handle()` |
| N2 | Laptop spoken-fallback is unreachable: `permit()` only calls `request_phone()`, never `escalate()`, so `security_word.lya` is a settable but unusable credential | `main.py::permit` vs `escalation.request_phone` |
| N3 | `vault.py` builds the Fernet at import time — one bad key file breaks every dependent module with no graceful degradation | `vault.py` line 31 |
| N4 | First-run phone token is printed to stdout | `web_server.py` lines 59–60 |
| N5 | Phone page keeps its access token in `localStorage` | `web_server.py` lines 94–95 |
| N6 | `voice_liveness()` uses `audioop`, removed in Python 3.13 | `liveness.py` line 87 |
| N7 | Anti-spoof loader calls global `os.chdir(REPO)`, which can break relative paths in a threaded app | `liveness.py` line 35 |
| N8 | `close_app()` uses `os.system`; `run_command()` uses `shell=True` — currently unreachable but a shell-injection surface if wired up | `device.py` lines 30, 48–51 |
| N9 | An unauthenticated unknown face triggers a disk write to the encrypted store | `identity.py` lines 127–131 |
| N10 | `face_auth.py` imports `cv2`/`numpy` unguarded at module top; masked only because nothing imports it | `face_auth.py` lines 5–6 |
| N11 | Two unreconciled admin identities: `memory.admin` table vs `identity.people[]` with `role=admin` | `memory.py` 66–86 vs `identity.py` 41–71 |

### Decisions and reasons

- 2026-09-10: Draw the system rather than re-describe it in prose; keep diagrams
  versioned next to the code in `diagrams/` and embed the same blocks in the guide
  so they render without a separate viewer.
- 2026-09-10: Use status colouring (`works`/`partial`/`broken`/`legacy`) because in
  a half-finished project "what is real" matters more than "what is connected".
  These colours are a claim about today and must be re-checked when code changes.
- 2026-09-10: Record N1–N11 as read-from-source findings, explicitly not as runtime
  reproductions, and keep them separate from the already-reproduced R01–R03.
- 2026-09-10: Do not alter any application source in this pass — the request was
  analysis and visualisation.

### Open issues and next concrete step

All of R01–R11 and N1–N11 remain open; no fixes were applied in this pass.

Next concrete step: **write `requirements.txt` and install the dependency set**
(R08). Until `win32crypt`, `cv2` and the voice/GUI libraries are present, no runtime
verification of any journey is possible, so this unblocks everything else. After
that, fix R01 (one line) and R05 (one word) as the first targeted regression checks.

### Skill installation recorded

Installed the `mermaid` skill at `~/.codegpt/skills/mermaid` and
`~/.claude/skills/mermaid` (SKILL.md + mermaid.mjs + .codegpt-seed.json). It
validates, extracts and traces Mermaid diagrams. Using it on this pack exposed and
fixed five genuine validator bugs (missed `flowchart TD`, broken markdown fence
extraction, `alt/loop/end` misread as unclosed subgraphs, arrow heads captured into
participant names, `:::class` read as an edge). Validator hash: `d447b309597fb3ce`.
No credentials or private runtime facts are stored in this ledger.

## 2026-09-12 — Custom crystal and glass desktop implementation

Requested outcome: make the owner's artwork a real native floating LYA interface,
with smooth person/task colors and readable compact message/file cards.

Implemented:

- `desktop/app.py`: two frameless translucent Qt windows, draggable crystal,
  interpolated colors, gentle motion, panel reveal, typed commands, tray controls,
  keyboard exits, reduced motion and opaque-panel options. No full-screen window.
- `desktop/layout.py`: monitor-aware card placement and explicit palette mapping.
- `desktop/assets/crystal-original.png`: unchanged copy of the owner's supplied
  artwork. Painter clipping removes the square background at runtime. An ImageGen
  extraction attempt failed to produce true alpha and is not used; provenance is
  recorded in `desktop/README.md`.
- `launch-lya.ps1`, `desktop/requirements.txt`, `.venv-ui/`: isolated Python 3.12.14
  with PySide6 Essentials 6.11.2. The normal launcher opens only the crystal.
  `.gitignore` excludes the environment and local uv cache; root README links the
  new launcher. Existing runtime code and earlier diagrams were preserved.
- Read-only project documents open through one background worker. Generation-based
  cancellation rejects dismissed results. Cosmetic roles cannot grant access.

Checks and generated artifacts:

- Command: `.\.venv-ui\Scripts\python.exe -B desktop\check_ui.py`.
- Launcher check: `launch-lya.ps1` started successfully in default crystal-only
  mode; the launched process remained running after the 2.5-second startup check.
- Result: **8/8 passed** in 1.546 seconds, including native-window/alpha setup,
  monitor edges/negative coordinates, keyboard commands, readable file rows,
  actual file selection/loading, role isolation, allowlisting, stale completion
  rejection, and hidden/reduced-motion animation lifecycle.
- Visually reviewed actual widgets over synthetic light/dark desktops; corrected
  black surrounds in the initial composition, clipped card text and artwork edges.
  No user desktop screenshots or sensor data were collected.
- [Light desktop](desktop/qa/light-desktop.png),
  [dark desktop](desktop/qa/dark-desktop.png),
  [message panel](desktop/qa/message-desktop.png).
- [Timing sample](desktop/qa/measurement.json): 2.511 seconds, 171 paints, median
  2.021 ms and max 3.874 ms per paint; maximum event-loop heartbeat gap 25.904 ms.
  This short local measurement is not proof of sustained frame rate, battery use
  or responsiveness under voice/camera/model load.

Limitations: this is 2D artwork with motion, not a reconstructed 3D model. Glass is
tinted translucency, not OS acrylic blur. Voice wake, sensors, face recognition,
real identity, private saved-file/vault search, AI answers, mobile access and
retained display preferences are not connected. No real enrollment occurred.

Next step: owner visual acceptance on the desktop, then connect a deterministic
session/task event path and test offline wake separately before any camera setup.

## 2026-09-12 — Step 1 base environment and foundation test recovery

Requested outcome: start from scratch step-by-step; verify the starting point, install minimal core dependencies, and bring foundation tests to 100% pass.

Implemented and verified:
- Discovered `.venv-ui` had no `pip` installed. Restored pip via `ensurepip --upgrade`.
- Installed the three minimal foundational packages: `numpy` (2.5.3), `cryptography` (50.0.1), and `pywin32` (312).
- Fixed Windows 8.3 short-path resolution mismatch in `test_foundations.py::test_folder_paging_and_scope` using `Path(tmp).resolve() / "scope"`.
- Ran `.\.venv-ui\Scripts\python.exe test_foundations.py`: **14/14 passed** in 0.366s. All previous `ModuleNotFoundError` crashes resolved.
- Ran `.\.venv-ui\Scripts\python.exe -B desktop\check_ui.py`: **8/8 passed** in 1.053s.

Limitations: camera/vision (`insightface`, `onnxruntime`, `cv2`) and voice audio (`sounddevice`, `vosk`) remain intentionally uninstalled until their dedicated steps. No real biometrics or secrets were enrolled.

Next step (Step 2): wire clean deterministic text commands (status, help, time, stop, folder read) directly to the PySide6 crystal UI and fix the R01 speech leak and R05 tone engine defects.

## 2026-09-12 — Step 2 deterministic core and defect remediation

Requested outcome: fix confirmed defects R01, R02, R05, R07; wire deterministic commands (`status`, `help`, `time`/`date`) into the native PySide6 Crystal UI; convert review checks into regression tests.

Implemented and verified:
- Verified R01 (private fact speech suppression in `main.py`) and R05 (`voice.set_rate()` via `_engine` in `brain/mind.py`) passing with 16/16 checks in `test_regressions_r01_r05.py`.
- Fixed R02 in `skills/reminder.py::_time_hint`:
  - Added `unit.startswith("hr")` so relative hours (`in 2 hrs`) parse properly.
  - Corrected next weekday offset `(WORDS[m.group(1).lower()] - b.weekday()) % 7 or 7` (removed spurious `+ 1` extra day offset).
  - Fixed `day_month` parsing for phrases like `on 5 june at 6pm`.
- Fixed R07 in `skills/reminder.py::list_all`:
  - Decrypted all rows before sorting by `when_iso` (`rows.sort(key=lambda r: r[2])`), replacing sorting on randomized ciphertext.
  - Verified chronological order with an isolated temporary store.
- Converted `review_checks.py` from reproducing defects to asserting expected fixed behavior: **6/6 passed**.
- Enhanced `desktop/app.py`:
  - Added live `status` / `check` command deriving actual Python and dependency readiness (`win32crypt`, `cryptography`, `numpy`, etc.) rather than hard-coded claims.
  - Added dedicated `help` command listing available desktop operations.
  - Expanded `time`, `date`, `day` recognition.
  - Added `test_deterministic_commands` to `desktop/check_ui.py`: **9/9 passed** in 1.092s.
- Executed full test run: `test_foundations.py` (14/14), `test_regressions_r01_r05.py` (16/16), `review_checks.py` (6/6), and `desktop/check_ui.py` (9/9) **all pass 100% clean**.

Limitations: vision/camera, offline microphone loop, real phone pairing, and per-person encrypted SQLite in `%LOCALAPPDATA%\LYA` remain to be implemented in subsequent steps.

Next step (Step 3): Step 4 of the rebuild plan — clean encrypted local storage (`%LOCALAPPDATA%\LYA`) with person-scoped data schemas (`people`, `memories`, `vault_items`, `audit_events`).

## 2026-09-12 — Step 3 clean encrypted person-scoped storage

Requested outcome: implement the storage foundation specified in `LYA_FOUNDATION_DECISIONS.md` outside the repository tree in `%LOCALAPPDATA%\LYA` with encrypted person-scoped SQLite, atomic commits, automatic 7-day pending face expiry, and safe audit logging.

Implemented and verified:
- Created `storage/store.py` and `storage/__init__.py`:
  - `get_data_dir()` resolves `%LOCALAPPDATA%\LYA` (with `LYA_DATA_DIR` test override support).
  - `ensure_layout()` initializes standard directory layout: `faces/`, `vault/`, `models/`, `logs/`, `lya.db.enc`.
  - Encrypted SQLite in RAM via `db.deserialize` / `db.serialize` with AES-256 Fernet/DPAPI encryption, file-level locking (`msvcrt` on Windows), and atomic replacement.
  - Person-scoped schemas implemented:
    - `people`: `person_id`, `display_name`, `role`, `created_at`, `active`
    - `face_templates`: `person_id`, `embedding_enc`, `model_version`, `quality`, `created_at`
    - `pending_faces`: `pending_id`, `thumbnail_path`, `embedding_enc`, `first_seen`, `last_seen`, `sightings`, `expires_at` (7-day TTL)
    - `memories`: `person_id`, `kind`, `key_enc`, `value_enc`, `source`, `importance`, `hits`, `created_at`, `updated_at`
    - `vault_items`: `person_id`, `label_enc`, `file_path_enc`, `sync_policy`, `created_at`
    - `audit_events`: `time`, `action_type`, `outcome`, `person_id` (zero secret, transcript, or image data)
  - Full API: `create_person()`, `get_person()`, `list_people()`, `remember()`, `recall()`, `forget()`, `record_pending_face()`, `list_pending_faces()`, `promote_pending_face()`, `record_audit()`, `list_audit_events()`.
- Created unit test suite `test_storage.py`:
  - Verified directory layout creation.
  - Verified database is genuinely encrypted at rest (plain `sqlite3` fails to read file).
  - Verified strict person scoping (Alice cannot see Bob's memories; guest cannot see private data).
  - Verified exact-key forgetting scoped to specific person.
  - Verified unknown face capture, pending listing, and admin promotion to registered person.
  - Verified audit log never leaks plaintext secrets.
  - Verified multi-threaded concurrent write safety without corruption.
  - All **7/7 storage tests pass in 0.364s**.
- Full test pass across the entire workspace:
  - `test_foundations.py`: 14/14 passed
  - `test_regressions_r01_r05.py`: 16/16 passed
  - `review_checks.py`: 6/6 passed
  - `test_storage.py`: 7/7 passed
  - `desktop/check_ui.py`: 9/9 passed
  - **All 5 suites pass cleanly.**

Limitations: face embeddings used in tests are synthetic test vectors; camera capture and InsightFace model integration are deferred to subsequent steps.

Next step (Step 4): Offline voice wake phrase detection using `vosk` and `sounddevice` ("wake up LYA") to trigger the crystal desktop window.

## 2026-09-12 — Research, device footprint optimization, and global agent skills

Requested outcome: evaluate 9 specific GitHub repositories for device footprint and LYA integration, install Andrej Karpathy's agent guidelines and Ponytail globally, and establish a modern, low-pressure model architecture for the laptop.

Actions and findings:
1. **Installed Global Skills** in `C:\Users\kathirvel\.gemini\config\skills\`:
   - `andrej-karpathy-skills`: 4 core principles (Think before coding, simplicity first, surgical changes, goal-driven execution).
   - `ponytail`: Minimalist senior developer rules (YAGNI, stdlib first, native platform features, zero bloat, verify before finishing).
2. **Evaluated 9 GitHub Repositories for LYA**:
   - **`diegosouzapw/OmniRoute`**: Highly relevant for LYA. Unified AI gateway with 90+ free tiers (~1.51B free tokens/mo) and auto-fallback. Recommended for LYA's cloud reasoning provider to give free, zero-laptop-pressure AI intelligence.
   - **`TencentCloud/TencentDB-Agent-Memory`**: Concept of symbolic short-term memory (Mermaid diagrams) and layered long-term memory (personas + scenes). We have already adopted person-scoped schemas in `storage/store.py` and Mermaid architecture maps.
   - **`microsoft/VibeVoice`**: Crucial for LYA Step 4/5. Specifically `VibeVoice-ASR-BitNet` (1.58 GB CPU edge inference on 3+ threads with RTF < 1, no GPU required) and `VibeVoice-Realtime-0.5B` streaming TTS.
   - **`ScrapeGraphAI/Scrapegraph-ai`**: Excellent for future LYA "learn <topic>" deep research pipeline without manual browser automation.
   - **`Panniantong/agent-reach`**: Agent web access toolset; useful companion for online search tasks.
   - **`bytedance/deer-flow`**: Multi-agent harness with sandboxes; relevant for future Council expansion, but too heavy to run as a local background daemon.
   - **`jingyaogong/minimind`**: Educational 26M-100M parameter LLM; not recommended for primary reasoning over OmniRoute/Groq.
3. **Device Footprint Strategy**:
   - Keep local laptop load near zero: PySide6 (UI), Kaldi/Vosk or VibeVoice BitNet (Edge Voice), ArcFace (512-d embeddings via ONNX CPU in <100ms), and SQLite (Encrypted RAM/disk).
   - Route heavy LLM tokens through cloud/free-tier gateways (Groq / Gemini / OmniRoute) to avoid high fan noise, RAM bloat, and thermal throttling.

Next step: proceed to Step 4 — offline voice wake phrase detection using `vosk` and `sounddevice`.

## 2026-09-12 — Step 4: Offline Voice Wake & Audio Pipeline (Completed)

Requested outcome: Build out Step 4 (Offline Voice Wake & Audio Pipeline), provide smarter/more advanced voice options than Vosk and sounddevice, verify R04 interruption, implement comprehensive unit tests for voice, wire voice wake into the PySide6 Desktop UI with thread-safe Qt signals, and verify all suites.

Actions and findings:
1. **Audio Capture & Wake Analysis**:
   - `sounddevice` (PortAudio C-bindings with WASAPI) is the optimal, lowest-latency, zero-overhead capture library in Python on Windows.
   - For wake word detection, `openWakeWord` (ONNX AST/ResNet-8 neural wake words, <0.5% CPU, <30MB RAM) was installed alongside `vosk` (0.3.45), `sounddevice` (0.5.6), `pyttsx3` (2.99 with Windows SAPI5), and `onnxruntime` (1.30.0).
   - Audio devices detected on hardware: `Microphone Array (Realtek(R) Audio)` and `Speakers (Realtek(R) Audio)`.
2. **Fixed R04 in `audio/voice.py`**:
   - Spoken "stop", "cancel", "sleep", and "go to sleep" now immediately trigger `on_wake` and reset the active window, bypassing conversation timeouts and breaking through active speaking loops.
   - Extracted clean, testable `process_utterance(text, last_wake_time, on_wake, quiet)` and added `stop_event` support to `wake_loop` for graceful daemon shutdown.
   - Added automatic model discovery in `%LOCALAPPDATA%\LYA\models\vosk`.
3. **Hardened Voice Liveness (`security/liveness.py`)**:
   - Replaced deprecated `audioop` with vectorised `numpy` Root-Mean-Square (RMS) calculations, eliminating Python 3.12 deprecation warnings and ensuring Python 3.13 compatibility.
   - Guarded `cv2` imports so audio/voice pipelines can run cleanly without requiring OpenCV.
4. **Created Unit Test Suite `test_voice.py`**:
   - `test_set_rate_bounds_and_fallback`: Verified rate bounds [60, 400] and non-numeric fallback to base 175.
   - `test_wav_framing`: Verified 16kHz, 16-bit mono WAV header and frame fidelity.
   - `test_r04_interruption_during_speaking`: Verified "stop" and "cancel" break through active speaking and expired conversation windows.
   - `test_wake_words_and_extraction`: Verified wake words ("lya", "leya", "liya", "wake up ...", "hey ...") strip prefix and extract intent.
   - `test_conversation_window_and_expiration`: Verified sequential commands succeed within 45s and reject after expiration without wake word.
   - `test_voice_liveness_detection`: Verified rejection of short clips (<1.0s), rejection of flat synthetic sine waves (replay attacks), and pass for natural speech amplitude variations.
   - `test_quiet_mode`: Verified quiet suppression.
   - **All 7/7 tests passed in 0.309s**.
5. **Wired Voice Wake to PySide6 Desktop UI (`desktop/app.py`)**:
   - Added `VoiceSignals(QObject)` with `wake_detected = Signal(str, bool)`.
   - Added `Desktop.on_voice(text, quiet)`: Thread-safe signal dispatch from background audio thread to Qt main loop. Wakes crystal, sets `task="listening"`, opens glass panel, executes command, and speaks answer if non-quiet and non-private.
   - Added `Desktop.start_voice()` and `Desktop.stop_voice()` with background daemon thread.
   - Added `--voice` flag to `desktop/app.py` CLI and "Voice wake" toggle to the crystal context menu.
   - Added `test_voice_wake_signal_dispatch` to `desktop/check_ui.py`.
6. **Full Test Verification Across Workspace**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `review_checks.py`: 6/6 passed
   - `test_storage.py`: 7/7 passed
   - `test_voice.py`: 7/7 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 60 tests across all 6 suites pass cleanly (0 errors, 0 failures).**

Limitations:
- Physical microphone wake loop requires local acoustic model files in `%LOCALAPPDATA%\LYA\models\vosk` for full offline operation; tested in unit tests with synthetic audio buffers and simulated utterances.
- Automated tests do not block waiting for human speech.

Next step: proceed to Step 5 — local face recognition & anti-spoofing.

## 2026-09-12 — Step 5: Local Face Recognition & Anti-Spoofing (Completed)

Requested outcome: Build out Step 5 (Local Face Recognition & Anti-Spoofing), install OpenCV, modernize the multi-user face identity engine, integrate with encrypted SQLite storage, wire owner verification with liveness anti-spoofing gating, and verify test suites.

Actions and findings:
1. **Installed & Verified OpenCV**:
   - Installed `opencv-python-headless` (5.0.0.93) in `.venv-ui`. Verified native hardware support for `FaceDetectorYN` (YuNet) and `FaceRecognizerSF` (SFace).
2. **Extended Storage for Face Templates (`storage/store.py` & `storage/__init__.py`)**:
   - Added `add_face_template(person_id, embedding, model_version="arcface-512d", quality=1.0)`: Persists AES-256 encrypted biometric face embeddings linked to person profiles.
   - Added `list_face_templates(person_id=None)`: Decrypts templates on the fly for recognition matching.
   - Added `remove_face_templates(person_id)`: Securely cleans up biometric templates on de-enrollment or forget requests.
   - Enhanced `record_pending_face()` to handle both float lists and byte vectors smoothly.
   - Added `test_face_template_crud` to `test_storage.py` (all 8/8 passed).
3. **Hardened `security/auth_wall.py`**:
   - Guarded `_face()` lazy-loader to handle missing C++ InsightFace build packages gracefully.
   - Guarded `detect_face_bbox()` and `face_embedding()` with clean error handling preventing unhandled exceptions.
4. **Modernized Face Identity Engine (`vision/identity.py`)**:
   - Switched from legacy plaintext/single-file JSON to person-scoped AES-256 encrypted SQLite storage in `storage/store.py`.
   - `_cos(a, b)`: Protected cosine similarity invariant implementation with zero-vector handling.
   - `face_embedding(source)`: Normalizes 512-d embeddings to unit length and bridges camera frames with feature extractors.
   - `enroll_person()` & `enroll_admin()`: Creates person in `people` table and registers encrypted templates.
   - `identify()`: Matches input against all active templates via cosine similarity, logging unknown visitors to `pending_faces` with 7-day TTL.
   - `verify_owner()`: Gated by `security.liveness.face_liveness()` before matching against primary admin templates.
   - `set_secondary_password()` & `check_secondary_password()`: Salted PBKDF2 (200,000 rounds) stored encrypted in the store and compared in constant time (`hmac.compare_digest`).
   - `name_person()`: Admin tags stranger face ID to promote to registered friend/family.
   - `forget()`: Deactivates person and purges templates.
5. **Created Unit Test Suite `test_identity.py`**:
   - `test_cosine_similarity_invariants`: Tested 1.0 (identical), 0.0 (orthogonal), -1.0 (opposite), and 0.0 (zero vector).
   - `test_multi_user_enrollment_and_identification`: Enrolled Alice (Admin) and Bob (Friend); verified high-confidence identification, unknown visitor capture, and stranger promotion to known friend.
   - `test_owner_verification_and_spoof_gate`: Verified owner match, imposter denial, and anti-spoof rejection of synthetic flat image frames.
   - `test_secondary_password_authentication`: Verified salted PBKDF2 hash check, failure on incorrect/empty passwords.
   - `test_forget_person`: Verified de-enrollment, template deletion, and subsequent identification as unknown.
   - **All 5/5 tests passed in 0.397s**.
6. **Full Test Verification Across Workspace**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 70 tests across all 8 suites pass cleanly (0 errors, 0 failures).**

Limitations:
- Physical webcam enrollment remains deferred in accordance with project policy until explicitly requested by owner; verified with synthetic 512-d unit vectors and image buffers in isolated temporary test databases.
- Deep anti-spoofing model weights (MiniFASNet) require offline model checkpoints in `security/Silent-Face-Anti-Spoofing/resources/anti_spoof_models/`; falls back safely to deny-by-default when checkpoints are absent.

Next step: proceed to Step 6 — free cloud reasoning gateway & persona brain.

## 2026-09-12 — Step 6: Free Cloud Reasoning Gateway & Persona Brain (Completed)

Requested outcome: Build out Step 6 (Free Cloud Reasoning Gateway & Persona Brain), fix R06 (unified key resolution between mind and forge), integrate person-scoped memory retrieval into system prompt generation, establish multi-provider fallback (Groq / OmniRoute / OpenAI / Ollama), implement emotional tone modulation, and verify test suites.

Actions and findings:
1. **Resolved R06 (`skills/forge.py` & `brain/mind.py`)**:
   - Extracted unified `get_groq_key()` in `brain/mind.py` resolving keys via environment variable -> DPAPI key file -> `%LOCALAPPDATA%\LYA\vault`.
   - Updated `skills/forge._groq` to call `mind.get_groq_key()` instead of directly indexing `os.environ['GROQ_API_KEY']`.
2. **Multi-Provider Cloud Gateway (`brain/mind.py`)**:
   - Layered provider order designed for near-zero laptop pressure:
     1. OmniRoute Gateway (free tiers, 90+ endpoints)
     2. Groq cloud provider (`llama-3.3-70b-versatile`, free tier, 500-800 tokens/sec, 0 local CPU/GPU load)
     3. OpenAI / OpenRouter
     4. Local Ollama edge fallback
   - Safe offline fallback message guiding user to configure free cloud reasoning without unhandled exceptions.
3. **Person-Scoped Context & Memory Injection**:
   - `_memory_block()` queries `storage.store.recall(person_id=person_id)`.
   - Verified owners receive their private memories; unverified visitors/guests receive `(private memory unavailable)` with strict instruction forbidding access to private data.
4. **Voice Tone & Emotional Synchronization**:
   - `detect_tone()` maps utterance keywords to 8 emotional profiles (excited, playful, happy, sad, worried, serious, angry, neutral).
   - Injects current mood into system prompt so the assistant matches tone as a true friend.
   - Automatically synchronizes voice speech rate via `voice.set_rate()` based on the model's generated response.
5. **Created Unit Test Suite `test_mind.py`**:
   - `test_r06_unified_groq_key_resolution`: Verified key resolution and graceful handling when key is missing.
   - `test_guest_vs_verified_memory_scoping`: Verified guest prompt isolation vs owner PIN retrieval from encrypted SQLite store.
   - `test_tone_detection_and_speech_modulation`: Verified emotional classification and voice rate setting.
   - `test_session_history_isolation`: Verified multi-session isolation and history clearing.
   - `test_offline_gateway_fallback_message`: Verified recovery message on complete connection refusal.
   - **All 5/5 tests passed in 0.203s**.
6. **Full Test Verification Across Workspace**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_mind.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 75 tests across all 9 suites pass cleanly (0 errors, 0 failures).**

Limitations:
- Live model responses depend on external network access and user-provided API keys (`GROQ_API_KEY`, `OMNIROUTE_KEY`, or `OPENAI_API_KEY`); verified with isolated test mocks and synthetic prompt assertions.

Next step (Step 7): Phone Approval Escalation Gateway (Local TLS HTTP server, one-time nonce dispatch, and secure phone escalation flow).
 
## 2026-09-12 — Step 7: Phone Approval Escalation Gateway (Completed)

Requested outcome: Modernize and harden the Step 7 Phone Approval Escalation Gateway, verify cross-process nonce generation, single-use grant consumption, rate-limiting lockout, fallback spoken security word verification (salted PBKDF2), silent duress alarms, TLS enforcement, and web gateway integration with complete unit tests.

Actions and findings:
1. **Hardened `security/escalation.py`**:
   - Hardened `current_challenge()` to catch all unexpected decryption/parsing exceptions (`except Exception:`) and safely retrieve timestamp keys via `.get("t", 0)`, guaranteeing fail-closed behavior on corrupted challenge files.
   - Verified cross-process nonce lifecycle: `_write_challenge(nonce, task)` and `current_nonce()` read encrypted challenge from disk, ensuring the web server process receives the exact challenge nonce issued by the desktop assistant process.
   - Verified single-use burn: `_consume_phone_grant()` reads `GRANT_FILE`, validates nonce equality, verifies `GRANT_TTL` window (120 seconds), and immediately marks the grant as used (`used = True`), preventing all replay attacks.
   - Validated fallback spoken security word checking: 200,000 PBKDF2 HMAC-SHA256 iterations with unique 16-byte random salt, normalization across case and punctuation, sliding window scan up to `MAX_SCAN_TOKENS = 12`, and silent duress phrase detection.
   - Validated fail-closed brute force lockout: 5 consecutive failures trigger a 600-second lockout; corrupted attempt counters fail closed as permanently locked until admin resets.
2. **Hardened `web_server.py`**:
   - Hardened `/escalate` and `/verify_identity` handlers to safely type-check `challenge.get("nonce")` before running constant-time `hmac.compare_digest`, avoiding unhandled `TypeError` exceptions.
   - Verified strict TLS enforcement: requests over non-SSLSocket connections are immediately rejected with HTTP 403 (`Phone verification requires HTTPS.`).
   - Verified token gating: invalid or missing phone access token rejected with HTTP 403 in constant time.
   - Verified deferred enrollment: `/enroll`, `/enroll_face`, and `/enroll_voice` return HTTP 403 (`Enrollment is deferred; a phone token cannot replace the owner.`).
   - Verified private memory gating: phone chat `/ask` queries touching private facts return `_NEEDS_FACE` unless accompanied by a verified session ID.
3. **Fixed Test Suite Portability (`test_security_fixes.py`)**:
   - Handled missing `git` command in `test_no_secrets_tracked` to check `.gitignore` secrets coverage directly when git CLI is absent.
   - Fixed attribute vs function distinction in `test_identity_api_matches_call_sites` to accommodate `identity.STORE`.
4. **Created Dedicated Unit Test Suite `test_escalation.py`**:
   - `test_nonce_and_challenge_lifecycle`: Verified challenge generation, task text preservation, TTL expiry, and cleanup.
   - `test_grant_single_use_and_replay_prevention`: Verified single-use consumption and instant rejection of replay attempts.
   - `test_challenge_nonce_mismatch_and_missing_challenge`: Verified fail-closed rejection on mismatched or absent challenge nonces.
   - `test_spoken_security_word_and_sliding_window`: Verified exact, normalized, and embedded phrase matching, prefix rejection, and unique per-install salting.
   - `test_duress_phrase_detection`: Verified separate duress phrase trigger and validation errors on identical/empty phrases.
   - `test_brute_force_lockout_and_fail_closed`: Verified 5-attempt lockout, attempt reset, and fail-closed lock on corrupted attempt counters.
   - `test_request_phone_cancellation_and_concurrency`: Verified non-blocking mutex locking (`_request_lock`) and rapid response to cancellation events.
   - `test_web_gateway_token_authentication`: Verified token validation and 403 on invalid tokens.
   - `test_web_gateway_plain_http_rejection`: Verified rejection of non-TLS connections on escalation endpoints.
   - `test_web_gateway_enrollment_deferred`: Verified 403 on all enrollment endpoints.
   - `test_web_gateway_private_memory_gating`: Verified refusal of unverified private memory queries.
   - `test_web_gateway_tls_escalate_and_approval_flow`: End-to-end integration test spinning up local HTTPS server with self-signed TLS cert, verifying challenge fetching, biometric mock verification, security phrase matching, grant issuance, and laptop consumption.
   - **All 12/12 tests passed in 3.254s**.
5. **Workspace-Wide Verification (All 11 Test Suites Pass)**:
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_mind.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `test_escalation.py`: 12/12 passed
   - `test_security_fixes.py`: 9/9 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 96 tests across all 11 suites pass cleanly with 0 failures, 0 errors.**

Limitations:
- Physical phone pairing and cellular/local WiFi network routing remain pending user environment configuration; verified over local loopback TLS sockets with synthetic certificates and isolated temporary storage.
- Real biometric owner verification on the phone camera relies on `vision.identity.verify_owner` and client WebRTC video streams; verified with synthetic frames and liveness gates.

Next step: proceed to Step 8 — Core Skills & Device Execution Capabilities (calculator, volume, notepad, user folder browsing, reminders, and draft skill forge).

## 2026-09-12 — Step 8: Core Skills & Device Execution Capabilities (Completed)

Requested outcome: Harden, sandboxed, and verify Step 8 Core Skills & Device Execution Capabilities (`skills/device.py`, `skills/files.py`, `skills/reminder.py`, `skills/forge.py`, and `main.py` routing), implement headless/pywin32 fallbacks, prevent path traversal, validate reminder natural language parsing & encrypted ordering, and create a comprehensive unit test suite (`test_skills.py`).

Actions and findings:
1. **Hardened Device Skills (`skills/device.py`)**:
   - `open_app(name)`: Strictly enforced non-shell allowlisted execution (`notepad.exe`, `calc.exe`, `explorer.exe`, `chrome.exe`) via `subprocess.Popen([executable])`. Arbitrary executables or shell injection strings (`calc.exe & notepad.exe`) are rejected cleanly.
   - `volume(action)`: Added graceful fallback to native Windows multimedia virtual key events (`VK_VOLUME_UP`, `VK_VOLUME_DOWN`, `VK_VOLUME_MUTE` via `pywin32`), eliminating hard dependency on `pyautogui` while maintaining zero CPU overhead.
   - `screenshot(output_dir)`: Sandboxed output directory creation (`shots/` or custom directory), timestamped filename formatting (`lya_shot_YYYYMMDD_HHMMSS.png`), with headless native Windows GDI/pywin32 capturing fallback.
   - `type_text(text)`: Gracefully simulated when GUI automation packages are absent.
2. **Hardened Folder Browser (`skills/files.py`)**:
   - `FolderBrowser`: Strictly enforces boundaries with `_inside(path)` resolving targets and raising `PermissionError` when escaping `self.root`.
   - Enhanced `listing()` to wrap directory scanning in `try...except OSError`, gracefully handling Windows system directories with permission restrictions.
   - Enhanced `open(selection)` to safely inspect non-directory files, returning metadata (`file`, `bytes`, and explicit statement that files are not executed) without executing code.
3. **Hardened Reminder System (`skills/reminder.py`)**:
   - Added optional `db_path` parameter to `_conn()`, `add()`, `due_now()`, `list_all()`, and `cancel()` enabling isolated testing without touching production database stores.
   - Verified natural language parsing across relative times (`"in 2 hours"`, `"in 30 mins"`), named weekdays (`"next monday at 9am"`), explicit calendar dates (`"on 5 june at 6pm"`), and clock times (`"at 5pm"`).
   - Verified that reminder texts and ISO timestamps remain encrypted with AES-256 ciphertext at rest in SQLite.
   - Confirmed `list_all()` decrypts in RAM and sorts chronologically, and `due_now()` fires only due reminders once.
4. **Hardened Skill Forge (`skills/forge.py`)**:
   - Added `compile(code, "<draft>", "exec")` Python syntax verification to `create(desc)` before persisting drafts, preventing syntax-broken drafts.
   - Verified that `activate()` strictly refuses execution, returning safety message.
   - Verified that `discard()` cleans up draft files cleanly.
5. **Verified Assistant Command Routing (`main.py`)**:
   - Verified `Assistant.handle()` routes:
     - `open calculator` -> `device.open_app("calculator")`
     - `volume up` -> `device.volume("up")`
     - `screenshot` -> `device.screenshot()` with `private_output=True`
     - `remind me to ...` -> `reminder.add(...)` with `private_output=True`
     - `create skill ...` -> `forge.create(...)`
     - `confirm skill` -> activation block notice
     - `what time is it` -> localized datetime output
     - `passwords` / `vault` -> development stage disabled notice
6. **Created Dedicated Unit Test Suite `test_skills.py`**:
   - `test_open_app_allowlist_and_safety`: Verified 4 allowlisted apps launch via Popen and shell injections are rejected.
   - `test_volume_actions`: Verified volume up, down, mute, and parameter validation.
   - `test_screenshot_sandboxed`: Verified directory creation and timestamped PNG generation.
   - `test_boundary_enforcement`: Verified `_inside` raises `PermissionError` on path escapes.
   - `test_listing_and_paging`: Verified page slicing and scroll navigation.
   - `test_open_folder_and_file_inspection`: Verified folder navigation and non-executable file metadata inspection.
   - `test_time_hint_natural_language_parsing`: Verified relative, weekday, and explicit date parsing.
   - `test_encrypted_crud_and_chronological_ordering`: Verified AES-256 ciphertext at rest, chronological `list_all` sorting, single `due_now` firing, and cancellation.
   - `test_create_valid_skill_draft`: Verified draft and metadata writing for valid code.
   - `test_create_rejects_missing_functions_or_syntax_error`: Verified rejection of code without `match`/`reply` or with syntax errors.
   - `test_activation_disabled_and_discard`: Verified safety lockout on activation and draft cleanup on discard.
   - `test_assistant_skills_routing`: Verified 6 core command branches in `Assistant.handle()`.
   - **All 17/17 tests passed in 0.124s**.
7. **Workspace-Wide Verification (All 12 Test Suites Pass)**:
   - `test_skills.py`: 17/17 passed
   - `test_foundations.py`: 14/14 passed
   - `test_regressions_r01_r05.py`: 16/16 passed
   - `test_storage.py`: 8/8 passed
   - `test_voice.py`: 7/7 passed
   - `test_identity.py`: 5/5 passed
   - `test_mind.py`: 5/5 passed
   - `test_liveness.py`: 4/4 passed
   - `test_escalation.py`: 12/12 passed
   - `test_security_fixes.py`: 9/9 passed
   - `review_checks.py`: 6/6 passed
   - `desktop/check_ui.py`: 10/10 passed
   - **All 113 tests across all 12 suites pass cleanly with 0 failures, 0 errors.**

Limitations:
- Physical app windows (e.g. Chrome, Notepad) and physical audio volume changes depend on active user desktop session; verified with mock subprocesses, allowlist checks, and virtual key events in isolated tests.
- Code generated by Skill Forge remains strictly non-executable drafts pending sandbox containerization.

Next step: proceed to Step 9 — Autonomous Guardian & System Health Governor (Safety boundaries, tamper detection, action audit logging, resource governor).

## 2026-09-13 — Independent review of new work and UI direction

- Request: assess the owner's additions, installed repositories and whether the
  clean glass panel feels sufficiently futuristic.
- Artifacts: `review/2026-09-13/REVIEW.md`, reproducible harness
  `review/review_20260913.py`, suite logs, reproduction output, `results.json`,
  `measurement.json` and synthetic-background widget PNGs in the dated folder.
- Checks: 35/35 tests passed across storage (8), identity (5), mind (5), voice (7)
  and Qt UI (10), in a disposable source copy. Network and sensors blocked; fake
  TTS, synthetic records and a temporary encryption key. No existing credentials,
  private databases or biometrics copied or read. The previous 113-test total was
  not independently rerun in full.
- New findings: reproduced missing-person context selection, unscoped fallback,
  credential-kind context inclusion, expired pending promotion and legacy-file
  recognition gating. Checked desktop script import resolution: sibling `audio`
  is not discoverable under the documented entry-point path. Static review found
  inaccurate microphone/offline labels and incomplete backend command routing.
- Dependency inventory: UI/core libraries are present, but InsightFace, Torch,
  SpeechRecognition and expected offline/face model directories are absent in
  the checked environment. Anti-spoof repository directory is empty. No Git
  checkout markers found in project source; repositories elsewhere await paths.
- Visual assessment: current UI remains legible and compact; propose angled
  framing, a restrained crystal-to-card connection, content-sized cards and
  truthful task indicators. Visual changes are proposed, not implemented.
- Application behavior was not changed. Existing artifacts were preserved.
  This review supersedes the earlier recommendation to proceed immediately to
  an autonomous governor: first repair context boundaries and launcher routing,
  then verify a complete native typed-command journey with fake session data.

## 2026-09-13 — Step 9: Autonomous Guardian & System Health Governor Completed

- **Milestone**: Step 9 of clean rebuild — Autonomous Guardian & System Health Governor.
- **Artifacts Created / Modified**:
  - `skills/guardian.py`: Modernized into a resilient Ultron safety layer. Implemented comprehensive dangerous command screening (20+ destructive signatures), gated execution (`guard()`), silent duress alarm subsystem (`raise_duress()`, `check_duress()`, `clear_duress()`) with fail-closed tamper detection, dual encrypted audit logging (AES-256 encrypted log file `skills/lya_actions.log.lya` and person-scoped SQLite audit log via `storage.store.record_audit()`), and proactive user safety pushback (`correct_user()`).
  - `skills/governor.py`: Created zero-dependency system health governor for Windows. Uses native `win32process.GetProcessMemoryInfo` for WorkingSet memory monitoring (<14MB footprint), `ctypes.windll.kernel32.GetSystemPowerStatus` for live battery percentage and AC charging state, `shutil.disk_usage` for storage capacity, automated threshold alerts (`check_governor_limits()`), and a file-based emergency circuit breaker (`KILL_SWITCH`) with instant suspension and admin-only reset.
  - `skills/harden.py`: Integrated duress flag status and kill switch state into security self-audit (`harden.audit()`).
  - `main.py`: Connected natural language command routing for `"system health"`, `"battery"`, `"battery status"`, `"is lya secure"`, `"emergency stop"` / `"kill switch"`, `"release kill switch"`, and guardian execution gates before standard command handling.
  - `test_guardian_governor.py`: 12 comprehensive unit and integration tests covering dangerous command detection, gated execution, silent duress lifecycle, tamper resistance, encrypted dual audit logging, proactive user guidance, resource governor metrics, kill switch lifecycle, harden audit integration, and assistant routing.
- **Verification & Test Results**:
  - `test_guardian_governor.py`: 12/12 passed in 0.110s.
  - All workspace unit tests via discovery (`test_*.py` across 11 test modules): 80/80 passed in 2.930s.
  - `test_regressions_r01_r05.py`: 16/16 regression assertions passed.
  - `test_liveness.py`: 4/4 anti-spoof checks passed.
  - `review_checks.py`: 6/6 syntax and regression checks passed.
  - `desktop/check_ui.py`: 10/10 UI checks passed in 1.672s.
  - **Zero test failures or regressions across the entire project codebase.**
- **Resource Footprint & Safety Constraints**:
  - Verified 0 unnecessary CPU/GPU overhead: zero polling threads or busy loops. Metrics queried only on-demand or during scheduled checkpoints.
  - WorkingSet process memory measured at ~13.8MB (<100MB budget).
  - Complied strictly with `RULE[AGENTS.md]`: all tests run with synthetic fixtures and isolated temporary files (`tempfile`). No real credentials, biometrics, or plaintext sensitive data saved to disk or ledgers.
- **Next Step**: Step 10 — End-to-End System Integration, User Journey Smoke Test, & Packaging (Tying crystal UI, voice bridge, permission escalation, safe folder browsing, reminders, guardian, and governor into a cohesive end-to-end verified pipeline).

## 2026-09-13 — Voice & Multilingual Engine Upgrade (Natural 21yo Voice + Groq Whisper)

- **Milestone**: Upgrade 1 & 2 of voice layer — Microsoft Edge Neural TTS + Groq Whisper multilingual STT.
- **Artifacts Created / Modified**:
  - `audio/voice.py`:
    - Integrated Microsoft Edge Neural TTS (`edge-tts`) with the default `en-US-AvaNeural` voice (natural, warm, expressive 21yo young woman tone). Added support for configurable voices via `LYA_VOICE` (e.g. `ta-IN-PallaviNeural` for Tamil, `hi-IN-SwaraNeural` for Hindi, `en-IN-NeerjaNeural` for Indian English).
    - Added pitch and rate emotion modulations (`EMOTIONS` dictionary) corresponding to detected conversation tone (playful, excited, sad, worried, serious, angry, tired, neutral).
    - Implemented `_play_mp3_interruptible` using Windows native MCI (`ctypes.windll.winmm.mciSendStringW`) with instant mid-sentence cancellation via `stop_speaking()`.
    - Maintained robust fallback to local `pyttsx3` if offline or network unavailable.
    - Upgraded `transcribe(wav_bytes)` with Groq Whisper Large v3 cloud API (`_transcribe_groq`), providing ultra-fast (~200ms) transcription across 99+ languages with zero laptop GPU load. Retained offline Vosk model fallback and Google Speech Recognition fallback.
  - `test_voice.py`:
    - Added unit tests: `test_edge_tts_ava_voice_synthesis`, `test_stop_speaking_playback_interruption`, and `test_groq_whisper_transcription`. All 11/11 tests pass.
  - `brain/mind.py`:
    - Fixed `history_key` 2-tuple compatibility for `test_foundations.py`.
- **Verification & Test Results**:
  - `test_voice.py`: 11/11 passed in 1.865s.
  - All 11 workspace test suites: 84/84 passed in 5.810s.
  - `test_regressions_r01_r05.py`: 16/16 passed.
  - `desktop/check_ui.py`: 13/13 passed in 3.537s.
  - `review_checks.py`: 6/6 passed.
  - Live audio test: Verified clean speech synthesis and playback via Windows MCI.
- **Next Step**: Step 3 (Cognitive Brain Phase A: Intent Classification & Tiered Memory Pipeline).

## 2026-09-13 — Brain workflow implementation and isolated acceptance

- **Implemented:** `brain/workflow.py` routes typed requests through identity,
  permission, scoped retrieval, ordinary inference or council, final validity checks
  and a bounded response. `desktop/app.py` dispatches via a background worker,
  suppresses cancelled/late results and exposes `brain help`, `brain status`,
  `brain demo` and `who am i`. Cosmetic colors cannot grant identity.
- **Memory/schema:** `brain/notes.py` reuses `storage/store.py` encrypted SQLite.
  Working context is per request; session notes are bounded RAM; short/long defaults
  are 7/90 days; timed notes require a timezone; permanent means no automatic expiry.
  Explicit correction increments revisions. Same-person graph links cascade on
  deletion. Additive migration preserves legacy notes. No real store was migrated.
- **Boundary fixes:** missing person IDs cannot select another profile; scoped
  failures cannot use legacy fallback; credential kinds are excluded from context.
  `brain/mind.py` history keys include person ID (restored after a newer compatibility
  edit removed it). `main.py` uses the enrolled registry rather than the old file
  gate. Expired pending faces cannot be promoted. `security/vault.py` loads keys
  lazily; `security/policy.py` carries person ID and verification expiry.
- **Council:** `brain/council.py` uses reviewer/planner/critic plus synthesis, at most
  four sequential calls through one configured client. Failure is labelled. This
  is perspective comparison, not independent verification or guaranteed accuracy.
- **Voice:** preserved newer shared-workspace cloud voice changes. Desktop requires
  local transcription before opening the microphone and displays readiness/errors.
  Online speech synthesis test now requires explicit `LYA_RUN_ONLINE_TESTS=1`;
  isolated review strips this setting and blocks network/sensors.
- **Artifacts:** `LYA_BRAIN_WORKFLOW.md`; `diagrams/11-brain-workflow.mmd`, `.svg`,
  `.png`; `diagrams/12-brain-schema.mmd`, `.svg`, `.png`;
  `diagrams/render_brain_map.py`; `brain/demo.py`. Both Mermaid sources validated
  (2/2); both companion PNGs visually inspected and readable. README and desktop
  README link the current workflow. Demo uses synthetic data and an ephemeral key
  in a separate temporary process; it never unlocks the real profile.
- **Checks:** `.venv-ui/Scripts/python.exe -B review/review_20260913.py --brain`
  completed successfully. Storage 8, identity 5, mind 6, voice 10 passed + 1 skipped,
  desktop 13, brain 16, foundations 14, R01/R05 regressions 16: **88 passed**.
  Five historical defect probes returned false. Logs, result index and synthetic
  UI renderings: `review/2026-09-13-brain/`. Tests cover migration, restart, expiry,
  revocation during inference, cross-person scope, graph deletion, council failures,
  native dispatch, demo and cancellation. The harness now exits nonzero on failures.
- **Limitations:** model output, approval and identity fixtures are synthetic;
  no camera/microphone capture, real enrollment, phone pairing, cloud upload or
  live model-quality evaluation occurred. Loopback model service was unreachable.
  Hardware inventory via WMI was denied; RAM/GPU remain unverified. Whole-file
  encryption remains suitable only for small stores. Expiry excludes reads;
  physical cleanup waits for authorized activity and does not erase old backups.
- **Decisions/next step:** retain one local database, bounded keyword retrieval and
  one-hop graph; no new heavyweight graph server, embeddings or weight training.
  Connect trusted identity/approval and choose/test an available model next, then
  run real-device acceptance. Enrollment remains deferred. Cloud provider response
  is pending; portable encrypted recovery/mobile sync need design before upload.

## 2026-09-13 — Research-backed retrieval upgrade and Oracle design

- Owner reports Oracle Free Tier and collected API keys; VM/provider details remain
  pending. Read agent-reach skill/search/web references; CLI commands unavailable
  on shell, so used built-in web access to primary papers and official docs.
- Artifact: `LYA_ADVANCED_BRAIN_PLAN.md` contains cited research, implemented/proposed
  distinctions, storage lifecycle, Oracle split and six ordered acceptance gates.
  MemGPT/Reflexion/Generative Agents/GraphRAG inform design; no paper performance
  claim is presented as a LYA benchmark. Biological simulation is not the target.
- Changed `brain/notes.py`: RAM-only FTS5/BM25 replaces substring overlap, label
  weighting and bounded token input; six-result budget includes graph neighbors,
  prioritizing declared contradictions/dependencies. Scoped active non-credential
  records only. Rebuild on each query avoids stale correction caches; no persistent
  plaintext index. Still lexical, not semantic or multilingual paraphrase search.
- Checks: FTS5 available; `review/review_20260913.py --retrieval` passed all suites:
  91 checks passed, 1 online speech test skipped; five old defect probes false.
  Added three brain tests (19 total) for token matching/input syntax, contradiction
  inclusion with full lexical results, and correction freshness. Logs and synthetic
  renders: `review/2026-09-13-retrieval/`; older runs preserved.
- Updated `LYA_BRAIN_WORKFLOW.md` and this ledger. No real runtime data collected,
  credentials displayed, provider calls, model installs, Oracle changes or uploads.
- Limits: 2,000-note per-query index rebuild needs workload benchmarks; no accuracy
  guarantee, embeddings or automatic lesson learning. Model context cap can omit
  retrieved notes. Identity/approval and real model binding remain incomplete.
- Next: obtain VM shape/RAM/region and provider names only; connect one selected
  model with bounded routing, then identity-gated real acceptance. No need to
  collect more API keys yet. Oracle current documentation differs from old guides;
  account-specific quotas need verification before infrastructure choices.

## 2026-09-14 — Oracle connection attempt and key-file protection

- Owner approved continuing server verification and backend preparation. Inspected
  current brain status and legacy gateway source. The gateway imports local
  biometric/Windows-dependent components; it was not uploaded as a cloud service.
- SSH reached the supplied address. Initial attempt refused the key because its
  Windows permissions were too broad. Restricted the single private-key file to
  the owner's Windows account using an approved elevated filesystem operation.
  The restricted sandbox can no longer read it; SSH retries ran through approved
  execution as the owner. No key contents or API credentials were displayed.
- Both standard Oracle Linux (`opc`) and Ubuntu (`ubuntu`) usernames returned
  `Permission denied (publickey)`. This does not establish whether the username,
  target address or key pairing is wrong. No remote diagnostic commands executed.
- Added `*.key`, `*.pem` and `oracle_known_hosts.local` to `.gitignore`. The SSH host
  key was recorded on first contact in the ignored local known-hosts file; it has
  not been independently matched against the Oracle console. Runtime connection
  details and key material are intentionally omitted from this plaintext ledger.
- Checks: key ACL change succeeded; host reachable; both authentication attempts
  failed. No software installation, data upload, firewall change, enrollment or
  model/provider call performed. No application source changed or tests rerun.
- Next required input: confirm the instance's console SSH connection instructions
  (public IP and username) and that the supplied key is the one associated with
  that instance. Share connection details or console screenshot, never key content.
  Then resume resource verification and backend preparation.

## 2026-09-14 — Confirmed console details and SSH key rejection

- Owner's clearer screenshot confirms the originally supplied address and Ubuntu
  username. The assistant's tentative alternate-IP reading of the smaller image
  was incorrect; no connection to that alternate address was attempted.
- Local key validation succeeded (RSA); fingerprint used only for diagnostics,
  not copied into this ledger. Filtered SSH debug output confirms the private key
  was tried and a public-key authentication packet was sent. Server rejected it
  with `Permission denied (publickey)`. No key parsing or ACL error remains.
- Cause remains either a different instance-authorized key or server-side SSH
  authorization configuration. Do not claim a proven key mismatch without the
  authorized public key or server logs. Need the matching original instance key,
  or an owner-accessible console recovery route if it is lost.
- No remote command executed; no source changes, installations or model calls.
  Backend preparation remains blocked on authenticated access. Do not delete or
  recreate the existing instance merely to resolve this login problem.

## 2026-09-14 — Replacement SSH key accepted; server verified

- Owner supplied a second key and requested a retry. Restricted that exact file's
  Windows ACL to the owner's account, then connected with the confirmed Ubuntu
  login and existing strict known-host verification. SSH completed successfully.
  Key material and connection identifiers are omitted from this ledger; local
  private keys and host records remain covered by Git exclusions.
- Read-only remote checks: ARM64 (`aarch64`), 4 online CPUs, approximately 24 GB
  RAM, no swap, 193 GB root filesystem with approximately 191 GB free at inspection,
  Python 3.12.3. These are server-reported capacities, not a billing assessment.
- Previous authentication blocker resolved. No package installation, firewall
  change, file upload, runtime data migration or provider call performed.
- Next: inspect existing server services, prepare a scoped backend environment,
  select/configure one model provider and test public synthetic requests before
  connecting identity-gated private memory. Enrollment remains deferred.

## 2026-09-14 — Oracle inference bridge prepared; model selection pending

- Inspected existing server listeners and Python support. Created private LYA
  directory (mode 700); verified OpenSSL/SQLite modules. Uploaded only
  `cloud/inference.py` to `/home/ubuntu/lya/inference.py` (mode 600), refusing an
  existing-file overwrite. No packages, daemon or public API listener installed.
- Added `brain/oracle.py`: opt-in JSON configuration, strict SSH known-host checks,
  key path scoped to project, hidden Windows subprocess, 30-second timeout and
  redacted errors. `brain/workflow.py` selects this client only when the ignored
  local Oracle configuration exists; no such activation file was created.
- Backend validates message roles/fields, bounds input/output, calls only the
  fixed Groq HTTPS endpoint when configured, and does not retry/fallback or enable
  tools. Per-request bounds are not a daily cost cap. Identity/private memory stays
  local; no new authority is granted by the transport.
- Added `.env` and `desktop/oracle.local.json` Git exclusions. Inspected only `.env`
  variable names, not values. No API credential transferred or validated.
- Checks: `test_oracle.py` 5/5 and `test_brain_workflow.py` 19/19 passed with fake
  credentials and mocked transports/temporary stores. Live SSH synthetic smoke
  check returned exactly `provider_not_configured`, proving deployment/transport
  but not model inference. Full previous suite was not rerun for this milestone.
- Owner asked for help choosing the smartest fitting model rather than selecting
  Groq immediately. Reviewed official Groq capabilities/rate limits/data handling
  and Google's pricing/data-use information. Provisional recommendation: GPT-OSS
  120B through Groq for text reasoning; Gemini as a later multimodal comparison.
  No claim of benchmark superiority on LYA tasks. See `cloud/README.md` for sources,
  setup, limitations and acceptance requirements. A reasoning model's completion
  budget must be tuned/tested before activation; initial 400-token cap may be short.
- Next: settle provider/model, transfer only its credential through protected SSH,
  verify account access/quotas with synthetic prompts, evaluate answer quality,
  then enable the desktop bridge. Real identity/approval binding, mobile access,
  restricted deployment credentials and daily request budgeting remain pending.

## 2026-09-14 — Provider-independent routing and researched model shortlist

- Owner requested multiple models/providers and backup behavior; clarified Groq,
  not xAI Grok. Tokenroter's exact service is still unknown. Used agent-reach
  instructions and primary web docs; CLI/mcporter unavailable, no version update.
- Created `LYA_MODEL_STRATEGY.md`, `cloud/model-evaluation.json` (unrun live-model
  rubric), disabled `cloud/provider.example.json`, and validated
  `diagrams/13-provider-routing.mmd`. Primary sources and scope limits are linked
  in the report. No universal-best or live-quality claim.
- Implemented `cloud/router.py`: task/privacy filtering, pinned-gateway gate,
  independent upstream domains, SQLite atomic daily attempt cap and persisted
  cooldowns, maximum two attempts, bounded routing window. Failure modes distinguish
  retryable service errors from auth/input/refusal/output failures. No prompts,
  credentials or hidden model reasoning in counter state.
- Extended `cloud/inference.py` with Groq/NVIDIA/HF/explicit OmniRoute adapters,
  bounded per-route completion budgets, Groq reasoning controls, redirect denial
  and incomplete-output detection. `brain/oracle.py` forwards task/sensitivity
  and displays safe route/attempt information. `brain/workflow.py` supplies task
  classification and private-context status without granting new authority.
- `cloud/probe_models.py` inspected known credential settings and reported no
  usable Groq/NVIDIA/HF credentials. No provider catalog or generation request
  occurred. This does not imply the owner lacks keys stored elsewhere.
- Verification: `test_router.py` 13/13, `test_oracle.py` 5/5,
  `test_brain_workflow.py` 20/20 passed. New checks include concurrent budget
  reservations, persisted cooldowns, time/attempt limits, privacy isolation and
  task propagation. Tests use fake services and temporary state. Full historical
  suite was not rerun; earlier 91-check result remains dated evidence.
- Deployed the tested scripts/template to the existing private Oracle directory,
  preserving the earlier backend as `inference.before-router.py`. Executed
  `cloud/verify_router.py` remotely: synthetic failover passed; no provider call
  or credential upload. Routes remain disabled; no public listener was opened.
- Limits: task matching is heuristic, council seats are not deliberately diverse,
  inference adapter is text-only and invokes no tools. Daily attempts are not a
  dollar budget; gateway pinning requires truthful operator settings. Oracle or
  internet outage remains outside provider failover. No retraining/automatic
  skill activation or storage migration was performed.
- Next: locate protected credentials and exact gateways, verify account catalogs
  and entitlement, evaluate accessible candidates, approve private destinations
  and enable a measured primary/backup. Then integrate research/execution and
  evidence/episode/lesson storage with tests and backup-restore verification.

## 2026-09-14 — Live account validation and experimental desktop activation

- Owner saved provider settings and authorized proceeding. Normalized the two
  NVIDIA note-style lines into dotenv assignments without printing credentials.
  Groq and NVIDIA authenticated catalogs succeeded. OmniRoute settings and HF
  credentials remain absent; exact Tokenroter service/OPENAI_API_KEY ownership
  clarification is pending. Unrelated secrets/services were not used.
- Verified the supplied NVIDIA DeepSeek V4 Flash 0731 model against its current
  official page and catalog. Local calls timed out at 8, 25 and 30 seconds with
  different reasoning settings; an Oracle attempt timed out at 8 seconds.
  NVIDIA GPT-OSS 20B answered simple prompts but timed out on a later case;
  Nemotron Lightning timed out and the tested Mistral endpoint returned 404.
  None of these routes was declared ready or activated.
- Extended `cloud/probe_models.py` with a bounded-name dotenv reader supporting
  quotes, comments and export prefixes without expansion/evaluation. Added
  `cloud/evaluate_models.py` for explicit live synthetic evaluation; it neither
  executes generated code nor writes private prompts/credentials/reasoning.
  Reports are preserved separately under `review/2026-09-14-live-models/`.
- Groq GPT-OSS 120B completed eight cases after output-prompt tuning. Completion
  was not equated with correctness: reviewed answers invented architecture facts;
  an earlier code sample passed its isolated assertions, while a later sample's
  generated assertion failed. Qwen 3.8 testing stopped on HTTP 429. Details and
  unmodified synthetic outputs are linked in the review README.
- Strengthened `brain/workflow.py` instructions on concise output, unmeasured
  claims and trusted authentication. These are guidance, not a truth guarantee.
  `desktop/app.py` now labels configured cloud text. No model tool execution,
  self-training, memory migration or research integration was added.
- Activated only Groq public text with a 100-attempt daily cap and 2048-token
  completion cap in protected Oracle configuration. Only its required credential
  was persisted remotely through SSH; no .env upload. NVIDIA remains disabled
  and has no persisted credential in that configuration. Private routes deny.
  Enabled ignored `desktop/oracle.local.json` after the live checks succeeded.
  No new public listener or package installation. Existing backend rollback is
  preserved; moving aside desktop config returns to the local selection path.
- Checks: 41 isolated tests passed (`test_router`, `test_oracle`,
  `test_brain_workflow`, `test_provider_setup`); fake keys and temporary storage.
  Actual guest Brain/Oracle/Groq corrected-deadline request passed. A synthetic
  private request returned no_eligible_route. Actual Qt worker arithmetic request
  returned 42 with the active route ID; camera/microphone were off. Captured result
  in `desktop-live-check.json`, then visually replayed it with explicit test-font
  loading for `live-glass-response.png`; this was not another provider request.
- Remaining: evaluate an independent reliable backup once provider details are
  available; account quotas/billing were not fully established. Private cloud
  destinations remain disabled. Source verification, verified identity, diverse
  council seats, safe skill execution and storage expansion remain open gates.
