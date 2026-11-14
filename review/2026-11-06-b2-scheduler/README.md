# B2 Nightly Backup Scheduler — Implementation and Qualification

Prepared 2026-11-06. This is a Windows Task Scheduler integration, not a live
production job, real credential creation, or deployment.

## What was built

**`tools/schedule_b2_backup.py`** — Minimal nightly-backup runner for Windows
Task Scheduler. Ponytail approach: uses only stdlib + existing B2 worker;
no new dependencies.

| Flag | Purpose |
|---|---|
| `--setup` | Interactive wizard: writes a public-only config (paths + bucket meta). No secrets stored. |
| `--register` | Registers `LYA_B2_NightlyBackup` in Windows Task Scheduler via `schtasks /Create`. Requires an admin shell. |
| `--unregister` | Removes the task. |
| `--status` | Prints safe Task Scheduler fields (TaskName, Status, run times, schedule type). |
| `--run` | Called nightly by Task Scheduler. Loads DPAPI credential → reads pins from latest-state store → calls `backup_with_credential` → writes a dated receipt. |
| `--dry-run` | Smoke-tests config and paths without real B2 access. |

### Security properties

- Config file contains only paths and bucket metadata — **no secrets**.
- Credential is loaded from the DPAPI-protected file at run time; not cached between runs.
- Logs redact any string ≥ 20 alphanumeric chars (potential token/key-like values).
- Receipt-name collisions (same day) return exit 0 (idempotent); no overwrite.
- Exit code non-zero on any real error → Task Scheduler retries next night.

**`test_qualification.py`** — Restored to workspace root (was in `review/2026-10-13-memory-linux/`).
This unblocked `test_memory_b2_backup.py` and `test_memory_recovery_pack.py`.

## What was verified

| Check | Result |
|---|---|
| `test_schedule_b2_backup.py` — 23 cases, Windows, B2 mocked | **23/23 pass** |
| `test_memory_b2_backup.py` — 28 cases (mock subset), after `test_qualification.py` restored | **28/28 pass** |
| `desktop/check_experience.py` — regression | **47/47 pass** |

## Limits

- No real `schtasks` task was created or executed during testing (subprocess mocked).
- The nightly run requires a valid DPAPI credential (created via `brain/memory_b2_credential.py --setup`), which the owner must provision separately.
- The `--run` path's latest-state store read assumes `SyntheticRecoveryLatest` is the actual publication authority; it must be wired to the real authority when that is activated.
- Independent Oracle Linux witness, real key custody, and production activation remain pending.

## Owner activation steps (when ready)

1. Run `python tools/memory_b2_credential.py <path>` from an interactive terminal to create/refresh the DPAPI credential.
2. Run `python tools/schedule_b2_backup.py --setup` to write the public config.
3. Open an **admin PowerShell** and run `python tools/schedule_b2_backup.py --register`.
4. Verify: `python tools/schedule_b2_backup.py --status`.
5. Smoke-test: `python tools/schedule_b2_backup.py --dry-run`.
