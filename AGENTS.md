# LYA project continuity

For work in this project, read `lya-project-brain.md` first, then the relevant source and `LYA_VISION.md` as needed. Treat recorded status as dated evidence, not proof of current behavior.

## Preserve working features - owner rule (2026-10-05)

- Do not change a working or owner-accepted feature unless the owner explicitly asks to change that feature.
- A question asking why something happens, or asking for status, is not permission to change its behavior.
- Keep requested work within its named scope. Do not redesign, refactor, replace models, change defaults/startup, or "improve" adjacent working features opportunistically.
- If a problem is found outside the requested scope, report it and wait for an explicit change request. If the requested scope is unclear, clarify before editing working behavior.
- Preserve working voice, hearing, interaction and interface choices. Do not roll them back or replace them without a specific owner instruction.
- Necessary checks and project continuity updates may accompany the authorized change; they do not authorize additional product changes.

After each meaningful development task:
- Update the project brain's affected status/findings and append a dated work-ledger entry.
- Record what changed, file/artifact paths, decisions, checks run, results, limitations and the next step.
- Save generated project artifacts to an appropriate workspace location and link them in the ledger. Preserve existing artifacts unless replacement is intended.
- Keep source code and large outputs in their own files rather than duplicating them in the brain.
- Never store credentials, biometric material or private runtime facts in the plaintext ledger. Record safe summaries and protected locations instead.
- Distinguish implemented, tested, blocked, deferred and legacy work. Do not claim an integration works from isolated tests alone.

Use isolated tests with fake secrets and temporary storage. Read older test scripts before executing them; some may modify real stores. Enrollment remains deferred under the recorded requirements until the owner requests enrollment setup.

These instructions maintain project documentation; they do not authorize new runtime data collection, external transmission or deployment.
