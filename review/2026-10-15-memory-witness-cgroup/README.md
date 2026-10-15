# Temporary witness service budgets — 15 October 2026

The owner requested the next memory-foundation step and asked to use REA. Applied the installed REA skill's routing guidance: this is readable Python source with available fixtures, so ordinary source/test tools provide the relevant evidence. No REA target analysis, binary decompilation or runtime attachment was performed or needed. REA configuration and providers were not changed.

Added [five Linux qualification cases](../../test_memory_witness_cgroup.py) and [a reviewed runner](check.py). They reuse the existing process/TLS witness fixtures inside unique **temporary systemd user services**. No production module, existing test, installed service, global OS/WSL setting, dependency, accepted assistant interface or real store changed. Unit names are generated locally; generated fake protocol keys travel only over the child's stdin, not command arguments, service properties or retained results. Certificates and stores remain disposable fixtures. No sudo is used.

## Candidate policy

| Property | Verified setting and meaning |
| --- | --- |
| `MemoryMax` | 256 MiB across the service cgroup, including its descendants and charged memory; not a pure RSS limit. |
| `MemorySwapMax` | Zero; no cgroup swap allowance. |
| `CPUQuota` / `CPUQuotaPeriodSec` | 25% of one CPU / 100 ms; kernel readback `25000 100000`. Rate control replaces the finite worker's ten-second lifetime CPU cap for this separate lab profile. |
| `TasksMax` | 16 processes/threads across the service cgroup. Does not apply a per-user task limit. |
| `OOMPolicy=kill` | Verified `memory.oom.group=1`; an OOM event terminates this service group. |
| `LimitNOFILE` / `LimitCORE` / `LimitFSIZE` | 64 descriptors per process, core dumps disabled, 8 MiB per regular file. Worker verifies soft/hard readback and no lifetime CPU limit before opening the witness. |
| `KillMode` / `TimeoutStopSec` | `control-group` / five seconds; terminate remaining owned descendants when stopping the service. |
| `RuntimeMaxSec` | 60 seconds, a safety bound for each finite lab service. Not a selected persistent-service lifetime or production supervisor. |

The existing Ubuntu user manager and cgroup controllers support this profile. These controls are selected only by the new test helper. Existing finite workers retain their prior explicit `RLIMIT` profile; default witness callers remain unchanged. This qualification does not install or enable a service, select an independent host or provide automatic restart/backoff.

## Checks and results

**All 93 selected assistant-executed Ubuntu cases pass**, zero failures/errors/skips: the five new cgroup cases plus the preceding 88 resource/admission/process/TLS/retirement/capacity/protocol/coordinator cases. **All 20 selected Windows cases pass**, zero failures/errors/skips: the existing platform guard and request-budget/process/TLS cases. Windows does not qualify Linux cgroups; counts overlap and are not added. The corrected focused five-case Linux run also passes and is preserved separately.

The new cases verify effective cgroup/rlimit settings, 40 signed observe/prepare/finish/retire rounds with zero retained receipts, a synthetic descendant removed on shutdown, kernel CPU throttling during a transaction, rejection of excess threads followed by healthy service, three stalled-connection waves with recovery, and a real cgroup memory kill inside tentative prepare followed by hot-journal rollback and successful retry in a fresh bounded service.

The memory fault allocates only inside the owned service with its 256 MiB cap; neither the runner nor unrelated processes receive that limit. The failed transaction has generation zero, no reservation and no receipt after reopening. Task rejection and CPU-throttle counters come from kernel cgroup files. A reply deadline may expire while CPU-throttled work later commits; the CPU case verifies a signed observation of that durable reservation instead of assuming a timed-out request rolled back.

All three healthy attempts made during a stalled request timed out in the focused run; one of three timed out in the full run. All three immediate recovery observations succeeded in each run after the stalled request cleared. Timing varies with scheduling. This proves bounded recovery in this workload, **not fairness or continuous availability under a hostile connection stream**. No server concurrency/admission behavior was changed to hide that limit.

Evidence: [focused Linux result and metrics](focused-wsl-validation.json), [focused Linux log](focused-wsl-tests.txt), [current Linux result](wsl-validation.json), [current Linux log](wsl-tests.txt), [Windows result](validation.json), [Windows log](tests.txt), [19-source manifest](lab-source-manifest.json), [allowlisted lab refresh](wsl-refresh-validation.json), [selected accepted-source preservation](accepted-source-preservation.json), [static and cleanup checks](static-validation.json). The runner checks all 19 reviewed source hashes before and after execution. Its own digest is recorded with each result. Only the new test was added/refreshed in the existing Ubuntu lab, preserving a numbered backup of its first revision. The owner need not run or paste these completed checks.

The initial Linux fixture used an unsupported `MemoryOOMGroup` property, so all five cases refused startup. Preserved [initial result](initial-wsl-validation.json), [initial log](initial-wsl-tests.txt) and [initial source manifest](initial-source-manifest.json) distinguish that failed attempt from corrected qualification. A focused temporary probe verified supported `OOMPolicy=kill` and effective group/rlimit settings before correction. The preceding initial 20-case Windows pass is retained separately in [initial Windows result](initial-windows-validation.json) and [initial Windows log](initial-windows-tests.txt).

[Post-run verification](wsl-post-run-validation.json) confirms all 19 lab source hashes still match, no test-owned service units remain, and no lab fixture directory remains. Each managed-service context also verifies its cgroup is absent or unpopulated after cleanup.

The Linux runner uses the existing verified lab cwd/interpreter; its default selection adds these five cases to the preceding 88. Windows selects only the existing request-budget/process/TLS cases and platform guard, without claiming Linux cgroup enforcement:

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-15-memory-witness-cgroup/check.py
wsl.exe --distribution Ubuntu-24.04 --cd /home/kathirvel/lya-lab --exec .venv/bin/python /mnt/c/Users/kathirvel/Downloads/lya-main/lya-main/review/2026-10-15-memory-witness-cgroup/check.py
```

## Limits and next step

This is a bounded service-budget qualification, not a long soak, performance guarantee, persistent supervisor, production deployment or independent-host recovery test. CPU rate, charged memory and task-tree budgets are now exercised together; aggregate filesystem/journal/WAL quotas remain unresolved. The eight-MiB per-file cap and four-MiB logical database page cap do not bound all disk usage. No mount/quota configuration or global limits were changed.

Next choose a concrete independent free witness placement with aggregate storage limits, restricted identity/storage, supervision/restart policy and certificate/key custody, then qualify that environment before a separate production/private pilot request. Oracle/ARM64 execution of this profile, whole-witness rollback protection, real custody and device integration remain pending. No real key, owner enrollment, sensor collection, external transfer, paid resource, deployment, commit or push occurred.
