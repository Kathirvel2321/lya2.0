# T01 baseline evidence — 2026-09-16

Status: **complete** for `LYA_IMPLEMENTATION_CHECKLIST.md` scope.

This establishes a reproducible starting point. No provider request, sensor,
enrollment, deployment or real-store write was performed.

## Starting state

- Branch `main`, upstream `origin/main`; revision
  `8671be1a33fc7774b2c509693b0eafd425f124c8`.
- `.venv-ui/Scripts/python.exe`: Python 3.12.14.
- `launch-lya.cmd` SHA-256:
  `74817A606C74C6BB4792B36849218B5E77C31220670E6A2C38585BDE1A82DE71`.
- Existing orb, planning and ledger changes were preserved. Git warned that the
  sandbox could not read the user's global ignore file; configuration was unchanged.
- The IDE's external provider settings file was not read.

## Acceptance results

| Case | Result | Evidence |
| --- | --- | --- |
| T01-A native panel opens and accepts input | PASS | `launch-lya.cmd --reduced-motion` started the expected app. Native offscreen checks exercised keyboard input and dispatch. |
| T01-B guest status is truthful | PASS | `who am i` returned guest/unverified; admin color did not bind identity. |
| T01-C cancellation suppresses stale output | PASS | UI checks covered stale document and delayed brain results after close. |
| T01-D quit ends the tested process | PASS | Isolated Qt process called real `Desktop.quit` and returned 0. Real smoke-test processes were cleaned up and confirmed absent. |
| T01-E environment/results recorded | PASS | This report records revision, environment, commands, checks, limits and recovery. |

The real launcher established Windows startup/process behavior. Input and Quit
were exercised in the native Qt harness because visible-window clicks were not
automated in this environment.

## Checks

| Check | Result |
| --- | --- |
| `test_router.py` | 13 passed |
| `test_oracle.py` | 5 passed |
| `test_provider_setup.py` | 3 passed |
| `test_brain_workflow.py` | 20 passed |
| `desktop/check_ui.py` `InterfaceChecks`, offscreen with test fonts | 16 passed |
| Isolated Qt process calling `Desktop.quit` | Event loop returned 0 |

Automated baseline: **57 passed, 0 failed**. The visible launcher check is separate.
Suites were reviewed first and ran in separate processes with fake providers or
temporary encrypted storage.

## Ten baseline commands

| Command | Expected/current behavior |
| --- | --- |
| `help` | Shows native commands. |
| `status` | Shows system readiness. |
| `time` | Shows local time. |
| `show files` | Shows four allowlisted project documents. |
| `brain help` | Shows brain/memory syntax. |
| `who am i` | Reports guest/unverified. |
| `brain status` | Reports connected workflow and missing real integrations. |
| `brain demo` | Runs the labelled synthetic workflow. |
| `stop` | Closes panel and rejects stale results. |
| `sleep` | Clears working/session context and sleeps the UI when tray permits. |

A direct guest check used an unused fixture client, preventing network access.
`show memories` was blocked and `sleep` reported temporary context cleared.

## Limits and recovery

- This is not a fresh live-model quality, battery, voice, camera, iPhone or
  long-duration test.
- Visible startup was process-verified; input was checked through native offscreen Qt.
- Forced cleanup of the smoke-test instance is not evidence of the Quit UI path;
  the actual `Desktop.quit` method passed separately.
- Guest/private-memory limitations in the project brain remain.

No production configuration changed. Restart with `launch-lya.cmd`; use
`--original-art --reduced-motion` for the conservative visual mode. Do not revert
the dirty working tree to recover from this documentation task.

Next: T02 independent provider backup. Preserve private-route denial and do not
claim completion from synthetic failover alone.

## Owner verification helper

Added `check-t01.cmd` after the baseline run. It executes the same 57 safe offline
checks and stops at the first failing suite. It was run successfully on 2026-09-16.
See `LYA_TEST_GUIDE.md` and the validated Mermaid source plus directly viewable
companions at `diagrams/14-t01-working-and-test.{mmd,svg,png}`.
