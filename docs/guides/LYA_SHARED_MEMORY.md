# Shared memory client integration

Implemented in source on 22 October 2026. Desktop and phone now have an explicit command route to one configured publication authority. The first supported backend is the existing **synthetic-only** authority. No real personal-memory activation, existing-note migration, new owner enrollment or live deployment has occurred.

## Connected path

Desktop voice/text reaches the existing `Brain.respond()` workflow. A shared command requires its existing exact native approval and fresh passkey-bound identity. The configured native client uses the existing pinned operator SSH path to the `shared-memory` control operation in `cloud/mobile_runtime.py`. The phone sends the same command through its existing `/chat` route, with a live paired session and fresh Verify owner proof. Both paths reach `SharedMemoryService` and the same encrypted publication authority and server-held fenced writer grant.

The operator SSH channel is a trusted native-adapter boundary, as with existing pairing control. Its native identity claims are not independently signed/reverified as an exact action on the server. They are never accepted by a browser HTTP endpoint. This and the phone's bounded owner-verification window are **demo trust boundaries**, not qualification of production private-action authorization. Existing local note/vault approval and confidentiality rules remain unchanged.

No writer token, storage key, unlock or memory database is sent to the phone. Neither client sends these shared facts to public inference. A shared turn clears the public model history and is never appended to it. The current phone page can show the exchange in its existing bounded DOM history; lock/background lifecycle cleanup remains, with no new browser persistence.

## Explicit commands

Once the fake-only service and client have been explicitly configured:

```text
shared memory demo: remember permanent colour = blue
shared memory demo: recall colour
shared memory demo: correct colour = green
shared memory demo: forget colour
```

`demo` is the project scope; different project names remain separate. `remember` requires `short`, `long`, `permanent` or `until <ISO timestamp with timezone>`, following the existing retention vocabulary. Labels support Unicode. Corrections preserve expiry and use the exact current label. Recall returns up to three complete matching notes, bounded for the phone response, and asks for a more specific label when additional matches exist. Replies say `Shared demo memory`. Ordinary local `remember`, private mode, public chat/research, voice engines and startup choices retain their existing routes.

This is explicit memory management. Automatic extraction from conversation, general-answer memory injection, a full knowledge graph and scheduled jobs are not added. A model cannot turn an ordinary question into a shared write.

## Configuration and preparation

[prepare_shared_memory.py](../../tools/prepare_shared_memory.py) prepares a **new empty fake-only** directory for a generated fake identity binding. Both `--synthetic-only` and `--approved` are mandatory. It reuses the SQLCipher candidate, existing snapshot/capsule/trust/latest publication primitives and explicit writer acquisition. It creates no account, real owner, provider request, network listener or scheduled task, refuses an existing destination and puts a scoped `.gitignore` in the generated directory. A failed preparation may leave an incomplete directory; preserve it and use a new destination rather than resetting custody.

The target needs compatible Python, `cryptography`, `fido2` for the mobile runtime and the qualified `sqlcipher3` driver. Dependencies and native drivers are not installed by this implementation. A successful existing mobile service does not establish SQLCipher availability there. Linux service/runtime/resource qualification remains necessary before a remote activation.

The generated `shared-memory.local.json` holds **disposable fake** custody and writer state. It must be treated as protected local runtime material, never committed, shown in chat or reused for real memory. POSIX mode checks are enforced; independent custody and Windows ACL qualification are not provided by this helper.

The server's explicitly selected configuration entry is:

```json
{"shared_memory":{"mode":"synthetic","state_file":"/var/lib/lya-connect/shared-demo/shared-memory.local.json"}}
```

This is a proposed path, not an installed directory or a change to `/etc/lya-connect.json`. Absent/false configuration leaves the current service behavior unchanged. A missing catalogue/latest/configuration, invalid fake-only mode, incomplete-recovery marker or revoked grant refuses startup/use; there is no recovery bootstrap or automatic takeover.

The desktop reads the ignored `desktop/shared-memory.local.json` only on a shared command. It requires `enabled: true`, `mode: "synthetic"`, an explicitly selected host and an existing project-contained pinned SSH key path. It never modifies the accepted inference/mobile settings. The key is used only by SSH; identity context and command text go over stdin. No live configuration or key was created during development.

## Interrupted writes and retries

The service stores a bounded resolution journal in the fake authority catalogue: principal, request ID, command hash and resolved target ID/revision. It stores no command text, values or grant there. Before dispatch, this pins the original correction/forget target. The existing authority provides durable mutation receipts and waits for publication before acknowledgement. A later edit cannot silently change an interrupted request's target revision.

The desktop and phone page preserve an uncertain write's original ID in RAM and reuse it only for the identical command. Another write is blocked until it is resolved; reads remain available when canonical publication is confirmed. Phone admission permits only an exact shared-command retry and keeps public-chat/audio replay rejection intact. Concurrent processes use the existing canonical source lock and exact-anchor checks; a race may refuse and require explicit reconciliation rather than overwrite another update.

After any uncertain result, use the existing explicitly approved `reconcile_publication()` operator path and resend the original request. Do not create a new request assuming that an exception rolled back the write. A process/session/page loss can discard the client's RAM retry ID; inspect the committed state and reconcile before issuing another mutation. No automatic retry, grant recovery, owner reactivation or resumed job is added.

## Evidence and remaining work

[Dated implementation report](../../review/2026-10-22-shared-memory/README.md) distinguishes passing functional cases, the fresh-process runtime check, the simulated client retry checks and one unexplained refused-write result. All data/keys and signed identities in those checks are generated fixtures, with an injected trusted native approval verifier.

This delivers the first shared-client command integration in source. Remote activation, real iPhone/Windows interaction, laptop-off availability, current Linux runtime/resource behavior and production identity/key custody remain unverified. Complete catalogue publication in every acknowledged update, independent current-state survival, combined remote witness fencing and private rollout remain separate unfinished parts of the larger shared-brain task. The existing synthetic guard must not be removed to bypass them.
