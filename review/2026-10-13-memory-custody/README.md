# Sealed recovery keys and latest-state witness — 13 October 2026

Later 2026-10-13 follow-up: [optional authority witness binding](../2026-10-13-memory-witness-ack/README.md) now implements local commit acknowledgement and reconciliation. The report below describes the earlier standalone slice. Independent witness hosting, real keys and production integration remain pending.

The owner requested implementation and selected an **existing password manager**
for eventual recovery-key custody. Added an isolated fake-data key-envelope and
witness protocol in [memory_custody.py](../../brain/memory_custody.py).
No password-manager account or entry is connected, and no real unlock/storage/
recovery key is created. Production memory and accepted clients remain unchanged.

## Implemented boundaries

| Component | Behavior |
| --- | --- |
| Key envelope | Authenticated Fernet encryption of the generated storage/recovery keys and lineage, using a separate random unlock key. The unlock key cannot equal either stored key. No password-based encryption or custom cryptography. |
| Publication | Reuses the existing atomic no-overwrite publication primitive; verifies the encrypted envelope before/after publication. Cancellation or failure never silently replaces a previous capsule. |
| Unlock | Requires explicit fake-data opt-in/approval, exact trusted envelope digest and lineage. Bounded reads, strict fields/version, duplicate-field rejection, authentication and canonical generated-key validation fail closed. Keys are omitted from object representations. |
| Witness | A separately trusted SQLite metadata store pins the capsule digest and exact checkpoint plus writer epoch. It contains no raw key or conversational content. |
| Advancement | Literal approval, compare-and-swap, monotonic sequence/epoch and same-sequence divergence rejection. Writer takeover/revocation is detectable even if the memory checkpoint has not changed. Exact lost-reply retries are idempotent; silent key rotation is rejected. |
| Missing trust | Opening a missing witness fails; no empty replacement or backup-derived freshness is inferred. Explicit initial bootstrap is separate from reopening. |

The unlock key is intended to be an owner-held random secret in the selected
password manager, separate from the encrypted key capsule and backup host.
It is not the password-manager master password. Losing that unlock key prevents
opening the capsule. The witness identifies the exact capsule; a re-encrypted
replacement is rejected until a separately verified rotation process exists.

## Important integration limit

**This witness is not yet part of the authority's write acknowledgement path.**
Existing authority success means its local commit, not independent custody.
The test caller explicitly publishes a verified state to the witness and checks
it before recovery. A newer source state reports a mismatch until explicitly
witnessed. An external witness cannot detect writes never reported to it if both
the source and knowledge of those writes disappear.

Production integration must route every relevant write, takeover, recovery and
activation through the independently hosted witness and wait for its durable
acknowledgement before claiming independent recoverability. Partial cross-store
commits need reconciliation that fails closed; a stale success must not be
replayed. An exact-state check is only valid at its observation time, so recovery
and activation must serialize/revalidate against concurrent witness advances.
These distributed-service guarantees are not claimed by the standalone API.

The witness itself is trusted. Rolling it back together with all external latest
state remains undetectable. Putting it in another folder on the same host is a
test arrangement, not an independent failure domain. The encrypted key capsule
also does not contain backups, the latest authority catalogue or identity state;
those must survive separately. Native identity/lost-passkey enrollment remain
outside this work.

## Evidence

**20 checks pass on Windows and again on Oracle Linux ARM64**, zero failures,
errors or skips: 12 new [custody checks](../../test_memory_custody.py) plus the
eight preceding portable encrypted-storage checks.

- [Local validation](validation.json), [local log](tests.txt).
- [Linux validation](linux-validation.json), [Linux log](linux-tests.txt).
- [Static/source preservation](static-validation.json).

Cases cover encrypted roundtrip, restart, absence of raw secrets in envelope/
witness bytes and representations, literal approvals, independent unlock keys,
wrong unlock/lineage/digest, authenticated malformed or oversized capsules,
no-overwrite, missing witness/schema refusal, monotonicity, epoch-only rollback,
key pinning, cancellation/catalogue failure, simultaneous advances, invalid states
and actual child-process death before/after witness commit with safe retry.

The integration case unlocks fake recovery keys, validates the exact witnessed
authority state and restores a selected latest bundle plus consistent catalogue
copy without its live DB, preserving forgetting. It also demonstrates rejection
of an older witnessed state. Direct synthetic authority is used; no Windows/
phone proof, password-manager UI/API or physical host-loss drill is qualified.

The Linux runner stages only public source/tests and the same pinned ARM64 wheel
as the [previous Linux qualification](../2026-10-13-memory-linux/README.md), with
the same bounded child limits. It records successful temporary-stage removal and
unchanged checked mobile sources/active state/memory cap. No system/mobile package
or service changed. The earlier 19-case pre-crash-test pass is retained separately;
the final full 20-case runs include the process-death case. Previous 114-check
evidence is preserved and was not rerun.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-13-memory-custody/check.py
```

Explicit temporary Linux qualification uses `check_linux.py --stage-fake-only
--owner-confirmed-free` and refuses to overwrite its existing evidence.

## Next step

Select an independently durable witness location outside the live-memory host's
failure domain and implement its acknowledgement/reconciliation boundary.
Then perform an owner-controlled password-manager save/retrieval and clean-host
recovery drill using protected real keys, only when real setup is requested.
No real secret should be entered in chat, source files or the project ledger.

Protected service accounts, TLS/authentication for an actual witness endpoint,
key rotation, retention/physical erasure, disk/admission budgets, power loss and
real-device acceptance remain open. No production activation, private migration,
enrollment, paid resource, model/provider/UI/voice/startup change, commit or push.
