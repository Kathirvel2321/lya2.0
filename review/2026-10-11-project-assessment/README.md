# LYA whole-project assessment

Date: 2026-10-11

## Scope

This is a read-only review of the current checkout. It covered the project brain,
vision, architecture and roadmap documents; the native desktop, Brain workflow,
storage, recovery, security, mobile and external-work paths; current Git status and
diff; and the documented isolated tests. No product behavior was changed.

The repository is substantial: the current Git index contains 684 tracked paths,
including 227 Python files and 248 review paths. The working tree also contains
many intentional local additions and modifications, so the assessment uses the
current checkout rather than treating `HEAD` as the whole product.

## Verification performed

- `git diff --check`: passed; Git reported only line-ending warnings.
- `python -B -m compileall -q brain cloud desktop security storage skills audio main.py`: passed.
- Recent shared-contract/mobile/memory/recovery selection: **73 tests passed**.
- Selected existing foundation/project-memory/recovery selection: **47 passed, 1 failed**.
- The failing test is `test_project_memory.ProjectMemoryChecks.test_ordinary_project_question_keeps_the_existing_conversation_route`.
  It expects `private-local` for `project ideas for a simple game`, while the current
  workflow returns `model`. This is a real contract/documentation drift signal and
  was not changed during this review.

The runs used the existing `.venv-ui` interpreter, fake credentials, synthetic
passkeys, fake providers and temporary stores. They were not a full repository
discovery run and did not prove real-device, live-model, billing, load or production
readiness.

## What is strong

### 1. The safety boundary is much better than the average personal-assistant prototype

The project repeatedly keeps identity, permission and model output separate. The
policy is default-deny for unknown capabilities; private operations require an
identified owner and exact approval; names, color palettes and friendly language do
not grant authority; generated skills cannot activate themselves; and private
context is omitted from guest/public prompts. The mobile path adds origin/RP checks,
WebAuthn verification, replay/counter checks, bounded sessions, request limits,
Stop handling and no-store headers.

These are not just comments. The isolated tests exercise revocation, expiry,
replay, cancellation, stale replies, malformed input, scope separation and bad
provider output. That is a genuine engineering strength.

### 2. The project has unusually honest evidence discipline

The dated brain ledger, separate review artifacts and repeated distinction between
implemented, isolated-tested, live-tested, blocked and deferred work are excellent.
The project does not casually convert a mock pass into a product claim. Fake data,
temporary stores and explicit limits are used consistently. This makes the project
much easier to audit and continue safely.

### 3. The native interface has a clear identity

The PySide6 crystal/orb, glass panel, task-state visuals, reduced-motion support,
accessible labels, bounded document preview and off-UI-thread work form a coherent
product direction. The UI feels like an assistant rather than an admin dashboard.
The mobile page is also moving toward the same visual language instead of becoming
an unrelated second product.

### 4. The memory and recovery thinking is serious

Explicit saves, retention, revisions, project/person isolation, correction,
forgetting, outbox state, idempotent receipts and deletion-aware restore are the
right concepts for a long-lived assistant. The recovery prototype correctly treats
later deletion/expiry and unavailable newer values as important, and quarantines
restored access rather than reviving credentials automatically.

### 5. Scope boundaries are generally responsible

The project is cautious about cameras, biometrics, phone access, provider keys,
work-managed devices and free-tier resources. The external voice lab is isolated
from the main runtime, and the public archive is kept separate from private memory.
Those choices reduce the chance of a prototype silently becoming a risky system.

## What holds the project back

### 1. The biggest problem is integration, not imagination or coding ability

LYA currently contains several good systems that are not yet one system:

- The production desktop Brain uses the existing encrypted `storage.store` and
  `brain.notes` path.
- The production mobile connection uses a separate RAM-only public conversation
  history in `cloud.mobile.Connection`.
- `brain.conversation`, `brain.memory_prototype` and `brain.memory_recovery` are
  deliberately isolated and disconnected from production chat.
- The full neural/shared-memory design remains a proposal, even though many of its
  components exist in source.

So the project has strong parts, but the central promise — one logical LYA with the
same trusted identity, personality and selected memory across laptop and phone — is
not complete yet.

### 2. The end-to-end product is still prototype-level

The current evidence does not establish all of the owner experience: real iPhone
voice/Stop/owner-proof behavior, laptop-asleep operation, live memory save/recall
across devices, real enrollment, sustained resource behavior, full-repository
regressions, and dependable independent model backup. The current mobile release is
best described as a bounded public conversation service, not a full remote LYA.

### 3. The repository has accumulated too many generations and parallel paths

There is an older Tk/native runtime, the newer PySide6 desktop runtime, legacy
browser/cloud/skill paths, multiple face approaches, multiple voice approaches and
several research-era designs. The documentation itself records that some older
architecture statements are historical. This is understandable for an evolving
project, but it raises maintenance cost and makes it harder to answer a basic
question: “Which path is the product?”

The stale or historical material is useful evidence, but it should be visibly
separated from the current canonical path. Otherwise future changes can repair an
orphaned implementation or trust an old status table.

### 4. Tests are strong in depth but uneven in coverage

The recent focused suites are high quality. However, the project intentionally does
not run blanket legacy discovery because some scripts can touch real stores, and the
full repository/Linux/device/load matrix is not complete. The one current failure
also shows that the expected behavior and implementation can drift even when many
security tests remain green.

### 5. “Encrypted” is not yet one consistent operational property

The accepted Windows store uses DPAPI-wrapped encryption, while the new memory
prototype is explicitly plaintext fake-data SQLite and only its backup/checkpoint
files are encrypted. Independent recovery destination, key custody, checkpoint
acknowledgement, writer fencing and clean-host restoration remain open. That is a
reasonable development sequence, but it means valuable shared records should stay
out of the new path until those gates pass.

## My overall opinion

This is a thoughtful, unusually careful and technically ambitious project. The best
part is not the futuristic styling or the number of features; it is the refusal to
let model output, a face match, a phone token or a passing fixture silently become
authority. The project shows real systems engineering judgment.

My honest classification is:

- **As an engineering project:** strong and serious, roughly **8/10**.
- **As a finished personal assistant:** promising but incomplete, roughly **4/10**.
- **As a production-ready secure product:** not ready yet, mainly because the
  integrated authenticated memory/device journey and operational recovery are not
  proven.

The project is not failing because it lacks more features. It needs one canonical
vertical slice to become real.

## Recommended next priorities

1. **Declare the canonical runtime.** Keep PySide6 desktop + the current private
   mobile service as the product paths. Mark older Tk/browser/legacy modules as
   historical or isolate them so they cannot be mistaken for active behavior.
2. **Resolve the current contract drift.** Decide whether an ordinary “project
   ideas” question should use the model route or private-local route, then update
   the implementation or expectation and add the decision to the ledger. Do not
   leave the one failing regression unexplained.
3. **Finish the smallest one-LYA slice.** First target public conversation identity
   and style across desktop/phone. Then connect only explicitly saved facts and
   preferences, with one stable owner mapping, one retention contract and one
   tested save/correct/forget/expiry flow.
4. **Qualify storage and recovery before valuable records.** Complete encrypted live
   storage, independent key/backup custody, latest-checkpoint acknowledgement,
   writer fencing and a clean-host restore drill.
5. **Run a short real acceptance matrix.** Test the actual iPhone, Stop, voice,
   owner proof, laptop asleep/offline, and one harmless cross-device memory journey.
   Record each as PASS, FAIL, BLOCKED or NOT RUN.
6. **Only then expand.** Camera/visitor features, broader actions, external
   platforms, generated skills and optional model experiments should follow the
   stable vertical slice rather than compete with it.

## Conclusion

Keep building it. LYA has a real foundation and a distinctive product idea. The
next improvement should be consolidation and live proof, not another large feature
or another architecture proposal.
