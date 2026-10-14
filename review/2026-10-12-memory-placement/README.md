# Oracle screening and fresh-process recovery — 12 October 2026

13 October follow-up: the owner confirmed the existing free allowance, and
[temporary Linux ARM64 encrypted qualification](../2026-10-13-memory-linux/README.md)
passes eight portable checks. The screen below preserves the earlier read-only
observation; no permanently installed system driver or production memory is claimed.

The owner requested the next memory step and explicitly selected a **read-only
assessment of the existing Oracle server**. This slice adds a repeatable screening
command and a local recovery drill. No production memory code changed.

## Observed Oracle screen

[oracle-screening.json](oracle-screening.json) records the bounded pinned-SSH
observation, including its UTC timestamp. The probe reads machine counters,
selected service properties and installed-module metadata. It runs as the
existing SSH account without sudo, package installation, service changes or
private-store/configuration reads on the server. Detailed operational counters
remain in ignored local `.private/`; the published report contains fixed flags.
No host address, account identifier, credential or private record is published.

| Screen | Result | Meaning |
| --- | --- | --- |
| Available host memory at least 256 MiB | Passed | A screening threshold only; not a reserved service budget or load qualification. |
| Free disk at least 1 GiB | Passed | A screening threshold only; snapshots, retention and worst-case admission remain unmeasured. |
| Existing mobile service active | Observed active | Preserve its separate service and current resource cap. No phone flow was exercised. |
| System Python cryptography module | Discoverable | Availability only; no recovery engine test on Oracle. |
| System Python SQLCipher module candidate | Not discoverable | Neither `sqlcipher3` nor `pysqlcipher3` was found in the isolated system Python search path. No plaintext substitute was selected. |
| Free-account eligibility | Unverified | SSH and host capacity cannot establish billing entitlement. No tenancy/billing credentials or API were accessed. |

Oracle remains a **candidate**, not an approved or qualified memory destination.
This host would be independent of losing the laptop, but colocating live memory,
the sole latest-state catalogue, backups and keys there would still share one
host/failure domain. Another older encrypted backup cannot establish freshness.

## Implemented local drill

[check_recovery.py](check_recovery.py) uses generated keys and the existing fake
authority fixtures. It creates a consistent SQLite copy of the trusted metadata
catalogue and copies only its selected encrypted backup/checkpoint pair. It does
not copy the canonical live database, bootstrap store or historical snapshots.
The generated source directory is moved out of its original path before starting
a fresh isolated Python process; only that fixture is moved.

The child receives generated fixture secrets on stdin rather than command-line
arguments, logs no values/keys and reconstructs memory from the surviving
catalogue, bundle and separately supplied keys/known anchor. It then requires
explicit fake existing-owner proof for activation. This simulates loss of the
source path; it does not simulate losing a physical host, OS or disk.

[Three recovery checks pass](recovery-validation.json), with
[log](recovery-tests.txt):

1. Latest-state recovery and activation preserve a correction/stable owner UUID,
   suppress forgotten and expired records, reject the old writer and resume one
   binding with zero jobs, without the original source path or a live DB copy.
2. Missing/wrong storage or recovery keys and a missing catalogue refuse recovery;
   a missing catalogue is not recreated over the surviving directory.
3. An older catalogue/bundle is rejected when the latest trusted anchor survives
   separately. Combined rollback of that trust anchor and catalogue remains
   outside the current protection.

[test_screening.py](test_screening.py) adds one passing fake-counter check for
thresholds, malformed counters, withholding private fields and keeping billing,
key-custody, Linux qualification and production-readiness gates false.
[Static validation](static-validation.json) records source preservation, parsing,
local links, ignored raw evidence, fixture cleanup and the four local checks.
Previous 114-check evidence remains dated and unchanged; it was not rerun here.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-12-memory-placement/test_screening.py
.\.venv-ui\Scripts\python.exe review/2026-10-12-memory-placement/check_recovery.py
```

The explicit live command is
`check_oracle.py --live-read-only`. It refuses to overwrite the first screening
evidence; preserve that evidence before a deliberate later assessment. It reuses
the existing pinned SSH command builder and bounded exchange, never accepting
unknown host keys. Read-only SSH still produces ordinary server authentication
logs. No inference/provider call or synthetic memory transfer to Oracle occurred.

## Next implementation gates

1. Verify the existing instance/account allowance in the owner's Oracle console;
   no paid provisioning, resize or subscription is authorized.
2. Qualify an encrypted driver on the actual Linux architecture in an isolated
   fake-data environment, without modifying the mobile service environment.
   Driver installation or remote fixture creation needs a separately authorized
   staging step; neither was performed by this read-only assessment.
3. Select protected recovery/storage key custody and a trusted latest-state policy
   that survive the chosen host failure. Existing Windows DPAPI storage alone
   does not prove recovery after losing that Windows account/device.
4. Prepare and test a separate restricted authority service, storage/admission
   budgets, backup retention and a real clean-host recovery drill before routing
   clients or storing valuable records.

No real key creation, owner enrollment, private migration, deployment, new resource,
provider/model/UI/voice/startup change, commit or push. Protected keys, independent
durability, Linux encrypted-engine behavior and real-device acceptance remain open.
