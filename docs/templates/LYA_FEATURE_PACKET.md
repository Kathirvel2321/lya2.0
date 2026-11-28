# LYA feature packet

Copy this file for one feature. Keep the scope small enough for one branch and
one review.

## Feature

- **Name:**
- **Owner outcome:** What should the user observe?
- **Reason now:**
- **Status before work:** Specified / Implemented / Connected / Tested / Pending

## Scope

- **Allowed files or directories:**
- **Required integration point:**
- **Related source of truth:** Blueprint section, guide, plan or architecture link
- **Out of scope:**

## Contracts to preserve

- **User/interface:**
- **Identity/approval:**
- **Privacy/data boundary:**
- **Storage/retention:**
- **Voice/hearing/mobile behavior:**
- **Existing failure and cancellation behavior:**

## Implementation requirements

1. Read `lya-project-brain.md`, `LYA_VISION.md`, `docs/LYA_BLUEPRINT.md` and the
   related files before editing.
2. Reuse existing helpers and contracts where possible.
3. Use fake identities, fake secrets and temporary storage in tests.
4. Do not access, print or commit real secrets or private runtime data.
5. Do not change unrelated working behavior.

## Acceptance

- **Focused checks to run:**
- **Regression checks to run:**
- **Manual/device check, if any:**
- **Expected failure/denial cases:**
- **Evidence artifact path:**

## Handoff

- **Changed files:**
- **Tests and results:**
- **Implemented versus connected versus deployed:**
- **Known limitations or blocked prerequisites:**
- **Rollback approach:**
- **Next integration step:**
