# LYA: final platform and implementation recommendation

Research/design, 11 October 2026. This is the recommended next sequence, superseding
the order in the original IMPLEMENTATION.md where they differ. It is not a claim
that these integrations exist or permission to export personal records. The
architecture contract still defines identity, placement, retention and authority.

Implementation began after the owner requested one step at a time. See
[the first slice](../2026-10-11-foundation/README.md): server timing instrumentation
and synthetic HTTP baseline. Billing/recovery gates and live speed qualification
remain open; this does not mark all of steps 1-2 complete.

## Decision in plain language

Keep one small authoritative memory service on the existing Oracle host, the
accepted Windows and phone interfaces, and the existing private network and
passkeys. Put selected readable project material in Notion only if that connector
is enabled later. Use an independent encrypted backup destination for recovery.
Measure the current answer pipeline, then remove its measured waiting time.

The owner clarified the exact projects: NandhaKishorM/laya and
browser-use/jev-ultrafast, as examples rather than mandatory dependencies. These
optimize decision work and browser operation, respectively. Their role is separate
from transport protocols and storage; evaluate each against its appropriate baseline.

## What to keep, add and defer

| Component | Decision and job | Boundary / reason |
|---|---|---|
| Python, PySide6, existing phone HTML/CSS/JS | Keep the accepted clients and reuse shared logic | Same identity, style and memory semantics; device sessions remain separate |
| Oracle host | Keep as the candidate always-on service host | First verify tenancy free eligibility, volume budget and idle-reclamation exposure; free hosting is not an uptime guarantee [1] |
| Tailscale + HTTPS + existing passkeys | Keep private transport and device authentication | Narrow grants; fresh proof for sensitive operations; measure direct versus relayed connectivity [2] |
| PostgreSQL + built-in text search | Preferred new shared-memory candidate | Transactions, revisions and scoped records; compare against SQLCipher/FTS using fake data before choosing deployment |
| pgvector | Add only if semantic retrieval improves held-out recall | Optional index in the same DB, not another truth store; filtered approximate search needs specific tests [3] |
| A database outbox + one bounded worker | First background workflow mechanism | Durable jobs committed with records; retries, leases, deduplication, queue limits and a visible failed state |
| restic | Preferred backup candidate | Encrypted versioned repository on an independent destination; use consistent DB backups and test restoration [4] |
| Google Drive or suitable object storage | Choose one approved off-host destination | Check remaining quota and restore capability first. Same-account Oracle copies alone do not cover account loss. No free-unlimited assumption |
| rclone | Optional storage adapter if the chosen destination requires it | restic already encrypts its repository. For independent file exports, rclone crypt is an option; sync alone is not versioned backup [5] |
| Notion | Optional approved research, decisions and tasks notebook | Publish asynchronously; scoped token, explicit destination, versioned export job. API rate limits make it unsuitable as a required step for every reply [6] |
| Obsidian | Optional selective Markdown notebook | Local files consume device storage; it is a readable export view, not a second writable memory authority [7] |
| Content-free timing metrics; OpenTelemetry later if useful | Measure latency, failure rate, resources and cost first | Allowlist diagnostic fields. Exclude prompts, transcripts, memory text, tokens and secrets [8] |
| MCP | Optional common adapter for multiple external tools | A tool interface, not a speed booster or authorization system. Pin reviewed servers, validate audience/scope, never pass arbitrary credentials through [9] |
| LangGraph | Later, if complex resumable tasks justify it | Checkpoints retain state; scope, expiry, idempotent effects and uncertain external outcomes still need application policy [10] |
| n8n | Later, if visual workflows are valuable to the owner | Use for asynchronous business tasks. Queue mode introduces Redis/workers/database coordination; unnecessary for two-device conversation [11] |
| LiveKit / Pipecat | Evaluate one voice stack only if continuous interactive audio is required | Qualification must preserve Amy, pauses and Stop. LiveKit self-hosting adds media networking, certificates and TURN considerations [12] |
| Letta, Mem0, Graphiti, Hindsight | Adopt researched memory principles first | Existing RESEARCH.md compares evidence, time, corrections and retrieval. Installing several overlapping memory frameworks would multiply consistency work |
| LAYA decision engine | Later isolated local routing experiment | Candidate for a small ordinary-intent shortlist; deterministic authority and memory-consent checks remain outside the model [17] |
| Jev Ultrafast | Later approved browser-task experiment | Structured page/action selection using TypeSafe Jev plus a text helper; external provider and browser permissions need separate qualification [18] |

No current requirement justifies Kafka, Kubernetes, a separate graph cluster or a
separate vector service. Reconsider only after a measured resource or capability
limit, not because those names appear in larger deployments. Keep authentication
in its existing system rather than adding another hosted identity provider.

## LAYA and JEV: where they actually fit

LAYA predicts typed choices, scores and yes/no-style probabilities in a forward
pass. Its repository offers English and multilingual checkpoints; the latter has
about 322 million parameters. Checkpoints download on first use, so local operation
still has disk, RAM and startup costs. [17] At FP32, 322 million parameters alone
are approximately 1.20 GiB; at FP16, about 0.60 GiB, before runtime/activations.
These are arithmetic estimates, not measured process RAM, and neither fits the
existing 256 MiB phone-service cap. A quantized deployment would need its own tests.

The benchmark document attributes roughly 33 ms to a T4 GPU run. It also reports
0.310 Tamil accuracy on its refreshed 20-option MASSIVE intent evaluation, and
notes that its Jev comparisons use different published tests rather than a common
head-to-head run. These results do not establish reliable Tamil/Tanglish routing
for LYA. [19] Structured output can be well formed and still be the wrong choice.

Our experiment should compare existing rules, a small conventional classifier,
and one pinned LAYA checkpoint on the same held-out ordinary intents. Measure
confusion, abstention coverage, p50/p95, cold start, RAM and energy/resource cost on
the actual Oracle ARM CPU and laptop. Include Tamil script, transliterated Tamil,
English, ambiguous requests and option-order changes. Enable only if useful
accuracy/latency improves at the agreed budget. Never let a classification grant
admin access, decide export consent, authorize a purchase, or turn uncertain chat
into permanent memory. A low-confidence result can clarify or fall back safely.

Jev Ultrafast is a browser agent with indexed visible controls. The README describes
selecting an operation and matching target together, then using a text model for
typed content. [18] Source confirms it sends URL/title/page text, element state,
recent actions and goals to TypeSafe; its text helper receives further page/field
context. [20] Running the wrapper locally therefore does not make inference local.

Its performance report measures three paired runs of one Flights task: median
9.450 to 7.092 seconds. Initial navigation/setup and independent final verification
are outside the timed interval. The reported tiny text-helper cost excludes the
TypeSafe and browser costs. The document explicitly limits broader reliability
claims. [21] We have not reproduced any of these results.

The useful design lesson is to reduce redundant browser round trips and choose
from observed, valid targets with freshness checks and independent outcome
verification. For LYA, use direct scoped app APIs first when available; otherwise
evaluate browser automation in an isolated profile, with allowed domains/actions,
data minimization and exact action authorization. Do not attach an unrestricted
personal browser or ship its page contents to a new provider by default. TypeSafe
Jev is the model service; jev-ultrafast is a consuming application. [22]

Recommendation: LAYA is a conditional experiment in step 8; Jev Ultrafast belongs
to step 10 only when browser work is requested. Neither is required for durable
memory, shared identity or fast delivery of text between devices.

## Fast transfer: select by traffic type

| Traffic | First choice | When another option earns its place |
|---|---|---|
| Memory reads/writes and ordinary commands | Small validated UTF-8 JSON over existing private HTTPS | Protobuf only when measured serialization/bandwidth cost warrants generated schemas |
| Incremental answer text and progress | HTTPS streamed response using SSE framing, consumed through fetch; separate POST for cancellation | WebSocket if sustained bidirectional messages are actually required [13] |
| Current voice clips | Preserve existing bounded WAV path while measuring it | Then qualify binary/chunked output or a supported compressed codec with provider and iPhone tests |
| Continuous interactive voice | Future WebRTC/Opus prototype | Use only for an approved continuous-audio requirement; it does not remove ASR/model/TTS work [14] |
| Local gateway to local worker | Existing pipes, or a narrow local socket if worker reuse is qualified | No remote broker required merely to communicate within one host |
| Larger files and backups | Resumable encrypted transfers, bounded concurrency, integrity verification | Outside the conversation worker and bandwidth budget |
| Many independently deployed backend services | Defer gRPC/Protobuf | gRPC provides typed services/streaming; set deadlines and cancellation, and account for browser integration [15] |

SSE sends events server-to-client; requests and cancellation still use authenticated
POSTs. Native EventSource does not send a POST body, so the proposed POST streaming
endpoint needs a tested fetch stream reader. Bound event sizes, partial UTF-8
buffers and concurrent streams; disable intermediary buffering as appropriate.
Reconnection must never replay a write or restart model work implicitly.

The browser WebSocket API lacks automatic backpressure. If selected later, bound
queued bytes and drop obsolete audio on cancellation. A stream needs session
expiry/revocation enforcement while open, not just at connection establishment.
Test origin/CSRF rules on cookie-authenticated operations. [13]

Tailscale direct connections usually reduce latency compared with a relay, but
direct connectivity depends on NAT and networks. Diagnose it without weakening
the firewall or exposing LYA publicly. Transport encryption protects traffic;
Oracle still sees shared records it is trusted to process. [2]

Do not infer speed from product advertising. For example, reducing a 20 KiB
message to 5 KiB at a hypothetical 10 Mbit/s saves about 12.3 ms of serialization
onto the link, excluding RTT and overhead. It does not remove a seconds-long model
or speech stage. Protobuf is a serialization format; JSON is a representation;
HTTPS/WebSocket/WebRTC carry data; these are different layers. [16]

## The workflow to build

1. Device sends a bounded request with a unique ID and schema version. Server
   derives owner, grant and project from verified authority, not prompt text.
2. Apply deadline, privacy route and cancellation; clarify uncertain input before
   a consequential action. ASR partials may help display, not authorize writes.
3. Select direct command, explicit save/correct/forget, supported recall, or an
   eligible model. A stored preference may be answered without an LLM.
4. Retrieve a small scoped evidence set, including source, current revision,
   validity and expiry. No matching evidence is a valid outcome.
5. Produce checked text incrementally where safe, then sentence audio after its
   relevant gates pass. Do not read provisional commands or unsupported claims as
   confirmed results. Context-dependent answers may require buffering.
6. For writes, atomically commit fact, provenance, revision and background job;
   say "saved" only after commit. A lost acknowledgement is recovered through the
   request ID. Concurrent edits use expected_revision and explicit conflicts.
7. Independently process permitted embeddings, Notion exports and recovery work.
   Connector failure does not block the core reply. Show saved-versus-exported
   status separately; a new save is not automatically already backed up.

For accurate transmission, use validated types/lengths, request IDs, sequence
numbers, revisions, transaction acknowledgements and hashes for files. TLS does
not establish factual truth. Accurate answers additionally need source support,
temporal correctness, speech tests and abstention. These are separate tests.

An external edit is an import proposal with provenance and conflict handling; it
cannot silently overwrite an approved memory. Forgetting must reach search,
caches, exports and the deletion register used in recovery. Notebook trash and
backup retention mean physical erasure may lag logical deletion.

## The order to implement

| Order | Deliverable | Evidence required before the next dependent step |
|---|---|---|
| 1 | Confirm free-resource budget, selected shared-memory placement, recovery destination and key custody | Account limits checked; concrete data scope; no existing private vault migration implied |
| 2 | Baseline timing and resource measurements with synthetic inputs | Endpointing, upload, queue, ASR, retrieval, model first/final output, TTS first/final audio, download/playback; p50/p95, cold/warm and network conditions |
| 3 | Shared request/identity/style contract with fake data | Implemented and isolated-tested: [contract slice](../2026-10-11-conversation-contract/README.md), 10 new checks/46 combined pass, shared style and separate sessions. Production paths not connected; fake stable-owner mapping now covered in order 4. |
| 4 | Isolated durable memory API and storage comparison | [SQLite semantics baseline](../2026-10-11-memory-prototype/README.md) implemented: 19 new/29 combined checks, restart/correction/conflict/retry/expiry/forget, child-process crash and SQLite-full rollback, 1,000 synthetic records. Plaintext fake-only; PostgreSQL/SQLCipher comparison and live engine choice remain open. |
| 5 | Recovery before valuable records | [Isolated encrypted recovery](../2026-10-11-memory-recovery/README.md): 17 new/46 combined checks; consistent WAL snapshot, authenticated encryption, latest-anchor requirement, later-deletion/expiry suppression and quarantined restore. Live DB remains plaintext; independent destination, key custody, checkpoint acknowledgement, writer fencing and clean-host restore remain open. |
| 6 | Connect both devices to approved new shared records | Laptop save -> phone recall, phone correction -> laptop update, laptop-asleep recall, forget on both; visible persistence failures |
| 7 | Retrieval and answer quality | Held-out Tamil/English/transliteration, dated facts, ambiguous entities and unanswerable cases; tune optional embeddings only if they help |
| 8 | Measured latency improvements and optional LAYA routing experiment | Test text streaming, bounded worker reuse, sentence audio and binary payloads individually; compare LAYA with rules only if routing is costly; preserve accepted pause/voice/Stop and memory limits |
| 9 | One selected Notion/export connector, then file integration | Narrow scopes, retry/backoff, revision ordering, deletion propagation, outage isolation and visible export status |
| 10 | Resumable tasks and additional app adapters | Minimal job state first; choose LangGraph/n8n/MCP or a Jev browser experiment only for demonstrated needs, with action authorization and uncertain-outcome recovery |
| 11 | Optional continuous voice / native iPhone actions | Separate LiveKit/Pipecat/WebRTC or App Intents evaluation; owner acceptance before replacing any working interaction |
| 12 | Growth and maintenance | Larger corpus/load tests, upgrade/rollback drills, backup-budget checks and measured resource ceilings |

Orders 2-5 can be designed/tested with fake records before external placement is
approved. Live personal writes depend on orders 1 and 5. Speed instrumentation
starts early; risky voice changes wait for evidence and isolated qualification.

The current source supports investigating full-result waits and repeated worker
startup: cloud/mobile_runtime.py infer/speak use subprocess exchange; mobile.html
api waits for response JSON before rendering/playback. This is source evidence,
not a measured claim that startup or network transfer is the largest bottleneck.
The existing phone service has a 256 MiB cap with a previously near-cap voice test;
do not preload more models into it without a separate resource experiment.

Retain the earlier target budgets as goals, not promises: p95 direct text under
500 ms; model first text under 1.5 s and first voice under 2.5 s from confirmed turn
end; also report total delay since the last spoken word. Record failures and timeouts
in the denominator. Compare quality and resources at the same time as speed.

## Primary sources checked in this pass

1. [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).
2. [Tailscale connection types](https://tailscale.com/docs/reference/connection-types).
3. [pgvector filtering and iterative scans](https://github.com/pgvector/pgvector); [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html). Application DB roles must not bypass row security.
4. [restic repository design](https://github.com/restic/restic/blob/master/doc/design.rst); [integrity checking](https://restic.readthedocs.io/en/stable/045_working_with_repos.html). A repository check is not a successful application restore.
5. [rclone crypt](https://rclone.org/crypt/).
6. [Notion API limits](https://developers.notion.com/reference/request-limits): currently 180 requests/minute for non-Business/Enterprise connections, plus workspace/endpoint limits; respect Retry-After.
7. [Obsidian local storage](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data), checked in the preceding platform pass.
8. [OpenTelemetry sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/).
9. [MCP security best practices](https://modelcontextprotocol.io/docs/draft/tutorials/security/security_best_practices). Draft guidance informs risks; pin a supported protocol version during implementation.
10. [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence).
11. [n8n queue mode](https://docs.n8n.io/deploy/host-n8n/configure-n8n/scaling/enable-queue-mode.md).
12. [LiveKit deployment](https://docs.livekit.io/transport/self-hosting/deployment/).
13. [MDN server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events); [WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API).
14. [MDN WebRTC](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API).
15. [gRPC concepts](https://grpc.io/docs/what-is-grpc/core-concepts/); [deadlines](https://grpc.io/docs/guides/deadlines/).
16. [Protocol Buffers overview](https://protobuf.dev/overview/).
17. [LAYA repository](https://github.com/NandhaKishorM/laya).
18. [Jev Ultrafast repository](https://github.com/browser-use/jev-ultrafast).
19. [LAYA benchmark evidence and limitations](https://github.com/NandhaKishorM/laya/blob/main/BENCHMARKS.md).
20. [Jev model adapter source](https://github.com/browser-use/jev-ultrafast/blob/main/jev_ultrafast/model.py).
21. [Jev performance report](https://github.com/browser-use/jev-ultrafast/blob/main/docs/performance.md).
22. [TypeSafe Jev introduction](https://docs.typesafe.ai/introduction).

This pass used primary-source web fallback because the Agent Reach backend was
unavailable in the earlier checked environment. No external account quota, new
vendor benchmark, live latency, private provider transmission, installation or
deployment was performed. LAYA/Jev source and maintainer benchmarks were reviewed;
their dependencies and models were not installed or executed. Moving main-branch
documents may change; pin code, model and dependency revisions for any prototype.
