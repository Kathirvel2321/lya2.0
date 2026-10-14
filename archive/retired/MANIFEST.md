# noneeded/ — quarantined (NOT deleted) files, moved 2026-09-26

Everything here was reachable by zero runtime code paths, was legacy-only, or was
a documented unsafe/stale script. Nothing was deleted: each file can be moved
back into the tree if a decision changes. The classification evidence is in
`lya-project-brain.md` (work-ledger entry for this date) and `LYA_ARCHITECTURE.md`
(the legacy/broken status map).

## legacy-skills/ — unreachable legacy skill modules
`main.py` (and the desktop brain) never calls `skills/allskills.py`; these
modules were only imported by it or by each other. Kept in the tree because they
ARE used at runtime: `skills/device.py`, `files.py`, `forge.py`, `governor.py`,
`guardian.py`, `harden.py`, `reminder.py`, `__init__.py`.

Moved here: allskills.py, autonomous.py, build_knowledge.py, cooking.py,
general.py, guiding.py, hacker.py, home.py, kali.py, learnhack.py, passwords.py,
phone.py, security_brain.py, skillbook.py, teaching.py, techno.py, trap.py,
_probe.py.

Restore: `Move-Item noneeded\legacy-skills\<name>.py skills\`

## legacy-audio/ — superseded speech renderer
- `synthesis.py` — old Kokoro-based renderer. Its only consumer was
  `test_synthesis.py` (also quarantined, in dead-tools/). The live desktop path
  uses `external-work` Piper via `desktop/setup_speech.py`; `audio/voice.py`
  was re-routed to that worker on 2026-09-26.
  NOTE: `audio/voice_auth.py` was NOT moved — `desktop/activation.py` and
  `web_server.py` still import it.

## legacy-ui/ — superseded browser HUD
- `jarvis_server.py` — legacy browser HUD per `LYA_ARCHITECTURE.md`
  (`ui/jarvis_server.py — legacy browser HUD`, "not called"). `ui/orb.py` and
  `ui/themes.py` remain in the tree because `main.py` imports them.

## dead-tools/ — zero-reference tools and stale suites
- `tools/test-local-model.py` — one-off local-model evaluation harness; its
  evaluation rounds are recorded in `review/local-model-*/`.
- `tools/check-biometric-stack.py` — readiness probe superseded by live
  device checks (see `review/2026-09-25-admin-activation-refresh/`).
- `tools/install-voice-models.py` — the pinned Piper models already live in
  `models/voice/` (hash-verified).
- `examples/extract_books.py` — one-off extraction example, zero references.
- `desktop/bake_crystal.py` — zero references anywhere in the tree.
- `test_synthesis.py` — stubs the moved `Renderer.audio` API; per the brain it
  has been failing standalone since the `speak()` re-route.
- `test_native_ui.py` — Tk-based UI suite that could never initialize its Tcl
  runtime here (recorded in the 2026-09-10 evidence table).

## unsafe-test-scripts/ — DO NOT RUN against the real store
Per the brain's evidence table and README warnings, these write to or corrupt
the real encrypted stores:
- crash_test.py, crash_test2.py, security_test.py, test_security_fixes.py

## stray-artifacts/ — junk that collected in the repo root
- `external-cmd-artifact.txt` (was a root file named `external`) — a 99-byte
  piece of shell error text ("'external' is not recognized..."), not code.
- `probe.txt` — one-off piper/edge-tts introspection notes (1.2 KB), referenced
  nowhere.

Nothing else was moved. Files intentionally KEPT despite looking legacy:
`audio/voice_auth.py` (imported by `desktop/activation.py` + `web_server.py`),
`vision/face_auth.py` (imported by `web_server.py`), `brain/knowledge.py`,
`brain/sync.py` (imported by `skills/reminder.py` + `cloud/lya_cloud.py`),
`brain/council.py` (imported by `brain/workflow.py`), all of `ui/` except
jarvis_server, all `cloud/` modules (active router/oracle path),
`review_checks.py` (documented review probe), the two SSH key files and
`oracle_known_hosts.local` (in use, never commit).
