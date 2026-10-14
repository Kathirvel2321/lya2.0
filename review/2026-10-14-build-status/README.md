# LYA build status and next decisions — 14 October 2026

Owner requested a clear whole-plan account of what is built, what remains, what is actually connected, and whether to create production keys before continuing. This is a source/documentation/evidence review. No application, remote service, sensor, account or provider was exercised; no new product behavior or test run is claimed. Existing deployment records are dated evidence, not a fresh uptime check.

Later same-day follow-up: the owner approved implementing the next slice. The [durable network authority coordinator](../2026-10-14-memory-network-authority/README.md) now connects the isolated authority to the localhost witness with durable intent, generation fencing and approved reconciliation. The adapter-pending references below are the earlier assessment; the linked report supersedes them and records this revision's checks and limitations. The status map now shows that local connection as implemented. Independent hosting, TLS, production keys and shared-device integration remain pending; the test-key recommendation continues to apply.

## Recommendation on keys

Continue the durable network-authority adapter with disposable generated test keys and fake records. These tests use actual encryption/MAC algorithms and normal randomly generated key material; "fake" describes disposable fixtures and their non-production purpose, not a weakened encryption algorithm. Creating production keys early would not supply the missing adapter, independent placement, protected custody, rotation or successful real restore.

Prepare password-manager selection and operator instructions separately. Generate fresh production keys locally only for an approved pilot after the intended storage/custody path is ready, then prove owner save/retrieval and recovery before valuable records. Do not promote test keys, reuse one key across purposes, or paste secrets in chat. [Fernet's official documentation](https://cryptography.io/en/stable/fernet/) explains that losing a key prevents decryption and disclosure permits reading/forging its protected messages. Actual secret configuration belongs in protected local/operator setup, not source or this ledger. Real-key setup is not authorized or performed by this status review.

## Existing clients versus new foundations

| Area | Built / evidence | Current boundary and work left |
| --- | --- | --- |
| Windows desktop | Accepted PySide6 client, crystal/panels, hearing/speech and existing workflow/device choices remain in `desktop/`, `audio/` and `brain/workflow.py`. | Existing implementation; not freshly launched or device-tested today. The new shared-memory prototypes are not connected. |
| Phone conversation | Existing public-text/voice path, private HTTPS/passkey sessions, expiry/revocation and pause/Stop behavior have deployment evidence. [Timing release](../2026-10-11-foundation/README.md) includes activation/proxy checks. | Current uptime and real iPhone microphone/keyboard/passkey/Stop experience were not rechecked. Laptop-off acceptance remains pending. No shared private memory. |
| Latest phone history/edit | Up to 12 page-memory exchanges and latest-question edit/resend; [40 simulated scenarios and 12 headless layouts](../2026-10-12-mobile-history/README.md) passed. | Local implementation; its release to the phone page and real Safari acceptance remain pending. The earlier report's "not pushed/committed" wording predates the later checkpoint publication; Git publication does not deploy it. |
| Existing private/public data boundary | Local protected vault/notes, separate public archive and native/session authority code remain. | No private-vault migration, new owner/biometric enrollment or private provider export was added. Existing private routing is not a new full shared-data service. |
| Shared conversation contract | Isolated typed public turn, request IDs, style, identity/session checks, expiry and cancellation; [contract evidence](../2026-10-11-conversation-contract/README.md). | Not wired into both production clients. It provides no private memory by itself. |
| Selective memory API | Explicit save/get/search/correct/forget, owner/project scoping, revision numbers, retention/expiry, idempotent receipts and outbox rows; [prototype](../2026-10-11-memory-prototype/README.md). | Tested with fake data. No production capture/recall, complete target evidence/entity graph, semantic index or running outbox worker. |
| Encrypted storage candidate | Optional SQLCipher live/staging path, wrong-key/plaintext-driver rejection, journal/WAL checks and 1,000-record corpus; [hardening](../2026-10-12-memory-hardening/README.md), [Oracle ARM64 slice](../2026-10-13-memory-linux/README.md). | Plaintext baseline/catalogue remain; PostgreSQL comparison and production engine selection are open. Bounded corpus results do not establish large-scale capacity. |
| Recovery and writer authority | Consistent encrypted backup/checkpoint pairs, exact latest anchors, forgotten/expired suppression, quarantine, writer fencing and explicit verified reactivation; [authority/recovery](../2026-10-12-memory-reactivation/README.md). | Fake-data protocol. Encrypted files and trust metadata still lack qualified independent survival, power-loss tests, retention/physical erasure and real identity acceptance. |
| Key capsule and local witness | Authenticated key envelope, pinned capsule digest, checkpoint/epoch witness; optional authority schema-3 binding and durable partial-commit reconciliation; [witness acknowledgement](../2026-10-13-memory-witness-ack/README.md). | Production keys/password manager are not configured. Existing local witness transaction is a local mechanism, not a remote protocol. |
| Authenticated network-style witness | Signed scoped requests/replies, fresh nonces, durable reservation generations, bounded receipts, lost-reply/process-death handling; [service lab](../2026-10-14-memory-witness-service/README.md). | Localhost prototype only. Authority adapter, TLS, independent hosting and production integration remain pending. The authority intentionally rejects this client as its current witness. |
| Linux lab | Ubuntu WSL 2, separate home-folder Python environment, selected source copies and owner-run portable checks. | Development environment with Windows integration; not a hard sandbox or qualification of the whole Windows desktop/voice/vault on Linux. |
| Measurement | Content-free stage timing deployed; fake-provider HTTP baseline and isolated failure cases; [foundation](../2026-10-11-foundation/README.md). | No real speech/model/network p50/p95/cold-start acceptance, first-token/audio streaming or qualified worker reuse. |
| Source and explanations | Old/failed/historical material moved into `archive/`; maintained documentation index and move manifest; [organization evidence](../2026-10-12-project-organization/README.md). | Archive stays outside execution/discovery. This is organization, not proof that every runtime path is correct. |
| Visual work | Standalone concept assets and separate visual draft-branch refinement/evidence are preserved. [Checkpoint publication](../2026-10-13-github-checkpoint/README.md). | A concept or pushed visual branch is not integration into the accepted main client. Preserve accepted visuals until explicit review/integration. |

## Evidence that is green, with its limits

- [75 selected Windows memory checks](../2026-10-13-memory-witness-ack/validation.json): authority/reactivation/custody/storage plus 18 local witness-integration checks; no failures/errors/skips.
- [38 owner-reported WSL portable checks](../2026-10-13-memory-witness-ack/wsl-user-reported-validation.json): a portable selection overlapping that Windows run, not 38 additional unique checks.
- [18 Windows localhost protocol checks](../2026-10-14-memory-witness-service/validation.json) and [the same 18 owner-reported WSL cases](../2026-10-14-memory-witness-service/wsl-user-reported-validation.json): separate platform observations of the new service prototype.
- Earlier native/mobile/corpus/recovery results are preserved in their dated reports. No grand total, current full-suite pass, penetration-test certification or flawless-product claim is inferred from overlapping selections.

The owner supplied WSL terminal results; the assistant did not independently rerun those environments or measure their copied source hashes. This review verifies selected local source hashes against the prior test reports and records its own documentation/diagram checks in [validation.json](validation.json).

## Coverage of the eight original diagrams

The [architecture atlas](../2026-10-11-system-architecture/index.html) remains a target design. Its arrows are not an integration checklist automatically completed by test success. The new [status map](current-status.mmd) separates retained clients, isolated tested pieces and pending connections; green means existing implementation/deployment evidence, blue means isolated prototype, amber means pending. None of these colours is a fresh uptime measurement.

| Original diagram | Implemented coverage | Remaining target |
| --- | --- | --- |
| [01 Whole system](../2026-10-11-system-architecture/01-whole-system.mmd) | Existing clients/private boundary/public routes; isolated shared contract and memory/recovery foundations. | One connected shared brain, selected production store, scoped evidence/compiler and background services. |
| [02 Answer sequence](../2026-10-11-system-architecture/02-answer-sequence.mmd) | Existing complete text/voice replies; isolated turn validation and cancellation. | Shared authorized retrieval into replies, supported evidence handling and qualified sentence/text streaming. |
| [03 Memory lifecycle](../2026-10-11-system-architecture/03-memory-lifecycle.mmd) | Fake-data save/correct/forget/expiry, revision conflicts, receipt retries, outbox rows and deletion-aware restore. | Production lifecycle, worker/index/export propagation, backup retention and physical purge. |
| [04 Data model](../2026-10-11-system-architecture/04-data-model.mmd) | Prototype owner mappings, scoped facts, revision counters, request provenance, jobs/deletions. | Full evidence/source relations, temporal history, entities, embeddings, attachments and target-engine migration. |
| [05 Platform trust](../2026-10-11-system-architecture/05-platform-trust.mmd) | Retained local vault, paired public phone boundary and synthetic scope checks. | Approved shared private-data placement, restricted service accounts, new egress integration, independent custody and real-device checks. |
| [06 Recovery](../2026-10-11-system-architecture/06-recovery.mmd) | Encrypted snapshot verification, quarantine, exact latest state, old-writer rejection, local witness and isolated network protocol. | Durable network authority adapter, independent backup/catalogue/key survival, clean-host/power-loss recovery and rotation/retention. |
| [07 Model routing](../2026-10-11-system-architecture/07-model-routing.mmd) | Existing deterministic/public/private routing choices are retained. | Unified memory-aware routing, held-out Tamil/English/Tanglish quality/abstention, qualified fallback and any optional new routing model. |
| [08 Fast workflow](../2026-10-11-system-architecture/08-fast-workflow.mmd) | Deployed stage timing and prototype committed outbox rows. | Real latency baseline, streaming/worker optimizations, bounded background work, optional exports and independent scheduled recovery. |

## Smart next order

1. Implement and test the durable network-authority adapter with fake data. Prove source commit/reservation reconciliation, cancellation and stale-writer rejection across restart and dropped replies.
2. Prepare the password-manager/operator workflow, choose a concrete independent witness/backup placement and verify its free allowance, survival scope and service budget. These decisions must preserve phone use when the laptop is off.
3. Qualify restricted hosting and TLS with synthetic data, generate fresh protected production keys locally for an approved pilot, and prove owner save/retrieval plus independent restore before valuable records.
4. Connect both accepted clients in an isolated fake-data shared-record pilot. Demonstrate laptop save/phone recall, phone correction/laptop update, forgetting on both, laptop-off access, expiry/revocation and visible failures before a separately approved real-record rollout.
5. Finish quality, maintenance and failure qualification: held-out retrieval/answers, realistic load/disk admission, orphan cleanup, retention/deletion propagation, upgrade/rollback and power-loss/clean-host tests. These are production gates, not optional polish; qualify them before valuable records depend on the service.
6. Measure real delays before adding streaming/worker changes. Optional semantic retrieval, graph enrichment, Notion/files, resumable jobs, MCP/LangGraph/n8n, LAYA/Jev or continuous voice stay deferred until a demonstrated need justifies them. They are not all mandatory installations.

The existing private phone page's local history/edit changes and separate visual work have their own release/owner-acceptance paths; completing a memory step does not authorize deploying those features.

## What "clean" currently means

Source/history organization and the selected checks have positive evidence. The whole connected assistant has not passed fresh full-system acceptance. A [recorded 11 October route-contract mismatch](../2026-10-11-project-assessment/README.md) (`project ideas for a simple game`) remains an unverified finding; it was not rerun or fixed in this review. Current Git status includes new protocol/documentation work and two pre-existing dirty embedded repositories; that is not a clean checkout, nor by itself evidence that the app is broken. No unrelated feature was changed to make this report look green.

No production keys, additional account, independent hosting or private migration is required to complete the next fake-data development step. No code, test suite, live service, account or deployment was changed by this assessment.
