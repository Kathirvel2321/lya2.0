# Project organization — 2026-10-12

Owner requested a separate structured location for unused/old/failed implementation and lengthy historical explanations. The unfinished final sentence requested nothing additional. This task organizes the repository; it does not change product behavior or remove features.

424 inventoried tracked files relocated:

- 34 previously quarantined files from `noneeded/`, preserving their original categories and the earlier manifest; unsafe store-writing tests have their own `archive/unsafe-tests/` folder.
- Three superseded maintenance/review scripts (`store_key.py`, `review_checks.py`, `review/review_20260913.py`) and seven unused upstream voice-evaluation files moved out of the working source tree.
- 353 files from 75 historical review/evaluation folders, 13 files from three superseded desktop QA folders, and the old root test summary moved into historical evidence.
- Eleven root explanation documents were relocated: ten maintained documents into `docs/architecture`, `docs/plans` and `docs/guides`, and the dated build-progress report into the archive.
- The previous full project brain and root README were moved intact into the archive. Short current entry points link to the detailed history and maintained documentation.

See [archive](../../archive/README.md), [docs](../../docs/README.md) and [move-manifest.json](move-manifest.json). The manifest records every original/destination path and original SHA-256. Archived file bytes are unchanged, including the full previous ledger. Maintained Markdown links and source/evidence references were adjusted to the new locations. Root/archive AGENTS clarify that archived scripts are reference only and stay outside normal execution/import/test discovery. `pytest.ini` explicitly ignores `archive`; default unittest discovery already skips that non-package directory.

Kept deliberately: all accepted runtime modules, launchers, root regression suites, current mobile source and helpers, new conversation/memory/recovery prototypes, actual desktop voice implementation in `external-work`, and referenced legacy compatibility/shared modules. The two modified submodule checkouts were not changed. Root foundation/rebuild documents remain because the actual desktop reader allows those exact filenames. Two older review folders remain because current helpers reference their fixtures/output paths. Current `desktop/qa` generators/output locations remain.

Only tracked files were selected for relocation. Ignored/untracked local data and private or generated leftovers in former review directories stay in place; credentials, protected stores, model weights, environments, recordings and provider configuration were not read or moved. Empty obsolete source directories are removed only after checking their absolute paths and confirming they contain nothing. No recursive deletion, restore, import, execution or deployment of archived code.

Checks are recorded in `validation.json`, `launcher-validation.txt` and `mobile-client-validation.json`. `verify.py` compares retained source/asset/config-example hashes against the pre-move baseline, archived bytes against original hashes, parses retained Python source, checks maintained Markdown for newly broken links, exercises the real desktop document-reader function in isolation, and checks that the archive is not a package that normal unittest discovery traverses. These are dated checks: future intentional source edits will require a new baseline rather than blindly rerunning old hash assertions.

Final results: all 414 archived originals match their hashes, all 480 retained baseline files match, 232 active Python files parse, 61 maintained/index Markdown files have no newly broken local links, all four desktop document-reader entries work and its allowlist remains closed. Nine isolated launcher tests and 40 simulated mobile checks pass. Archive is excluded from pytest and default unittest recursion; `git diff --check` passes.

The fake launcher runner patches the provider-settings loader so no real `.env` key is read, then runs the existing launcher tests offscreen with fake keys and workspace-only temporary paths. An initial sandbox temporary-directory permissions failure was resolved by keeping fixtures inside the workspace, without changing product/test source. Mobile validation uses simulated DOM/media/network only. No real microphone/camera/account/provider/service access, enrollment, new dependency, deployment, commit or push.

The complete repository/hardware/live service suite is not claimed. Existing out-of-scope route-contract drift remains recorded in the current brain. The organization did not turn isolated prototypes into integrations or classify working features as failures.

Recovery: use the manifest to find a selected file's original location, check current dependencies and restore/requalify that file before reusing it. The one-time `organize.py` refuses to plan over an existing archive. Do not rerun historical release/setup/unsafe scripts from their new archive paths; their root calculations and old assumptions intentionally remain dated evidence.
