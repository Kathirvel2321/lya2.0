# Selected-note recovery and private-routing evidence

Date: 2026-09-20. Local development only. No enrollment, private store inspection,
provider generation, deployment or cloud transfer was performed.

## Changes

- `storage/recovery.py`: versioned, authenticated selected-note archive under a
  separate random recovery key. Exact approval binds selection/key fingerprint
  and resolved database path; restore binds the archive digest. Active owner,
  finite session expiry, strict metadata, size/count limits and cancellation are
  enforced. Restore requires an empty owner profile and never imports authority.
- `storage/store.py`: read-only encrypted-store access for recovery checks;
  failed encrypted temporary writes clean up their own file. Failed replacement
  leaves the prior database intact.
- `security/policy.py`: owner-only backup/restore actions, default denial preserved.
- `brain/workflow.py`: literal True approval instead of truthiness. Personal
  inference selects the local client directly; the built-in loopback transport
  disables proxy inheritance and redirects. Unavailable local inference stops.
- `security/vault.py`: corrected Fernet algorithm and secure-deletion claims;
  cipher and existing key location unchanged.
- `LYA_STORAGE_SECURITY_PLAN.md`: lifetime table, ownership, threat boundaries,
  recovery contract, optional-tool decisions and ordered integration gates.
- `diagrams/17-storage-recovery.mmd`, `.svg`, `.png` and
  `diagrams/render_storage_recovery.py`: checked source and local companion overview.

## Checks actually run

| Command | Result |
| --- | --- |
| `check-storage-recovery.cmd` | PASS: 12 recovery + 33 brain + 3 approval = 48 checks |
| `.venv-ui/Scripts/python.exe -B test_registration.py` | PASS: 12 synthetic registration regressions |
| Mermaid skill `check diagrams/17-storage-recovery.mmd` | PASS: zero errors/warnings |
| `.venv-ui/Scripts/python.exe -B diagrams/render_storage_recovery.py` with Qt offscreen | SVG and PNG generated; visually inspected |
| `git diff --check` | PASS; existing CRLF normalization warnings only |

Recovery tests cover a fresh local encryption key, remapped relationship IDs,
preserved revision/deadline, encrypted archive contents, wrong key, tampering,
authenticated invalid schemas, protected/cross-person selections, expiry skip,
existing-note protection, default denial, nonliteral approval, session change,
profile revocation, cancellation, partial encryption failure, atomic replacement
failure and read-only write denial. All use temporary files and disposable keys.
The registration regression suite uses a temporary DPAPI key and synthetic
vectors; it does not collect real biometric samples.

The new personal-routing regression gives cloud and local clients separate call
collectors and checks zero cloud calls even after local failure. Transport checks
mock the opener, inspect empty proxy settings, exercise redirect rejection and
reject an external endpoint before opening it. These are isolated contract tests,
not a live packet-capture proof or an independent penetration test.

## Limits and next step

T05 and T10 remain partial. This is a library returning archive bytes, not a
finished desktop backup feature. The UI, approved file-write boundary, safe key
custody, clean-device restoration, key rotation and Drive transport remain pending.
Enrollment is still deferred; the desktop remains a guest. Existing runtime keys
and stores were not migrated. Files, credentials and biometric identity cannot be
recovered from this selected-note format.

Fernet/DPAPI do not isolate secrets from malware in the same unlocked Windows
account. Trusted callbacks are an internal boundary, not a sandbox; legacy Python
modules are not all covered by the reviewed Brain route. Offline archives retain
deleted note history until those archives are deleted; a holder of the recovery
key can decrypt expired content outside LYA.

No new dependency was needed. The public-document research fetch was blocked by
an automatic approval-review usage limit and was not bypassed. External-tool
recommendations are conservatively scoped; Obsidian-specific claims need current
official verification before integration.

Next development unit: recovery UI/file handling and key-custody preview using
synthetic profiles until real trusted session setup is requested and verified.
Then perform a recovery drill before enabling any remote archive transport.
Rollback: do not invoke the new recovery API; preserve existing live database/key.
Do not roll back literal-approval/private-routing protections or restore a backup
over the sole live store. No repository-wide reset is appropriate in this dirty tree.
