# LYA brain strategy: decision and first implementation (2026-09-24)

## Decision

Adopt the research's principles: local handling of private data, explicit memory writes,
permission before protected actions, grounded answers with abstention, and recoverable
encrypted storage. Do **not** transplant the proposed architecture wholesale. It targets
legacy `main.py`/`brain/mind.py` and another laptop, while the native desktop runs
`desktop/app.py` -> `brain/workflow.py` -> `storage/store.py`.

This is an incremental build, not a new "human brain" implementation. No model can
guarantee perfect answers. LYA's advantage must come from retrieval, evidence checks,
bounded tools, and honest uncertainty.

## Machine and current implementation

- Read-only system query on this device: ASUS VivoBook X1504ZA, Intel Core i3-1215U,
  Intel UHD graphics, 7.7 GB RAM, approximately 0.86 GB free at measurement, and
  approximately 258 GB free on C:. Free RAM is a momentary reading, not a capacity
  guarantee. The research document `09-LOCAL-STACK-CPU.md` measured a *different*
  i3-1315U machine; its exact benchmark numbers cannot be transferred here.
- `models/local/` contains a Qwen2.5 1.5B GGUF (~1.1 GB) and a Qwen3 4B GGUF
  (~2.4 GB). Presence on disk does not prove usable inference. `run-local-model.cmd`
  starts the 4B model and `llama-server.exe` is available, but no sustained RAM,
  latency, quality, or power check was run in this review. Neither model should
  auto-start under the observed memory pressure. No new model was installed.
- The native brain already provides guest/verified session separation, policy checks,
  explicit `remember`/`correct`/`forget`, timed retention, person-scoped encrypted
  SQLite, bounded in-memory FTS retrieval, a one-hop relation graph, private
  loopback-only inference, a public provider route, and a bounded council. These
  are code paths, not a claim that the whole assistant is production-ready.
- This initial review found an in-memory FTS5 index at the 2,000-note cap.
  Subsequent synthetic benchmarking found it too slow at that cap. The native
  store now has a whole-file encrypted FTS5 index for new stores; existing stores
  require a verified backup and explicit migration opt-in. See
  [`retrieval-benchmark.md`](retrieval-benchmark.md).
- `storage/recovery.py` can back up selected notes only. It does not recover the
  DPAPI-wrapped master key or all encrypted stores after a Windows reinstall.
  The external `vault_recovery.py` now has a fake-tested portable key and encrypted
  store bundle, but no real key was exported, no off-device copy was made and
  cross-account restoration remains untested. See
  [`recovery-runbook.md`](recovery-runbook.md).

## First completed change

`security/auth_wall.py` previously sent audio containing a spoken security phrase
to Groq Whisper and included the recognized phrase in a report. The keyword gate
now accepts only a caller-supplied **local** transcriber and denies access when
one is absent. Reports no longer echo the phrase. The old `cloud/lya_cloud.py`
caller does not supply a local transcriber, so its legacy vault unlock path is
deliberately unavailable until a tested local adapter is connected. This does
not turn face/voice recognition into trustworthy owner authentication; enrollment
remains deferred. The change does not alter ordinary public speech recognition.

The active `brain/workflow.py` also stopped promising that an 8 GB laptop can
run Qwen3 4B just because the model file exists. Its built-in hardware and
zero-spend plans now require free-RAM, quality and power measurements before
enabling a local model, and keep private requests local with no cloud fallback.
Those responses are labelled `provisional-plan`, not `verified-plan`.

The external recovery script's `_dpapi_unwrap` helper held its production key
path as an import-time default. That made an isolated path override read the
wrong file. It now resolves the configured path when called. A disposable
fake DPAPI key passed export, verify, wrong-passphrase preservation and restore
in `test_vault_recovery.py`. This does **not** prove cross-account recovery or
protect the real vault yet; the owner must later export, verify and store a
real recovery file off-device with its passphrase separate.

## Build order and acceptance gates

1. **Recoverability before real secrets:** review and integrate a portable master-key
   recovery flow with isolated fake-key export/verify/restore tests. Later, the
   owner performs a real export and verify, and stores file and passphrase separately.
   Until then, encrypted stores are not proven recoverable on a new Windows account.
2. **Brain accuracy baseline:** run the supplied golden cases against the *native*
   `Brain` with fake identities/stores and stubbed models. Record grounded answer,
   abstention, permission and provider-failure outcomes. Fix failures on the active
   path before adding new layers. First isolated results and remaining gaps are
   in [`golden-results.md`](golden-results.md).
3. **Measure before changing retrieval/models:** benchmark 100/1,000/2,000 note
   retrieval on a disposable encrypted store; measure model first-token latency,
   RAM and battery in an owner-initiated local session. Keep private requests
   loopback-only and fail closed if local inference cannot run. The initial
   retrieval baseline exceeded the proposed budget; the encrypted in-database
   index now meets it in the synthetic fixture. Before/after details are in
   [`retrieval-benchmark.md`](retrieval-benchmark.md).
4. **Then expand capabilities:** add one deterministic tool at a time behind the
   existing policy and approval path, with a real output and a rollback check.
   Proposed job stores, vector indexes, MCP fabrics and extra clouds wait for a
   demonstrated need.

No new API key, signup or cloud service is needed for these four steps. Existing
provider keys were not read, printed, tested or changed. No camera, microphone,
real biometric data or owner vault was accessed for this review.

## Checks

2026-09-25 continuation: the first new native capability is on-demand device
status for a verified session. It uses local Windows aggregate readings and
does not call a model. Fake-identity/device checks and one read-only live probe
passed. See `brain/device_status.py` and the project-brain ledger. Capability
help now comes from the shared native command registry (2026-09-25). The
encrypted owner task list is documented in `../2026-09-25-task-list/README.md`.

- `python -B -m unittest test_vault_recovery test_auth_wall test_brain_workflow -q`
  using `.venv-ui`: **38 passed**. The authentication tests use fake
  audio/images/templates and
  verify fail-closed behavior, no network call, local phrase matching, and no
  phrase in the result. The brain tests cover the revised capacity-gated plan.
  These are isolated tests, not live enrollment or a
  production authentication claim.
