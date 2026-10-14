# Encrypted memory on Oracle Linux ARM64 — 13 October 2026

The owner requested continuation and explicitly confirmed in this chat that the
existing instance is covered by the Always Free allowance. This is owner-supplied
confirmation, **not an independent tenancy/billing API verification**. No resource,
shape, subscription or production service was created or changed.

## Result and scope

**Eight portable fake-data checks pass on Linux aarch64 / CPython 3.12**, zero
failures, errors or skips. [Validation](validation.json), [test log](tests.txt).
The actual SQLCipher runtime reports **4.12.0 community / SQLite 3.51.1**.
The 1,000-record case restores 940 retained records and 60 deletion markers,
with zero active bindings and zero resumed jobs before explicit activation.

The runner transfers only an allowlisted copy of public prototype source and
tests over the existing pinned SSH connection. Generated fake keys and records
are created inside the test process. No real owner identity, vault, credential,
provider configuration or memory record is read or transferred. Direct fake
`Context`/`PublicTurn` objects provide test authority; these checks do not qualify
native Windows or phone authentication.

`sqlcipher3==0.6.3` is unpacked only inside a mode-700 temporary directory under
`/tmp`, outside the system and mobile environments. No pip, apt, daemon, account
or service installation runs. The temporary directory is removed after the run;
the validation records successful cleanup and unchanged hashes for five existing
mobile source files plus unchanged active state and memory cap. System-package
and mobile-runtime dependencies were not modified.

The driver wheel is the published CPython 3.12 Linux ARM64 artifact:

```text
sqlcipher3-0.6.3-cp312-cp312-manylinux_2_28_aarch64.whl
sha256:96b89544616cb71284c89bedc5519c42ca34027016638678ba607f7189ead248
```

Its digest was checked against [official PyPI release metadata](https://pypi.org/project/sqlcipher3/0.6.3/#files)
and verified again before extracting or executing the wheel. Only a bounded
binary wheel is accepted; there is no source build or plaintext fallback.
Agent Reach tools were unavailable locally, so official-source web fallback was
used. No owner data was sent to the package source.

## Checks

[test_qualification.py](test_qualification.py) adds portable storage checks without
importing Windows enrollment/vault fixtures:

1. Active encryption, authenticated pages, no plaintext header, integrity, wrong
   keys and rejection of a plaintext substitute driver.
2. Unicode, correction revisions, retry receipts, owner isolation, forgetting
   and expiry.
3. Ciphertext in an active rollback journal, WAL and encrypted restore staging;
   quarantined restoration with zero bindings/jobs.
4. Corruption/truncation rejection without damaging the original store.
5. Cancellation and actual database-full rollback.
6. Old-writer rejection, exact-anchor conflict, failed publication rollback and
   explicit verified-fake-owner recovery activation.
7. Actual child-process death before commit and lost reply after commit, followed
   by a safe retry. Generated key bytes travel on stdin, not command-line arguments.
8. The 1,000-record corpus and recovery integrity/foreign-key checks.

Seven non-corpus checks also passed in a local Windows precheck before staging.
The preceding 114-check suite was not rerun; its sources and dated evidence are
preserved. [Static validation](static-validation.json) records parsing, unchanged
prior source hashes, exact transferred source digests, local links and cleanup.

The bounded test child had a 512 MiB virtual-address limit, 90 CPU-second limit,
128 MiB per-file limit, disabled core dumps and a 120-second wall timeout. The
observed child maximum RSS was about 45.3 MiB. These are qualification bounds and
one process observation, not production admission, retention or concurrency
budgets. A temporary Python search path isolates the driver; this is not an OS
sandbox against malicious code or a dedicated restricted service account.

## Reproduction and next step

[check.py](check.py) requires both explicit staging and owner-confirmed free
eligibility flags. It refuses to overwrite existing evidence:

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-13-memory-linux/check.py --stage-fake-only --owner-confirmed-free
```

[remote_stage.py](remote_stage.py) verifies target architecture, source allowlist,
digests, wheel archive paths and disk headroom before tests. Expected native
decryption/HMAC diagnostics from negative cases are withheld from the published
log. On connection failure the runner makes no success/cleanup claim; normal
completion explicitly verifies that its temporary directory is gone.

This closes a **bounded encrypted-driver/platform qualification slice**, not
production memory deployment or the full recovery gate. Existing production
callers remain disconnected and legacy raw calls remain outside writer fencing.

Next select protected storage/recovery key custody and an independently trusted
latest-state policy. Both must survive the selected host loss/rollback; keeping
the only catalogue, backups and keys on the same Oracle instance is insufficient.
Then qualify a restricted service, disk/admission/retention limits, clean-host
recovery and real phone/laptop acceptance before valuable shared records.

No real key creation, enrollment, private migration, model/provider/UI/voice/startup
change, production activation, paid resource, commit or push.
