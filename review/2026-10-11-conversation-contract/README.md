# Shared conversation contract: isolated implementation

11 October 2026. Owner authorized the next implementation step. This completes
the fake-data shared request/identity/style slice in roadmap order 3. It does not
connect the contract to either production chat path or deploy it to Oracle.

## Implemented

`brain/conversation.py` provides two trusted adapter entry points:

- `desktop_turn(brain, packet, cancelled=None)` reuses the existing unique active
  owner/passkey validation against the native store, read-only.
- `phone_turn(connection, token, packet, cancelled=None)` reuses the existing
  paired passkey session, revocation stamp, expiry and laptop binding.

Both resolve the existing pairing binding internally, retain different session
identifiers, and use one `lya-conversation-1` style definition. Friendly, concise
LYA wording is shared. The owner-specific addition requires a fresh verified
native owner or the phone's existing signed fresh-owner proof. An ordinary paired
phone session remains friendly without claiming fresh owner authority. Matching
identity does not copy native privileges to the phone.

The only accepted packet fields are `id` (32 lowercase hexadecimal characters)
and `text` (1-4,000 characters after validation; raw text also capped at 4,000).
Client identity, role, scope, tools, history and memory fields are rejected.
Inputs are copied into immutable turn/context values. The provider receives only
the fixed style prompt and current public question, with no name, binding,
session token, passkey material, private records or prior device history added.
Replies are nonempty strings capped at 8,000 characters and preserve the existing
`text`/`id` response shape.

The contract checks identity and cancellation before inference and again before
returning an answer. It rejects expired sessions, changed/revoked identity or
verification, cancellation and replies reaching a 30-second monotonic deadline.
The deadline discards late replies; it does not itself kill a provider call.
The injected provider must retain its own timeout/cancellation behavior.

No speech engine, accepted voice, pause policy, UI, pairing, startup, model
selection, existing store or production routing was changed. No dependencies,
resident services, resource provisioning, paid accounts or external calls added.

## Checks and boundaries

`test_conversation_contract.py` uses the existing signed synthetic WebAuthn
fixtures, two disposable stores and fake inference. Its ten tests cover:

- Same pairing identity with separate device sessions; identical owner prompts
  when both fresh proofs are active; no identity egress.
- Friendly paired-device style without owner privilege claims.
- Forged identity/authority fields, malformed packets, lengths, Unicode and input
  mutation after validation.
- Session expiry, monotonic deadline, revocation, owner deactivation, changed
  pairing binding, native session switch and phone session replacement.
- Fresh-proof expiry, device-scoped Stop, existing mobile replay rejection,
  provider failure/invalid output and byte-identical persistent store contents.
- Exclusion of both devices' existing history and private note fixtures.

Combined check: 46 tests pass (10 new contract, 34 existing mobile/timing/voice/
conversation, two existing native owner-tone/privacy tests). Existing synthetic
phone JavaScript check: 18 scenarios pass. The initial sandbox attempt was blocked
on Windows temporary-store lock permissions before test setup; the same checks
passed outside the sandbox with temporary stores. See `validation.json`.

These tests verify deterministic contract behavior, not model obedience,
conversational quality, phone/laptop end-to-end integration or real latency.
The original production conversation paths continue using their existing prompts.
Nothing new will appear in the running apps from this isolated slice.

The contract does not perform admission, durable deduplication or memory writes.
Its callers must retain their existing request limits and replay controls; the
phone check explicitly wraps its existing `Connection.job`. Reusing a turn object
is not a durable retry guarantee. It supplies no new network endpoint.

The credential-derived pairing binding is an existing authentication join, not a
permanent memory-owner ID. Before durable shared records, introduce an explicit
stable owner mapping that survives authorized credential rotation/recovery.
Do not key years of memories directly to a passkey digest. Reset/rebinding is not
automatically authorized by a matching greeting or a client-supplied value.

## Reproduce

From the project root using the existing environment:

```powershell
.\.venv-ui\Scripts\python.exe -m unittest test_conversation_contract test_mobile_timing test_mobile test_mobile_voice test_mobile_conversation test_visitors.VisitorChecks.test_owner_tone_is_personal_without_sending_identity_or_private_data test_visitors.VisitorChecks.test_public_owner_question_needs_no_approval_and_private_context_never_leaks
node review/2026-10-10-mobile-conversation/check_client.js
```

No real enrollment is performed: the enrollment helpers sign generated fake
keys against temporary databases and local loopback ceremonies only.

The next fake-record selective-memory baseline is now implemented and tested:
[memory slice](../2026-10-11-memory-prototype/README.md), including stable owner/
project scope, explicit retention, corrections, forgetting and transactional
retries. It is plaintext fake-only and remains disconnected from production.
Next qualify encrypted storage and deletion-aware recovery before valuable live writes or
production adapter cutover. Oracle free-only eligibility, actual costs, selected
server-readable personal placement, independent recovery destination and key
custody remain open gates. No existing private data migration is implied.
