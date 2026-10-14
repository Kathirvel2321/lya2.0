# LYA

A personal assistant under development, with a native Windows crystal interface and a lightweight paired phone client.

Read [the project brain](lya-project-brain.md) first for current status and limitations, then [owner requirements](LYA_VISION.md) and [the documentation index](docs/README.md). Older explanations and retired implementations are preserved in [archive](archive/README.md).

## Current entry points

| Area | Entry point |
| --- | --- |
| Normal desktop | Existing `LYA.lnk`, `launch-lya.cmd` or `launch-lya.ps1`; [desktop setup/guide](desktop/README.md) |
| Desktop implementation | `tools/start_nvidia_lya.py` → `desktop/app.py` / `desktop/experience.py` → `brain/workflow.py` |
| Mobile implementation | `cloud/mobile.py`, `cloud/mobile.html`; local source and deployed page are separate states |
| Voice | `audio/voice.py`, configured hearing adapters, `desktop/setup_speech.py` and the used `external-work/alya_voice` stack |
| Storage and authority | `storage/`, `security/`, `brain/notes.py`; existing protected locations/settings remain unchanged |
| Tests/tools | Root `test_*.py`, `desktop/check_*.py`, supported `tools/`, current dated `review/` helpers |
| Older compatibility interfaces | `main.py`, `web_server.py` and `ui/` remain because tests/shared code still reference them |

The isolated `brain/conversation.py`, `brain/memory_prototype.py` and `brain/memory_recovery.py` are retained development work, not a deployed shared-memory system. The `lya-external-work` and anti-spoofing submodule checkouts remain in place. Do not treat “external”, “legacy”, “failed test” or an old date as sufficient reason to remove a file.

## Development boundaries

Preserve accepted voice/hearing, interface choices, authentication and startup. Read `AGENTS.md` and test sources before running checks; use fake credentials and disposable stores. Enrollment remains deferred unless explicitly requested. No private-data migration, new transmission or deployment is authorized merely by a document.

`archive/` is reference only: do not execute its scripts, add it to import paths or include it in test/build discovery. Its [manifest](review/2026-10-12-project-organization/move-manifest.json) records original paths and hashes. The [full earlier brain](archive/history/continuity/project-brain-through-2026-10-12.md) and [previous README](archive/history/documentation/README-before-organization.md) preserve detailed historical explanations; their instructions and integration claims may be obsolete.

The latest mobile history/correction work is local and tested with synthetic replies. Live iPhone voice/keyboard behavior, publication of that change, fully integrated cross-device memory and independent recovery remain unfinished. See the current brain for dated evidence rather than assuming a component test proves the whole experience.
