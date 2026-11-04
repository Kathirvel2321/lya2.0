# LYA development blueprint

Updated: 2026-11-04

This is the concise coordination map for building LYA safely from different devices,
branches and coding assistants. It is an index and a set of contracts, not a
replacement for the source code, `lya-project-brain.md` or `LYA_VISION.md`.
Recorded status is dated evidence; a fresh check is required before claiming
that a path currently works.

For the complete architecture, request-flow, data-contract and AI-agent
reference, use the [advanced master blueprint](LYA_ADVANCED_MASTER_BLUEPRINT.md).

## 1. Required reading order

Before changing code, read:

1. [`lya-project-brain.md`](../lya-project-brain.md) — binding owner
   requirements, current status, limits and work ledger.
2. [`LYA_VISION.md`](../LYA_VISION.md) — product direction and accepted
   interaction, privacy and authority choices.
3. This blueprint — development boundaries and handoff rules.
4. The relevant maintained guide, architecture document, plan and tests.
5. The latest dated evidence for the affected capability.

`archive/` is historical reference only. Do not import, execute or use archived
scripts as current runtime or test sources.

## 2. System map

| Area | Current source of truth | Integration boundary |
| --- | --- | --- |
| Native desktop and visual presence | `desktop/`, `ui/`, `audio/` | Preserve the accepted orb/crystal, voice, hearing and startup choices unless the owner explicitly requests a change. |
| Conversation and orchestration | `brain/workflow.py`, `brain/conversation.py`, `brain/verification.py` | Route through existing contracts; do not create a second conversation/session policy. |
| Public cloud and mobile | `cloud/`, especially `cloud/mobile.py`, `cloud/mobile_runtime.py`, `cloud/mobile.html` | Keep public answers, mobile session rules and private/shared routes distinct. |
| Shared desktop/phone commands | `brain/shared_memory.py`, `cloud/shared_memory.py` | Use explicit authenticated commands and the existing publication/authority boundaries; do not bypass them with direct database writes. |
| Memory and recovery | `brain/`, `storage/`, `security/` and the maintained memory guides | Treat fake-data qualification, real custody, deployment and production integration as separate states. |
| Identity and authorization | `security/`, `vision/`, phone pairing adapters | Names, face similarity, voice or UI appearance never replace exact owner approval for confidential actions. |
| Automation and routines | `cloud/job_*.py`, `cloud/routine_drafts.py`, `desktop/routines.py` | Draft/review is not activation; preserve default-deny and explicit account/action scope. |
| Research and technology updates | `cloud/web_*.py`, `cloud/tech_news.py`, `desktop/news.py` | Keep fetched content untrusted, bounded and separate from authority or private memory. |
| Local/public storage | `storage/`, `security/vault.py`, `storage/public_archive.py` | Do not export private data to public archives or external services without a separately approved scope. |

For detailed relationships, use
[`LYA_ARCHITECTURE.md`](architecture/LYA_ARCHITECTURE.md) and
[`LYA_BRAIN_WORKFLOW.md`](architecture/LYA_BRAIN_WORKFLOW.md). For task order,
use [`LYA_TASK_ROADMAP.md`](plans/LYA_TASK_ROADMAP.md), not an AI-generated
guess at project priority.

## 3. Non-negotiable engineering rules

- Make the smallest change that satisfies the named feature.
- Preserve working, owner-accepted behavior outside that feature.
- Reuse existing helpers, contracts, formats and permission checks before adding
  new ones.
- Keep public, shared, private and synthetic data paths visibly separate.
- Use fake secrets, fake identities and temporary storage for isolated tests.
- Never request, print, commit or transfer credentials, biometric material,
  private notes, recovery keys or runtime secrets.
- Do not claim a feature is integrated because an isolated helper passed.
  Report separately what is implemented, connected, tested, deployed and still
  pending.
- Do not activate accounts, jobs, cloud storage, phone permissions, enrollment,
  deployment or paid resources unless the owner explicitly scopes that work.
- Do not import or execute anything under `archive/` during normal development.
- Do not rewrite shared history or overwrite unrelated work.

## 4. Change architecture

Every feature must identify:

**Entry point:** where the user or existing client starts the behavior.

**Policy boundary:** identity, approval, privacy and expiry checks required
before the behavior can run.

**Domain implementation:** the smallest reusable module that performs the work.

**Persistence boundary:** what is stored, where, for how long and under which
trust/custody assumptions.

**Client surfaces:** desktop, phone, voice and text paths that must remain
consistent.

**Failure behavior:** timeout, cancellation, stale request, missing dependency,
unknown fact, denied authority and partial commit behavior.

**Evidence:** focused tests, regression tests, manual checks and explicit
limitations.

A feature is not ready to merge if it only adds a helper with no identified
entry point, policy boundary or acceptance evidence.

## 5. Safe multi-device workflow

When working from a phone, work laptop or another coding assistant:

1. Start from the current repository head and create a feature branch.
2. Copy the completed feature packet from
   [`templates/LYA_FEATURE_PACKET.md`](templates/LYA_FEATURE_PACKET.md) into
   the task description.
3. Tell the assistant to read the required files before editing and to stay
   within the allowed scope.
4. Require a small diff, focused tests and a written limitation report.
5. Bring the branch, patch or pull request back for review.
6. Compare the diff with this blueprint and the current project brain.
7. Run the smallest relevant checks, then affected regressions.
8. Update documentation and append a dated work-ledger entry.
9. Merge only after the change is clearly classified as implemented, tested,
   connected, deployed or pending.

An assistant may build a feature separately. It must not invent how that feature
joins LYA; the packet must name the existing contract and integration point.

## 6. Merge decision

Merge when all of these are true:

- The change stays inside the packet's scope.
- Existing accepted behavior is preserved or an owner-approved behavior change
  is explicitly recorded.
- The affected policy and failure paths are tested.
- No secret, private data or unintended dependency is introduced.
- Documentation, project-brain status and work ledger are updated.
- The result states what was not tested or connected.

If a branch changes unrelated working behavior, silently broadens authority, or
cannot explain its integration boundary, stop and return it for correction
instead of merging it.

## 7. Standard assistant handoff

Use this short instruction before the packet:

> You are modifying the LYA repository. Read `lya-project-brain.md`,
> `LYA_VISION.md`, `docs/LYA_BLUEPRINT.md`, and every file listed in this
> packet before editing. Work only inside the allowed scope. Preserve accepted
> voice, hearing, UI, privacy, startup and authority behavior. Use fake data and
> temporary storage for tests. Do not access or print secrets. Do not claim
> integration, deployment or production readiness without evidence. Return the
> changed files, tests and results, known limitations, and the exact next
> integration step.

## 8. Status vocabulary

- **Specified:** requirement or design exists, but implementation is not claimed.
- **Implemented:** source exists for the described behavior.
- **Connected:** an actual supported client reaches the implementation.
- **Tested:** named checks passed on the stated environment and revision.
- **Deployed:** a named runtime/device is running that revision.
- **Accepted:** owner or responsible reviewer confirmed the behavior.
- **Pending:** a required dependency, device, approval, custody or integration
  step remains.
- **Legacy:** retained historical or compatibility code, not a current path.

Use the narrowest truthful label. A passing unit test does not imply connected,
deployed or accepted behavior.
