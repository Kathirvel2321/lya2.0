# Verified encrypted recovery-artifact transport — 17 October 2026

The owner requested the next memory/recovery foundation step after the quota/failure lab. Added isolated [recovery-pack helpers](../../brain/memory_recovery_pack.py), [ten fake-data cases](../../test_memory_recovery_pack.py), [a reviewed runner](check.py) and [the operator/trust guide](../../docs/guides/LYA_MEMORY_RECOVERY_PACK.md). No existing memory implementation, client, authority, witness, voice/hearing, research, automation, storage configuration or deployment was changed.

## Implementation

Reuses the existing encrypted backup/checkpoint formats, sealed key capsule, bounded schema validation, SQLCipher restore and atomic file publication. A pack contains exactly `backup.enc`, `checkpoint.enc` and `keys.enc`, with an eight-MiB combined ciphertext limit. No archive format, provider adapter, plaintext manifest, credential persistence or recursive copier was introduced.

Frozen `RecoveryPins` hold the caller-supplied independent checkpoint/writer observation, capsule digest and acknowledged backup digest. Pins and unlock keys stay outside the pack. Staging verifies a complete matching acknowledged snapshot, copies only the three fixed encrypted files to a new directory, and revalidates the destination before acknowledging transport. Inspection/restoration reject missing/extra files, stale or replaced contents against fresh pins, wrong unlock keys, incomplete snapshots and size violations. Existing output paths are preserved. Cancellation/interruption may leave an unacknowledged partial directory, never an implicit overwrite or success.

Restore always uses the capsule's storage key and the existing encrypted restore path, producing a quarantined database with zero active bindings and zero resumed jobs. This is record-only transport/reconstruction. Protected authority catalogue/owner mappings, writer fencing/reactivation and a separately surviving latest-state witness remain necessary for full authority recovery; they are not reconstructed from this pack.

The helper validates the pins provided by its trusted caller. It does not query a live witness or detect rollback of both the pack and its supplied trust inputs. Copying a pin from the same untrusted backup would defeat freshness protection. The guide records what must survive and remain independently trusted.

## Checks

**All 129 selected assistant-executed Ubuntu cases pass**, zero failures/errors/skips: ten new cases, twelve existing custody cases, eight portable encrypted-storage cases and the preceding 99 memory regressions. **All 51 selected Windows cases pass**, zero failures/errors/skips: the same thirty plus the preceding 21 guard/admission/process/TLS cases. Windows does not qualify Linux namespaces/cgroups. Counts overlap prior selections and are not added. The focused ten-case Ubuntu pass is preserved separately.

New cases cover the exact three-file encrypted layout and no plaintext keys/records, fresh-process restore after deleting the generated source/catalogue/local witness, exact flags, missing/corrupted/extra artifacts, stale packs against fresh independent pins, wrong unlock/missing pins/replaced capsule, authenticated but incomplete old snapshots, interrupted transfers/no overwrite, cancellation, combined byte admission and existing restore-output preservation.

The child drill uses independently supplied fake trust/key inputs over stdin, with no secret in command arguments or retained results. It reconstructs without the old source path or catalogue. A correction survives, forgotten/expired records are suppressed in records/search, old bindings are denied, the database remains encrypted, active bindings are zero and resumed jobs are zero. Independent identity/authority activation is deliberately absent. Source and destination folders remain on the same physical host; a fresh process is not a fresh machine or independent failure domain.

Artifacts: [focused Linux validation](wsl-focused.json), [focused Linux log](wsl-focused.txt), [full Linux validation](wsl-validation.json), [full Linux log](wsl-validation.txt), [Windows validation](windows-validation.json), [Windows log](windows-validation.txt), [23-source manifest](lab-source-manifest.json), [allowlisted lab verification/refresh](wsl-refresh-validation.json), [post-run cleanup/source verification](wsl-post-run-validation.json), [accepted-source preservation](accepted-source-preservation.json), [static checks](static-validation.json).

All 20 preceding selected lab hashes were verified. Only the new helper/test were added; the existing custody test already matched the reviewed workspace. Hash comparison normalizes CRLF to LF only. The runner validates all 23 source contents before and after execution, records its own digest and exact case IDs, and refuses to overwrite prior evidence. Wrong-key SQLCipher regression probes can emit expected authentication diagnostics; only the final unittest results determine their pass/fail state.

Post-run checks find zero test service units and zero pack/disk fixture directories, with all 23 lab hashes still matching. The accepted runtime and existing recovery/custody/repository/authority sources match HEAD. No manual owner run or pasted output is needed for the completed checks.

The default Ubuntu selection adds these ten cases, twelve existing custody cases and eight portable encrypted-storage cases to the preceding 99 memory checks. Windows selects the same thirty plus the preceding 21 platform/admission/process/TLS cases; actual cgroup/namespace quota enforcement remains Linux-only.

```powershell
.\.venv-ui\Scripts\python.exe -B review/2026-10-17-memory-recovery-pack/check.py --name windows-recheck
wsl.exe --distribution Ubuntu-24.04 --cd /home/kathirvel/lya-lab --exec .venv/bin/python -B /mnt/c/Users/kathirvel/Downloads/lya-main/lya-main/review/2026-10-17-memory-recovery-pack/check.py --name wsl-recheck
```

## Limits and next step

Explicit synthetic/approval flags are mandatory. There is no production caller or scheduled transfer, selected remote destination, real key/password-manager setup, physical cross-host durability, directory-fsync/power-loss guarantee, source-to-witness atomic remote publication, independent rollback-resistant trust or complete authority rebuild. Per-file atomic publication and final verification do not make the entire directory a crash-durable transaction. Protected local input/destination ownership and OS resource limits remain deployment requirements.

Next choose the independent witness/backup destination, verify its free allowance/failure-domain policy, select protected key custody and catalogue protection, then qualify a real host/storage adapter using fake artifacts with download/readback and independent restore. No real store, private data, enrollment, account, paid resource, dependency, system setting, external transmission, deployment, commit or push occurred. Face anti-spoofing remains deferred.
