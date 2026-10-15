# TLS witness process lifecycle lab — 15 October 2026

The owner requested the next memory-foundation step after supplying a successful 72-case Ubuntu TLS result. This slice adds [separate-process fake-data checks](../../test_memory_witness_process.py) and a [workspace-only runner](check.py). The existing witness, TLS verifier, coordinator and accepted application runtime are unchanged. It uses the existing standard-library subprocess/server APIs, existing test fixtures and disposable test certificates; no dependency or service is installed.

## Process behavior checked

The test worker reopens the existing synthetic witness and validates pinned protocol state/key before loading the TLS certificate and opening its fixed loopback listener. It never creates replacement trust on startup. Test-only fault injection exits immediately before or after the witness SQLite transaction commits. Fake protocol keys travel to the child over stdin, not command-line arguments; stdout carries only test readiness/synchronization signals. The worker accepts a local stdin stop command and closes the listener after its server thread stops. It is a test harness, not a deployable service or restart supervisor.

Seven new cases cover:

- External process termination after prepare: the listener closes, and restart retains the pending reservation so finish/retirement can proceed.
- Actual process exit before/after **prepare, finish and retirement** commits: six subcases distinguish rollback from durable state, generation, receipt count and retirement floor. The exact operation remains safely retryable after restart.
- Parent-driven termination at synchronized points inside a transaction and after commit, proving both rollback and committed reservation survival.
- Graceful process stop while a peer is silent during TLS handshake or has sent an incomplete HTTP body. The process must exit within five seconds and preserve the witness file.
- Oversized-body rejection before protocol access, followed by 40 signed observations: no mutation receipts, unchanged trusted state and logical database pages within the existing cap.
- Missing/corrupt witness or wrong protocol key: startup emits no readiness, exits with an error, and neither recreates nor repairs trust.
- Encrypted fake-memory coordinator integration: witness process death before/after finish commit withholds success, leaves the source journal pending, and restart permits approved exact-receipt reconciliation without returning lost grants/content. Repeated save returns the same record/state; approved retirement binds the latest confirmed protocol generation.

The original eight TLS cases are included in the focused selection. The earlier owner-reported 72-case Ubuntu suite remains separate evidence; overlapping counts are not added.

## Evidence

**All 15 selected Windows checks pass in one corrected run**, with zero failures/errors/skips: seven new process cases plus the eight existing TLS cases. No full 79-case run is claimed; the 64 preceding non-TLS cases and their implementations are unchanged and retain their earlier evidence.

[Validation and source hashes](validation.json), [test log](tests.txt), and [source/document preservation checks](static-validation.json) record the current result. The first run passed 14 of 15 cases; two subcases of the new coordinator test failed only because its assertion expected protocol generation 1 after two memory retries. Existing authority transactions correctly advance that counter even when a memory retry preserves the same record/state. The assertion now uses the exact confirmed head generation and checks receipt removal; no runtime implementation changed. [Initial validation](initial-validation.json) and [initial log](initial-tests.txt) preserve that run.

Temporary fixture stores, fake keys/certificates and child processes are cleaned up. Windows execution uses the permitted workspace-only path because the existing atomic hard-link publication operation is denied by the restricted sandbox; that primitive remains unchanged. No real store, OS/WSL setting, system trust, account, production key, paid resource or external host is touched.

### Owner-reported Ubuntu result

The owner supplied complete Ubuntu output reporting **all 15 cases passing**, final `OK`, and no failures/errors/skips. Matched all seven process and eight TLS case IDs against the current source definitions. [Sanitized reported validation](wsl-user-reported-validation.json) excludes terminal prompts/host details; [documentation/source preservation](wsl-report-static-validation.json) accompanies this evidence-only update. No assistant WSL execution or copied Linux source-hash measurement is claimed. The prior 72-case suite overlaps these TLS cases and is not added to this count.

Subsequent [direct WSL verification](../2026-10-15-direct-wsl-testing/README.md) compared 13 lab source/test hashes with reviewed workspace copies and independently ran these 15 checks through the assistant, all passing. This is separate evidence from the owner-reported output; no deployment or configuration change was needed.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-15-memory-witness-process/check.py
```

For the already-refreshed owner Ubuntu lab, copy only the new test. Existing `test_memory_witness_tls.py`, protocol/coordinator helpers, portable `test_qualification.py`, SQLCipher and `cryptography` are prerequisites from the completed lab:

```bash
cd ~/lya-lab
source .venv/bin/activate
src=/mnt/c/Users/kathirvel/Downloads/lya-main/lya-main
cp --backup=numbered "$src/test_memory_witness_process.py" .
python -m unittest -v test_memory_witness_process test_memory_witness_tls
```

Expected selection: **15 tests**, no skips. The owner-reported Ubuntu pass above is distinct from an assistant Linux run; Oracle qualification of this slice remains open.

## Limits and next step

This is same-host process termination/restart and bounded synthetic request testing. It is not physical power loss, an OS reboot, independent host recovery or whole-witness rollback protection. SQLite's existing synchronous transaction policy is reused; no storage-device durability guarantee is inferred from process death.

The existing 8 KiB body ceiling, two-second handshake timeout/socket inactivity limits, nonce/receipt limits and logical database page cap are exercised. These do not impose total HTTP-header, wall-clock request, RSS/CPU, journal/WAL or filesystem-wide budgets. Repeated slow connections can deny availability on this serial loopback server; forty observations are a functional bounded-state check, not a soak/load/throughput result. OS resource ceilings, admission under concurrent/hostile load, process supervision and certificate lifecycle remain open.

Next qualify concrete resource/admission limits and independent free witness/recovery placement. Real custody, device acceptance and a separately approved private pilot remain pending. No production caller, accepted voice/hearing/UI/startup, deployment, enrollment, commit or push was changed.

Follow-up: [fixed request I/O deadline and header budget](../2026-10-15-memory-witness-admission/README.md) qualifies the later transport revision with all 83 selected Windows/Ubuntu cases, including this process suite. It does not establish OS resource caps or sustained-load availability.
