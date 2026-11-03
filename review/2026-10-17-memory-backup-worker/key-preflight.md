# B2 key preflight — 2026-10-18

Read-only account inspection completed after owner reauthentication. A separate signed-in browser tab was available; the earlier sign-in tab was stale. The existing lab destination still showed three objects. No additional transfer, credential creation/reveal, permission change or deletion occurred. Private account identifiers and raw page state are deliberately absent from this report.

The observed Add Application Key dialog provides bucket selection, three access presets (Read and Write, Read Only, Write Only), a file prefix and duration. No custom capability selector was present. Opened the blank form, inspected it and cancelled; the final page showed no new application-key entry. The worker's exact three-capability requirement remains unchanged. Selecting a preset is not evidence of compatibility.

## Concrete proposed access

- One existing disposable lab bucket, with its ID supplied locally by the owner.
- Literal prefix `lya-memory-lab/worker/`; this excludes the earlier three root-level test objects.
- Exactly `listBuckets`, `readFiles`, `writeFiles`; no delete, sharing, retention, bucket modification or key-management capability.
- One-hour lifetime; this is a single fake-data qualification, not a persistent scheduler credential.

[Non-secret request template](key-request-template.json) records that scope. It contains placeholders, no credential, and is not a runnable provisioning command. Backblaze's [v4 create-key API](https://www.backblaze.com/apidocs/b2-create-key) accepts `bucketIds` (plural), `validDurationInSeconds` and explicit capabilities. The UI labels its duration differently; do not copy that label into the API request. The API requires an issuer token with `writeKeys`. The worker must never receive that issuer credential or the owner's vault password/unlock key.

The [filtered bucket-list API](https://www.backblaze.com/apidocs/b2-list-buckets) requires `listBuckets` and the restricted bucket's ID/name. The existing worker supplies `bucketId`; no account-wide name-listing capability is proposed. The general [console guide](https://www.backblaze.com/docs/cloud-storage-create-and-manage-app-keys) describes preset-based creation; the live form is the evidence for the observed choices.

## Remaining gate

Protected local provisioning is not implemented or qualified. Before real access is created, prepare and fake-test a local mechanism that hides issuer input, withholds secret responses from console/logs, keeps the issuer transient, stores only the restricted child credential using the host's protected credential facility, and hands that child to the worker without shell arguments/plaintext configuration. Credential expiry and cleanup must be explicit. This report neither authorizes use of a master credential nor instructs the owner to regenerate one: regeneration can invalidate an existing key.

After that mechanism is reviewable, obtain the exact access-creation approval and owner credential-entry handoff. Upload to this new prefix also needs its own scoped approval; the earlier approval covered only the three root-level files. Then qualify native-client TLS/authentication, actual forbidden-operation denials and fresh-process recovery from downloaded fake ciphertext. Do not weaken the worker to accommodate broad console presets.

Checks for this documentation-only preflight: request JSON shape, exact capabilities/prefix/duration against the current worker, placeholder-only identifiers, affected local links and whitespace. No runtime test rerun; preceding 47-case platform results remain dated evidence. No functioning live worker, credential custody or independently surviving witness/catalogue is claimed.
