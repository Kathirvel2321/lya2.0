# Memory witness disk-full and recovery qualification — 17 October 2026

The owner selected the memory/recovery foundation as the next brain track and deferred face anti-spoofing. Added [isolated disk checks](../../test_memory_witness_disk.py) and [a reviewed runner](check.py). No production source, existing fixture, accepted desktop/phone behavior, real store, dependency or installed service changed.

## What is enforced

Each Linux probe runs in a unique temporary user service with the preceding qualified cgroup policy: 256 MiB charged memory, no swap, 25% of one CPU, 16 tasks, descriptor/core/per-file limits, group cleanup and a 60-second lab lifetime. Kernel cgroup readback is checked inside the probe. An unprivileged user/mount/PID namespace then mounts **a private eight-MiB tmpfs with 128 file entries** at an empty owned fixture directory. `nosuid,nodev,noexec` are set; mount propagation is private. No sudo, host mount, loop device, system quota setting or persistent unit is used.

The mount remains alive across witness-child restarts within a probe, so trust and committed state survive those restarts. Namespace exit destroys the temporary filesystem. Its byte/inode accounting covers the witness database, its journal and other files on that volume; SQLite temporary-file placement is directed there inside the probe. Certificates, fake encrypted canonical source/catalogue, test logs and the fixture coordinator are outside that volume. This is not a quota for every file any process could write.

Filler files are explicitly named disposable fixtures. Writing allocated bytes or creating zero-length files reaches the kernel's actual `ENOSPC` error, rather than mocking SQLite or raising an invented storage exception. Each filler byte file is at most one MiB, below the separate eight-MiB per-file limit. Tests verify zero available blocks or zero available file entries at the failure boundary. Only these filler files are released before retry; no trust database or real data is recreated to recover capacity.

This is **volatile quota/failure qualification**, not a durable-storage implementation or physical disk/power-loss test. A production volume needs separately qualified persistent storage, quota/temporary-file placement, service identity and recovery custody. tmpfs does not provide reboot or host-loss survival.

## Cases and evidence

**All 99 selected assistant-executed Ubuntu cases pass**, zero failures/errors/skips: six new cases plus the preceding 93 memory regressions. **All 21 selected Windows cases pass**, zero failures/errors/skips: the new platform/action guard plus the previous 20 platform/admission/process/TLS cases. Windows does not qualify Linux quotas; counts overlap and are not added. The focused six-case Linux pass is preserved separately. One new case is the platform/action guard; the other five cover six private-filesystem scenarios:

1. Full byte capacity and exhausted file entries both prevent prepare acknowledgement and leave no reservation, generation advance or receipt after restart. Exact prepare retry succeeds after freeing capacity.
2. Full storage during finish preserves the earlier durable reservation and its prepare receipt. Restart and exact finish retry succeed after freeing capacity.
3. Failed retirement cannot advance the retirement floor or discard the receipts needed for recovery. Explicit retry retires only after space is available.
4. A finish commits, the witness volume fills, and the owned child exits before reply delivery. Fresh startup sees the committed head; exact retry returns that outcome and retirement still works.
5. The fake encrypted canonical source commits, then the separate witness volume fills before its finish transaction. The caller receives no success. Fresh startup remains blocked pending approved reconciliation; reconciliation verifies the source, finishes the reservation, returns no reconstructed grants/result, and permits idempotent caller retry without another source mutation.

The finite quota worker reuses the existing signed TLS/process fixtures. Disposable keys are generated normally and passed to witness children over stdin; they do not appear in service properties, process arguments or retained results. No network destination beyond loopback is used. Actual disk-quota cases require Linux namespaces, a working user manager and mount support; absent support fails rather than silently substituting an unbounded run. Windows selects the safe platform guard and existing request-budget/process/TLS regressions, without claiming Linux enforcement.

Artifacts: [focused Linux result/metrics](wsl-focused.json), [focused Linux log](wsl-focused.txt), [full Linux result](wsl-validation.json), [full Linux log](wsl-validation.txt), [Windows result](windows-validation.json), [Windows log](windows-validation.txt), [20-source manifest](lab-source-manifest.json), [allowlisted lab refresh](wsl-refresh-validation.json), [post-run cleanup verification](wsl-post-run-validation.json), [accepted-source preservation](accepted-source-preservation.json), [static/source-preservation checks](static-validation.json). Post-run checks verify zero remaining test units/fixture directories and all 20 lab hashes unchanged. No manual owner command or pasted output is needed for these completed runs.

All 19 preceding lab sources were verified against the prior cgroup evidence. Only the new disk test was added to the lab. Workspace hashes normalize CRLF to LF because the committed Windows checkout uses CRLF while prior Linux evidence uses LF; no other source normalization is applied. The runner verifies all 20 reviewed source contents before and after each run and records its own digest and exact case IDs. Prior evidence is preserved, and the runner refuses to overwrite an existing report/log name.

```powershell
.\.venv-ui\Scripts\python.exe -B review/2026-10-17-memory-disk/check.py --name windows-recheck
wsl.exe --distribution Ubuntu-24.04 --cd /home/kathirvel/lya-lab --exec .venv/bin/python -B /mnt/c/Users/kathirvel/Downloads/lya-main/lya-main/review/2026-10-17-memory-disk/check.py --name wsl-recheck
```

## Remaining work

These bounded tests add byte/inode quota failures to the existing TLS, process, cgroup and recovery evidence. They do not qualify a durable target volume, real disk firmware/cache failure, fsync correctness under power loss, backup/key survival, whole-witness rollback protection, independent free hosting or real-device/private memory integration. No automatic deletion, quota reclamation policy, persistent supervisor, private data placement, production key, cloud service or deployment was added. Face anti-spoofing remains deferred.

Next select the concrete independent witness/backup placement and protected key-custody path, including a durable quota and supervision policy, then reproduce the relevant failure/recovery checks in that environment with fake data before a separate private pilot. Existing same-host prototypes and successful local tests do not establish laptop-off or independent-host recovery.

Later 17 October follow-up: [verified encrypted recovery-artifact transport](../2026-10-17-memory-recovery-pack/README.md) prepares the exact three encrypted files, requires separately trusted pins/unlock material and qualifies quarantined record reconstruction in a fresh process without the original source/catalogue/witness. No real destination or full authority rebuild is supplied by that helper.
