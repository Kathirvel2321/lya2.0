# Authenticated witness protocol lab — 14 October 2026

Latest same-day follow-up: [witness capacity and recovery drain](../2026-10-14-memory-witness-capacity/README.md) adds signed receipt-free observations, protected finish receipt capacity, coordinator preflight, local counters and a logical database page cap. Earlier "all requests consume receipts" implications below apply to the initial protocol revision. No receipt retirement, TLS or independent host is enabled by this follow-up.

Later same-day implementation: the separate [durable network authority coordinator](../2026-10-14-memory-network-authority/README.md) now connects this protocol to the isolated authority. Prepare accepts a signed `expected_generation` field for atomic generation compare-and-swap; the coordinator always supplies it, while earlier standalone request forms remain compatible. The original authority still rejects a raw network client. The adapter-pending statements below describe this report's initial revision; current coordinator evidence is in the linked report. TLS, independent hosting and production integration remain pending.

The owner requested continuing the incomplete independent-witness work. Added [memory_witness_service.py](../../brain/memory_witness_service.py), a fake-data loopback client/server prototype with durable reservations, scoped HMAC-authenticated messages and retry receipts. No dependency, existing memory implementation, accepted runtime, host configuration or deployed service changed. The localhost endpoint starts only when explicitly constructed by tests; there is no background/startup installation.

## Implemented protocol

One explicitly configured service/client/lineage and independently generated 32-byte protocol key are pinned in metadata. Only the key's SHA-256 is stored; its raw value stays in memory and is never sent. Request/reply MACs use distinct domain labels. Requests bind the fixed POST path, service, client, nonce, time, request ID and exact operation; signed replies bind the HTTP status, nonce, request ID and SHA-256 of the original request. A reply for another request is rejected before its state is accepted.

| Operation | Contract |
| --- | --- |
| `head` | Authenticated observation of the current exact checkpoint, capsule digest and reservation metadata. It does not grant owner authority or prove a backup exists. |
| `prepare` | Require the exact head and capsule digest; reserve the transition using the stable request ID, increment a separate protocol fencing generation, and commit before replying. A competing prepare cannot steal it. |
| `finish` | Require the exact reservation ID, fencing generation, previous state and capsule digest; reuse the existing monotonic witness advance, release the reservation and commit its receipt in the same SQLite transaction. An unchanged-state finish is an explicit close, never an automatic timeout action. |

Fresh transport nonces are required even when retrying a logical request ID. Requests older or further in the future than 30 seconds are rejected; freshness is checked again before commit. Nonces and request-ID fingerprints/receipts survive restart. Reusing an ID for different content fails. A receipt is returned only while its complete observed head/reservation/generation is still current; a stale receipt cannot masquerade as the latest state. A lost prepare reply is retried with its original ID; a lost finish reply is retried with its original finish ID and a fresh nonce.

**Reservations do not expire or release on disconnect.** This deliberately chooses blocked availability over letting another writer proceed while the first source's commit outcome is unknown. The authenticated future coordinator must inspect its durable intent and authoritative local state before resuming or explicitly finishing unchanged. The service cannot itself prove that the source did not commit.

The HTTP boundary is fixed to `127.0.0.1`, rejects alternate paths, duplicate/oversized lengths, transfer encoding and wrong content type, caps bodies/replies at 8 KiB, uses a two-second socket/client timeout, and suppresses request logs. The lab server handles one request at a time. Receipt and live-nonce budgets are fixed at 1,024 and 2,048; full budgets fail closed. Expired nonce records may be removed; receipts are not automatically evicted. Lifecycle/retention tooling is not implemented. Errors carry fixed codes without request values or exception diagnostics.

See the validated [protocol diagram](protocol.mmd). Solid links describe this implementation; dashed links show work not connected. The scoped trace tool generated the entry node in [import trace](import-trace.mmd); explicit Python imports were then added from the reviewed source because the helper did not resolve dotted module names. This static import view is separate from the annotated protocol diagram.

## Authority integration boundary

The [existing authority integration](../2026-10-13-memory-witness-ack/README.md) holds one SQLite witness transaction across checking, source mutation and commit. The network client is intentionally rejected as a witness constructor argument. Substituting separate HTTP `head` and `finish` calls would lose that serialization guarantee.

The next adapter must durably record its operation ID and expected source/witness state before requesting a reservation; persist the returned fencing generation; commit the source transition and target in its local catalogue; finish that same remote reservation; and withhold replies until the signed current receipt is verified. On every restart or lost response, resolve the recorded intent against the trusted source journal and remote reservation before any new operation. Reads, expiry cleanup, takeover, restore and activation all need this path. An unchanged finish is permitted only after proving that the source transition was not committed. No lease-expiry bypass, token reconstruction or stale-result release is acceptable. That adapter is designed here, **not implemented or qualified**.

## Placement decision

No independent destination has been selected or provisioned. The current Oracle instance is the candidate live-memory host, so another folder or process there does not cover host loss. A laptop witness would make writes depend on the laptop being available, conflicting with the accepted phone-while-laptop-off goal. Another instance must not be presumed free or provisioned from the existing instance's allowance confirmation.

An acceptable destination needs a separate failure domain, persistent transactional state, authenticated restricted access, supported HTTPS transport, known free allowance/capacity and restore access independent of the live host/account failure being covered. Encrypted snapshot objects, the latest catalogue/identity state and the owner-held key capsule/unlock key need an explicit survival policy too; witness metadata alone cannot reconstruct memory. The selected password manager remains a key-custody preference, not a transactional witness host. Independently hosting both ends, key rotation/revocation, TLS identity, capacity/retention and clean-host recovery require a later concrete placement/setup step.

## Evidence and reproduction

[test_memory_witness_service.py](../../test_memory_witness_service.py) runs **18 fake-data checks**, all passing on Windows with zero failures/errors/skips. They exercise real localhost HTTP, wrong key/audience/client/domain, signed-reply substitution, time/nonce replay and expiry rollback, strict input bounds, key/state/generation pinning, missing schema, storage budgets, commit failure, lost prepare/finish replies, competing service instances and real process death before/after commits. [Results](validation.json), [log](tests.txt) and [source/documentation checks](static-validation.json) are recorded in this folder. The [initial run](initial-validation.json) passed 16 of 17; one malformed-HTTP test expected an HTTP status when Windows reset a connection with unread invalid body. The corrected test accepts either explicit rejection or TCP reset and confirms the head is unchanged; an additional expiry rollback case brings the final selection to 18.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-14-memory-witness-service/check.py
```

For the owner's Ubuntu lab, copy just the new module/test and run this independent selection using the existing virtual environment:

```bash
cd ~/lya-lab
source .venv/bin/activate
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src/brain/memory_witness_service.py" brain/
cp --backup=numbered "$src/test_memory_witness_service.py" .
python -m unittest -v test_memory_witness_service
```

The owner subsequently supplied Ubuntu WSL output reporting all 18 protocol cases `ok` and final `OK`, without failures or skips; see [owner-reported WSL validation](wsl-user-reported-validation.json). The assistant did not independently rerun WSL or measure the lab's source hashes. The pre-WSL static report retains its original observation and is supplemented by this later evidence. Oracle has not run this protocol. Previous 75-case Windows/owner-reported 38-case WSL evidence remains separate and applies to the existing unchanged authority flow. This is a local HTTP protocol experiment, not a TLS-qualified remote deployment, native authentication acceptance, hard sandbox, independent backup or power-loss qualification. Whole-witness rollback remains outside its protection. No real key, private data, enrollment, remote connection, paid resource, deployment, commit or push was used.
