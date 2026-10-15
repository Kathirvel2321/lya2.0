# Memory witness TLS and local restart lab — 15 October 2026

The owner confirmed continuing the memory foundation from the safe receipt-retirement checkpoint. This slice adds optional certificate-verified HTTPS to the existing **fake-data, loopback-only** witness client/server. It uses Python's standard `ssl` and `http.client`; the already installed `cryptography` package generates disposable test certificates. REA instructions were consulted, but readable Python source and focused tests cover this change without binary analysis or REA runtime integration.

## Implemented

[Witness transport](../../brain/memory_witness_service.py) accepts an explicit `ssl_context` on `loopback_server` and `SyntheticWitnessClient`. Contexts must have the correct client/server role and a TLS 1.2 minimum or higher. Clients require certificate-chain and hostname/address verification, rechecked before each connection. The peer is still fixed to `127.0.0.1`; no remote destination or listener option was added. Existing explicit synthetic HTTP fixtures retain their default behavior. A failed TLS connection never falls back to HTTP.

The TLS server accepts a raw connection, applies a two-second timeout, then performs the TLS handshake. Rejected/plaintext or silent handshakes close their socket without terminating the serving loop. Wrapping the accepted connection rather than the listening socket makes the handshake deadline apply before request-handler setup. HTTP body bounds, protocol signatures, replay/receipt validation and coordinator confirmation rules are reused unchanged. No coordinator schema, identity pin or receipt format changed.

The existing `shutdown`/`server_close` lifecycle remains. Tests stop/join the local serving thread, reopen the persisted endpoint, and reconnect with a verified TLS client. Pending reservations survive; committed finish receipts remain retryable after reply loss; acknowledged receipt retirement survives another restart. These are same-process server-thread restarts with reopened endpoints, **not** an installed service supervisor, OS reboot or power-loss qualification.

## Checks and artifacts

[Seven new cases](../../test_memory_witness_tls.py) check:

- Verified TLS prepare/finish, lost-reply retry, retirement and endpoint restart.
- Untrusted, expired and wrong-address certificates rejected before protocol access, with no HTTP fallback.
- Existing protocol-key authentication still required inside TLS.
- Wrong context roles, disabled verification, mutated client contexts and an inadequate server TLS minimum refused.
- Plaintext/silent connections rejected, subsequent verified requests served, and the stopped listener closed.
- Encrypted fake-memory coordinator reconciliation after a committed reply is lost and TLS service restarts; retirement and save retry then work.
- Certificate trust failure leaves the coordinator idle before local operation intent or source mutation.

[Runner](check.py), [combined validation/source hashes](validation.json), [combined log](tests.txt), [focused TLS validation](tls-validation.json), [focused log](tls-tests.txt) and [static/preservation checks](static-validation.json) retain the evidence. The first sandbox run was denied the existing atomic hard-link publication operation before reaching TLS; [initial result](initial-sandbox-validation.json) and [log](initial-sandbox-tests.txt) are preserved. The permitted rerun uses the same publication primitive and disposable workspace fixtures. Generated CA/leaf private keys and stores are removed with their temporary directories; nothing is installed into system trust.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-15-memory-witness-tls/check.py
```

**The initial revision passed all 71 selected Windows cases in one combined run, with zero failures, errors or skips:** seven new TLS cases plus the preceding 64 retirement/capacity/protocol/coordinator cases. This evidence predates the test-fixture correction below. Earlier local-authority/custody checks remain separate dated evidence; overlapping counts are not added. No full-repository or live application acceptance is inferred.

## Owner-reported Linux result and fixture correction

The owner's supplied Ubuntu output reports 71 cases run: all 64 preceding regression cases passed, while all seven TLS cases errored at the strict client-context check. The final summary records nine errors because one TLS case has three failing subtests. [Sanitized owner-reported evidence](wsl-user-reported-initial-validation.json) matches all 71 original test IDs and omits terminal prompts and host details. No assistant WSL execution, Linux source hashes or actual context-property measurement is claimed.

The TLS tests had relied on `ssl.create_default_context()` to expose an explicit minimum of TLS 1.2. An unspecified/platform-controlled minimum is refused by the intentionally strict verifier. This is the inferred explanation of the reported platform difference; the original traceback does not distinguish the individual context properties checked. A new regression simulates `MINIMUM_SUPPORTED` and [fails before the correction](portability-before-fix/validation.json), with [failure log](portability-before-fix/tests.txt).

Only the test setup changed: all three client-context construction sites now explicitly set TLS 1.2. The new regression checks that the fixture pins this minimum even when the factory reports it as unspecified, then makes a verified loopback request. The witness implementation, strict verifier, certificate/address checks, signed protocol and all 64 preceding tests remain unchanged.

**All eight current TLS cases pass on Windows with that unspecified platform default emulated across the suite**, zero failures/errors/skips; see [validation/current source hashes](portability/validation.json), [test log](portability/tests.txt) and [static/preservation checks](portability/static-validation.json). The existing runner was reused with its output directory redirected to `portability/` and the default-context factory temporarily patched in the test process; no runtime or system setting changed. The original 71-case Windows artifacts remain intact. These focused Windows results preceded the successful owner-operated combined Linux rerun below. The earlier static report refers to the pre-correction source revision.

For the owner rerun, only the updated TLS test needs copying. With the existing lab environment active:

```bash
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src/test_memory_witness_tls.py" .
python -m unittest -v test_memory_witness_tls test_memory_receipt_retirement test_memory_witness_capacity test_memory_witness_service test_memory_network_authority
```

The current combined selection has **72 cases**.

## Owner-reported corrected Ubuntu qualification

The owner's subsequent complete output reports **all 72 cases passing**, final `OK`, with no failures, errors or skips. Matched every case ID to the current test definitions: eight TLS, 14 receipt-retirement, ten capacity, 18 protocol and 22 coordinator cases. [Sanitized reported validation](wsl-user-reported-validation.json) retains the case results without prompts or host details. The original failed Linux run and all earlier Windows evidence remain preserved separately; overlapping counts are not added.

This establishes an owner-reported Ubuntu lab pass for the selected corrected test suite, including real loopback TLS, graceful thread restart and the existing protocol/coordinator crash checks. The assistant did not independently execute WSL or measure copied Linux source hashes. No OS reboot/power-loss, TLS service-process crash, remote Oracle, independent recovery placement or production integration acceptance follows from this result. [Documentation/source preservation checks](wsl-report-static-validation.json) accompany this evidence-only update.

For the existing owner-operated Ubuntu lab, refresh only the changed witness module and new test. The existing isolated SQLCipher driver and `cryptography` must already be available; this command installs nothing:

```bash
cd ~/lya-lab
source .venv/bin/activate
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src/brain/memory_witness_service.py" brain/
cp --backup=numbered "$src/test_memory_witness_tls.py" .
python -m unittest -v test_memory_witness_tls test_memory_receipt_retirement test_memory_witness_capacity test_memory_witness_service test_memory_network_authority
```

If the new retirement test has not yet been copied from the preceding instructions, refresh it too. The portable `test_qualification.py` and other prerequisite modules are required by the existing lab. The owner-reported Linux result above is distinct from an assistant rerun.

## Limits and next step

This proves a bounded local TLS transport slice and graceful thread lifecycle. It does not select independent free hosting, protect against whole-witness rollback/loss, install process supervision, qualify admission under hostile/concurrent load, manage production certificates/renewal or protect real recovery keys. TLS authenticates the server; the existing signed protocol key authenticates the client. It is not mutual certificate authentication. The serial server can still lose availability under repeated slow connections; the two-second deadline limits one handshake, not aggregate load.

Next qualify actual service process lifecycle/resource limits and choose independent free witness/recovery placement. Real custody, private device pilot and production connection remain gated separately. No production caller, accepted voice/hearing/UI/startup, real store, account, dependency, external host, enrollment, paid resource, deployment, commit or push was changed.

Follow-up: [separate-process TLS witness lifecycle](../2026-10-15-memory-witness-process/README.md) adds actual process exit/termination and restart checks without changing this transport. Its Windows evidence and remaining Linux/resource/placement boundaries are recorded separately.
