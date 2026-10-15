# Finite Linux witness-worker resource profile — 15 October 2026

The owner requested the next memory-foundation step after request I/O/header budgets. Added [a Linux-only synthetic budget helper](../../brain/memory_witness_budget.py), an explicit opt-in hook in the existing [test worker](../../test_memory_witness_process.py), and [resource failure checks](../../test_memory_witness_resources.py). No production server/authority, accepted interface, startup choice, global OS/WSL setting or dependency changed.

## Candidate profile and startup contract

The profile applies irreversible soft/hard limits to **the calling owned finite lab child only**, after explicit `synthetic_only=True` and `approved=True`. Unsupported platforms fail before applying limits. Existing stricter soft/hard limits are preserved. The complete plan is built before applying it; a worker already mapped beyond its effective address-space ceiling is refused before any limit changes. Every set limit is read back; an application failure propagates and the worker must exit rather than continue partly bounded.

| Linux limit | Candidate ceiling | Meaning |
| --- | --- | --- |
| `RLIMIT_AS` | 256 MiB | Per-process virtual address space/allocation ceiling; distinct from RSS/cgroup memory accounting. |
| `RLIMIT_NOFILE` | 64 | Per-process file-descriptor ceiling. |
| `RLIMIT_FSIZE` | 8 MiB | Maximum size of each regular file; not total filesystem usage. |
| `RLIMIT_CORE` | 0 | Core dumps disabled after profile application. |
| `RLIMIT_CPU` | 10 CPU seconds | Cumulative CPU time over the finite process lifetime; not CPU rate or wall-clock duration. |

The test-only startup packet must explicitly contain `process_budget=True` to apply this candidate. Existing workers omit the field and retain their previous behavior. Limits are applied before witness validation, certificate loading and listener creation, but interpreter/test-module imports precede the opt-in entry; their startup peaks are not bounded by this helper. The address-space precheck prevents accepting a currently oversized worker. No parent runner or other user process receives these limits.

These values are a functionally qualified **finite lab-worker candidate**, not a selected continuous-service deployment profile. A ten-second lifetime CPU cap would eventually terminate a busy persistent service. Continuous CPU-rate control, supervision and aggregate resource accounting require a separate service policy.

## Checks and evidence

Five new cases verify explicit flags/platform refusal, actual limit readback plus healthy signed TLS operations under the profile, kernel allocation/descriptor refusal, signed-transaction rollback after memory/per-file errors, and CPU-limit termination followed by restart/rollback/retry. Additional assertions prove stricter inherited descriptor limits survive unchanged and an anonymous pre-reserved address-space mapping is rejected at startup without filling that memory. Fake files/protocol state are temporary; core/key/private-store material is not collected.

The memory/file fault cases execute inside a real signed prepare transaction after its tentative state change. Memory allocation fails or file growth reaches the kernel cap; the pending transaction rolls back and the service remains observable. Restart can retry the same request. The CPU case spins only in the owned witness child until its hard CPU ceiling terminates it; reopening recovers the uncommitted journal and permits retry. These are resource/process failure drills, not physical power-loss tests.

**All 88 selected Ubuntu cases pass**, zero failures/errors/skips: five resource cases plus the preceding 83 admission/process/TLS/retirement/capacity/protocol/coordinator cases. Only the new resource cases explicitly opt workers into the candidate; the other cases qualify unchanged defaults. The assistant executed this selection directly after source verification. **All 16 selected Windows cases also pass**, zero failures/errors/skips: the opt-in/platform contract plus the existing 15 process/TLS cases. Actual resource enforcement is Linux-only; no Windows limit qualification or all-88 Windows result is claimed. Counts overlap and are not added.

Artifacts: [Windows validation/source hashes](validation.json), [Windows log](tests.txt), [direct Ubuntu validation](wsl-validation.json), [Ubuntu log](wsl-tests.txt), [source manifest](lab-source-manifest.json), [lab refresh verification](wsl-refresh-validation.json), [post-run lab source verification](wsl-post-run-validation.json), [static/source preservation](static-validation.json). The initial five-case Linux qualification and 16-case Windows run are preserved in [initial Linux validation](initial-wsl-focused-validation.json), [initial Linux log](initial-wsl-focused-tests.txt), [initial Windows validation](initial-windows-validation.json) and [initial Windows log](initial-windows-tests.txt); final evidence adds the oversized-startup/stricter-limit assertions and reruns the selections.

Only the helper, resource test and opt-in test-worker hook were refreshed in the existing Ubuntu lab, preserving numbered backups. All 18 selected source/test files matched the reviewed workspace before the final run. No real store/configuration, archive content or dependency was synchronized. Fake certificates, stores/output files and test-owned children clean up through the reviewed fixtures.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-15-memory-witness-resources/check.py
```

The already-refreshed Ubuntu lab uses its existing interpreter:

```powershell
wsl.exe --distribution Ubuntu-24.04 --exec bash -lc 'cd ~/lya-lab && exec .venv/bin/python -m unittest -v test_memory_witness_resources test_memory_witness_admission test_memory_witness_process test_memory_witness_tls test_memory_receipt_retirement test_memory_witness_capacity test_memory_witness_service test_memory_network_authority'
```

The owner need not run or paste this completed selection.

## Limits and next step

This profile bounds one explicitly opted-in process after startup entry. It does not cap a process tree/user, forbid spawning children, impose continuous CPU rate, guarantee RSS or bound total filesystem/journal/WAL usage across files. `RLIMIT_NPROC` was not used because its per-user effect could affect unrelated processes. The per-file limit and existing 4 MiB logical witness database cap remain separate from an aggregate disk quota.

Later follow-up: [temporary user-service cgroup qualification](../2026-10-15-memory-witness-cgroup/README.md) exercises continuous CPU rate, service-group charged memory/task budgets, descendant cleanup and repeated TLS load without changing this finite-process profile. Aggregate disk quotas and production supervision remain open.

No long soak, hostile-load fairness, production throughput, continuous supervisor/restart policy, ARM64/Oracle run, independent-host recovery, whole-witness rollback protection, real custody or device/private pilot is established. Next qualify sustained admission and aggregate/continuous service budgets together with a concrete independent free placement; production activation and real keys remain separate scopes. No deployment, enrollment, paid resource, commit or push occurred.
