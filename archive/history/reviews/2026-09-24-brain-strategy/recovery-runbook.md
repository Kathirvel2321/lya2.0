# Encrypted LYA store recovery — operator runbook (2026-09-24)

Status: commands implemented and tested with disposable fake DPAPI keys and fake
encrypted stores. No real owner bundle has been made or verified. A folder on this
laptop is not an off-device backup.

The bundle contains the current DPAPI-unwrapped vault key protected by a new
passphrase, direct `*.lya` files in the project root, `security/`, `brain/` and
`data/`, and direct `*.enc` files in `%LOCALAPPDATA%\LYA` and its `vault/`
subfolder (or under `LYA_DATA_DIR`). Each candidate must authenticate with that
same key. File names and source paths are in an encrypted manifest; the stored
files use numbered names. The bundle does not include `.env`, plaintext media,
model files, source code, other extensions or nested directories. It is not a
complete project or system backup. Individual encrypted files over 128 MiB are
rejected by the verifier.

Run from the repository root in PowerShell, replacing the sample destination
with a **new** folder whose parent already exists. The destination must be
outside the project and live runtime data. The tool prompts for a passphrase;
never put it on the command line or in `.env`.

```powershell
.\.venv-ui\Scripts\python.exe -B .\lya-external-work\lya-brain\recovery\vault_recovery.py bundle "D:\LYA-backup-2026-09-24"
.\.venv-ui\Scripts\python.exe -B .\lya-external-work\lya-brain\recovery\vault_recovery.py verify-bundle "D:\LYA-backup-2026-09-24"
```

After a successful verification, copy the entire bundle to a genuinely
independent location. Verify that copied folder too, using the same
`verify-bundle` command. Keep the passphrase separately from every copy.
Do not delete the current vault, current DPAPI key or source data during this
process. A local-only copy, a forgotten passphrase, or a bundle made before
new data was saved is insufficient for recovery.

On a replacement machine, use `verify-bundle` first. To inspect and stage the
encrypted files, extract to a **new empty** folder outside LYA's live paths:

```powershell
.\.venv-ui\Scripts\python.exe -B .\lya-external-work\lya-brain\recovery\vault_recovery.py extract-bundle "D:\LYA-backup-2026-09-24" "D:\LYA-staged-2026-09-24"
```

The staged `project/` and `runtime/` folders mirror the recorded source paths
but still contain ciphertext. `lya_recovery.key` is the passphrase-wrapped key.
`extract-bundle` never writes into the live project or runtime paths. Restoring
the key or replacing live data is a separate, deliberate operation after
reviewing the staged files. `restore` can authenticate one copied store before
writing the DPAPI key; replacing an existing different key requires
`--replace-existing` and `--encrypted-store`. Cross-Windows-account and full
application restore have **not** been tested, so do not treat this runbook as
proof of disaster recovery yet.

Isolated verification:
`test_vault_recovery.py` covers bundle creation, secret exclusion, encrypted
manifest, wrong passphrase, changed ciphertext, extraction, refusal to write
inside the live project and failure cleanup. The tests use only fake data.
