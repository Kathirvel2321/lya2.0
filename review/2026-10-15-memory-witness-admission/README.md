# Witness request I/O and header budgets — 15 October 2026

The owner requested continuing the memory foundation after direct Ubuntu testing was verified. This slice changes only the isolated fake-data witness transport in [memory_witness_service.py](../../brain/memory_witness_service.py), adds [four focused checks](../../test_memory_witness_admission.py), and records regressions/continuity. Accepted desktop/phone/voice/hearing behavior, storage/authentication rules, protocol schemas and production callers are unchanged. No dependency, OS setting or service was installed.

## Implemented bounds

The old two-second socket inactivity timeout restarted whenever bytes arrived. Four real HTTP/TLS header/body drip subcases demonstrated that continuous input could hold a request open beyond its intended budget. Many individually short headers also reached protocol parsing without a small aggregate header-byte ceiling.

The shared serial loopback server now starts one **two-second I/O deadline at accept**, including TLS handshake time. Its raw socket streams recompute the remaining time before every receive/send; buffered line/body reads therefore cannot reset the budget with new bytes. This also covers standard HTTP error writes. An elapsed deadline closes the connection quietly. No per-request timer/thread pool, alternate protocol or third-party server was added.

The buffered reader caps **request line plus all headers, including delimiters, at 8 KiB**. It stops reading at the first byte beyond that total, before protocol access. An exactly 8 KiB valid header block with a separately bounded authenticated body still succeeds. Existing 8 KiB body, strict framing/signature/nonce checks, receipt/SQLite limits and required TLS certificate/address validation remain. Responses stay bounded by the existing protocol.

Both HTTP and optional TLS use this same server and reader/writer. It handles one accepted connection at a time and requests a listen backlog of two. The backlog is a kernel hint, not an exact portable limit on SYN/pending sockets or an aggregate rate limit. Existing synthetic HTTP opt-in/defaults and exact witness-client type remain compatible.

A deadline is an **I/O limit**, not a cancellation/rollback of a database transaction. A valid operation may commit before response delivery expires. Its exact durable receipt remains available for the existing retry/reconciliation path; timeout must not be treated as proof that nothing happened. The new deterministic delivery-expiry case verifies this boundary without delaying a real store.

## Evidence and reproduction

[Before-change validation](before-validation.json) and [log](before-tests.txt) show three of four new cases failing, with six failure records including the four drip subcases; the exact-header boundary case already passed. After the shared transport fix, [all four focused checks pass](focused-validation.json), with [focused log](focused-tests.txt). No failed assertion was weakened to obtain that result.

The [full Windows runner](check.py) selects **83 cases**: four new admission checks plus seven process, eight TLS, 14 retirement, ten capacity, 18 protocol and 22 coordinator cases. [Windows validation/source hashes](validation.json), [log](tests.txt), [direct Ubuntu validation](wsl-validation.json), [Ubuntu log](wsl-tests.txt) and [static/source preservation](static-validation.json) retain platform evidence separately. Overlapping case counts are not added.

**All 83 selected cases pass on Windows and in the assistant-executed Ubuntu run**, with zero failures, errors or skips on either platform. The before-change reproduction and focused recheck remain separate artifacts.

Before Ubuntu execution, checked 15 existing lab file hashes against the prior known/current reviewed revisions. Refreshed only the changed witness transport and new test, preserving numbered backups. All 16 selected lab source/test hashes then matched the workspace and were [verified unchanged after execution](wsl-post-run-validation.json). [Source manifest](lab-source-manifest.json) and [refresh verification](wsl-refresh-validation.json) retain that check. The assistant directly executed the full 83-case selection in the existing Ubuntu lab, with final `OK` and zero failures/errors/skips. This is measured execution, rather than owner-reported output. No private store/configuration was inspected or copied.

```powershell
.\.venv-ui\Scripts\python.exe review/2026-10-15-memory-witness-admission/check.py
```

The already-refreshed Ubuntu lab uses its existing virtual environment:

```powershell
wsl.exe --distribution Ubuntu-24.04 --exec bash -lc 'cd ~/lya-lab && exec .venv/bin/python -m unittest -v test_memory_witness_admission test_memory_witness_process test_memory_witness_tls test_memory_receipt_retirement test_memory_witness_capacity test_memory_witness_service test_memory_network_authority'
```

The owner does not need to rerun or paste these checks for this completed qualification. Reviewed tests use generated fake keys, temporary stores/certificates and test-owned loopback processes. Windows execution uses the permitted scoped path for the existing atomic publication primitive. No archive discovery or whole-project lab synchronization occurred.

## Limits and next step

The deadline bounds socket I/O, not CPU work, SQLite lock/commit duration or OS scheduling. Buffered data received before expiry can still be validated; an already committed operation is never undone merely to enforce a response deadline. Existing SQLite lock timeout/error handling and durable reconciliation remain in force. No hard two-second end-to-end operation-latency claim is made.

Serial handling and bounded inputs limit application-level request buffering and thread growth, but repeated new connections can still deny availability. The tests do not establish fairness, concurrent/hostile-load availability, a long soak, production throughput, RSS/address-space/CPU caps, journal/WAL or total filesystem quotas. Logical database page limits remain distinct from physical storage consumption.

Next select and qualify concrete process/OS resource budgets and admission under sustained load, then independent free witness/recovery placement. Production supervision, certificate lifecycle, whole-witness rollback/loss protection, power-loss/independent-host recovery, real custody and native-device/private pilot remain open. No production deployment, enrollment, real keys, external host, paid resource, commit or push occurred.

Follow-up: [finite Linux lab-worker resource profile](../2026-10-15-memory-witness-resources/README.md) qualifies explicit per-process address-space/descriptor/file/core/lifetime-CPU ceilings and rollback/restart failures. It does not select a continuous CPU-rate policy or aggregate disk quota.
