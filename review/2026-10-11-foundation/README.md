# First implementation slice: readiness and server timing

11 October 2026. Owner authorized implementing the roadmap one step at a time.
This slice implements the measurement foundation. It does not enable shared
personal memory or install a new database/model/connector.

## Implemented and deployed

`cloud/mobile.py` adds a content-free `Server-Timing` response header for POST
requests, including rejected, failed and cancelled requests. Fixed stage names:

- `asr`: the existing transcription callback and audio-slot acquisition.
- `inference`: the existing complete inference callback, including worker startup.
- `tts`: the existing complete voice callback and audio-slot acquisition.
- `request`: handler time through reading/validation/response serialization, before
  writing the response to the connection. It includes the measured stages; do not
  add it to them as if it were a separate stage.

Timings use the monotonic performance clock, are isolated per worker thread and
are cleared after each request. Only fixed names and numeric durations are added.
No transcript, prompt, audio, cookie, request ID, credential, name or stored fact
is logged by this instrumentation. No new telemetry file/database/endpoint or
third-party analytics service exists. Existing diagnostic/session policies apply.

The JSON response shape, existing models, voice, pause logic, client script,
permissions, quotas and pairing are unchanged. The release staged four Linux
fake-data tests under the restricted service account, then atomically replaced
only `cloud/mobile.py`. A previous source copy is retained for rollback at
`/opt/lya-connect/updates/timing-20261011/previous.py`, readable only by root.
One service restart occurred; it discards existing RAM chat sessions, so a current
phone session may need sign-in again. Pairing itself was retained.

## Actual checks and measurements

| Evidence | Result / limit |
|---|---|
| `test_mobile_timing.py` plus existing mobile/voice/conversation tests | 34 pass, fake keys and temporary stores |
| Existing synthetic client check | 18 scenarios pass; page source unchanged |
| `baseline.py` / `baseline.json` | 48 real loopback HTTP requests with fake providers; p50/p95 reported by scenario |
| Injected failures | Eight provider errors, eight cancellations, eight voice fallbacks; all expected outcomes retained in report |
| `stage.json` | Four Linux tests pass under restricted account, before activation |
| `activate.json` | Service active, timing present, unsigned request rejected, auth file inode preserved, protected code/settings hashes unchanged |
| `network.json` | Private TLS/page/security headers and timing through the actual proxy checked; no sign-in/provider call |
| `readiness.json` | Fresh read-only Oracle counters and pre-release public-code hashes; not a billing check |

The baseline's millisecond results exercise the actual HTTP/auth/serialization
path with trivial fake providers. They are not end-to-end phone/model/voice speed.
The HTTP 2xx count is 32/48 because 16 failures/cancellations were deliberately
injected. Eight of the 32 successful HTTP results deliberately use text fallback.
Do not interpret these artificial proportions as production reliability.

Not measured: real microphone endpointing, external upload/download, cold/warm
model execution, actual provider latency, audio-device playback and owner accuracy.
The present route produces complete text/audio, so first-token/first-sample service
metrics are unavailable; do not equate callback completion with those events.
SSE/WebRTC, worker reuse and new models remain later experiments.

## Resource and data gates

Owner clarification: Oracle free tier only. `oracle-access.json` confirms the
configured project key exists, is ignored/untracked by Git and successfully
authenticates through the existing pinned SSH connection. Its contents were not
displayed. SSH access does not provide a billing-entitlement check; no paid upgrade,
new billable resource or resize is authorized.

Read-only counters still show four ARM logical CPUs, approximately 23.4 GiB RAM
and 189.2 GiB free server disk. These are capacity observations, not proof of free
entitlement. The phone service retains its 256 MiB limit. No extra resident model
or background service was added.

Actual Oracle billing/free eligibility, independent recovery destination and key
custody remain unresolved. They gate valuable live shared records, not fake-data
contract/prototype work. No private vault/biometric/photo/credential migration is
implied by the implementation request. Existing public provider routing remains.

## Reproduce safely

From the project root using the existing UI environment:

```powershell
.\.venv-ui\Scripts\python.exe -m unittest test_mobile_timing test_mobile test_mobile_voice test_mobile_conversation
node review/2026-10-10-mobile-conversation/check_client.js
.\.venv-ui\Scripts\python.exe review/2026-10-11-foundation/baseline.py
```

Tests need working temporary SQLite/loopback permissions. The first sandbox run
failed before test setup because Windows denied temporary database access; the
same tests passed outside the sandbox. A baseline report-content assertion also
mistook the scenario label `text` for a payload field; it was corrected to validate
the exact sample schema and forbidden fixture content, then all 48 cases passed.

`readiness.py` reads host counters through the existing pinned SSH operator.
`release_timing.py` is a one-time guarded stage/activate tool, not an automatic
startup or repeat-deployment command. It refuses mismatched source hashes or an
existing release stage. Do not rerun it to diagnose phone performance.

The isolated shared request/identity/persona contract is now implemented and
fake-data tested; see [the contract slice](../2026-10-11-conversation-contract/README.md).
It is not connected to production chat paths. The [fake selective-memory baseline](../2026-10-11-memory-prototype/README.md)
now covers stable owner/credential-rotation mapping and durable memory semantics.
Next: encrypted storage and deletion-aware recovery qualification. Live personal writes
remain behind the resource, placement and recovery gates. Use the measurements
from actual phone use before deciding which speech/model stage to optimize.
