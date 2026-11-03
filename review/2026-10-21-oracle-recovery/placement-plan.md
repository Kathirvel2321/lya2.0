# Independent custody: next bounded fake-data milestone

Prepared on 22 October 2026. This is a proposed qualification scope, not an installed service, selected credential, live transfer authorization or proof of independent custody. See the [reconciled evidence and limits](README.md).

## Intended placement

Reuse the owner's existing Always Free Oracle host for the current-state witness, the already selected B2 destination for encrypted backup candidates, and owner-controlled separate custody for the fake unlock. Account availability/cost limits must be checked in the actual scoped run; this plan creates no resource or subscription. Bitwarden/offline custody for real keys remains a separate owner-controlled enrollment task.

Keep three distinct responsibilities:

| Role | Must survive | Must not obtain its authority from |
| --- | --- | --- |
| Recovery backup | Authenticated encrypted complete catalogue/record envelope and required artifacts | Its own supplied latest fingerprint or a provider upload receipt |
| Independently current witness | Exact confirmed publication/fingerprint and writer epoch, plus explicit pending state | A replacement store created during recovery from the backup packet |
| Separate owner custody | Fake unlock and trusted code/service identity handoff | The backup folder, source laptop-only DPAPI record or plaintext ledger |

A second folder, another process or WSL is not a separate failure domain. A temporary Oracle store seeded at restore time is not independently surviving trust. Remote storage alone also does not solve rollback of the witness itself.

## Implementation boundary before placement

The existing schema-5 publication authority requires the exact local `SyntheticRecoveryLatest` type and directly uses its SQLite transaction. It cannot safely accept a network client by substituting a path or subclass. The existing authenticated TLS/network coordinator is a separate mode. Compose those existing acknowledgement/fencing protocols explicitly before treating a remote witness as live authority; do not weaken exact-type checks, expose SQLite on a share or add an uncoordinated mirror.

The complete catalogue envelope is currently sealed explicitly after a confirmed publication. Define how that exact protected catalogue capture becomes durably recoverable before its corresponding acknowledgement is considered recoverable. A current record pack with an older catalogue envelope must refuse, rather than silently discard later owner/writer changes. Preserve source reservations and explicit reconciliation across interrupted publication.

Do not connect the independent placement to accepted desktop/mobile behavior during this milestone. Use one generated lineage, bounded records, finite runs and an explicit new lab destination. No real enrollment, live store, scheduler, provider-key renewal, production certificate/service change, paid provisioning or automatic job resumption is included.

## Required acceptance evidence

1. Establish the fake witness and separately protected fake unlock before the loss event. Pin exact service/code identity through the agreed trusted channel. Record only content-free status and public source hashes.
2. Publish two distinct versions through the coordinated source acknowledgement path. Show the exact complete catalogue/encrypted artifacts are recoverable for each acknowledged state. Confirm the later witness state by a separate authenticated observation.
3. Interrupt publication before and after its durable boundaries. Pending or uncertain state must block recovery, then approved reconciliation must establish one exact outcome without replaying jobs or revealing a lost grant.
4. Delete only the owned generated original source/catalogue fixture. Recover on the separate qualified host from the surviving backup, previously established witness and separately retrieved fake unlock. The recovery procedure must never call witness `create()` or `begin(None, ...)` as a fallback.
5. Verify encrypted quarantine, preserved corrections and forget/expiry suppression, zero bindings/jobs, old-writer refusal, and fresh verification of the preserved pre-existing fake owner before activation. Test replay of the first version against the second confirmed state, missing/unreachable witness, wrong unlock, mixed artifacts and lost replies.
6. Exercise backup-host loss and source-host loss separately. Joint witness rollback must either be detected by a further independently current anchor or remain an explicit unqualified risk; never claim the existing local protocol detects it. Preserve old evidence and clean up only the exact temporary lab resources covered by the run.

Passing these checks would qualify that finite fake-data configuration. It would not by itself authorize real keys/private memory, whole-account disaster recovery or production cutover. No additional cloud operation has been performed by preparing this plan.
