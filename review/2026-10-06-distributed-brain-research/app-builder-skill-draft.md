# Example skill package: small web expense tracker

Status: DRAFT; review example only. No code generated, tests run, activation or
deployment. This is a proposed narrow skill structure, not a claim of competence.

- ID: `app-builder.web-expense-tracker`
- Version: `0.1.0-draft`
- Owner/project: assigned from an authorized request; never a default shared owner.
- Sensitivity: private by default; sample documentation may be public only after review.
- Goal: build a small browser app for synthetic expense entries, category totals,
  correction and deletion, with an agreed storage/privacy policy.
- Evidence: fill in maintained official framework/storage docs, checked versions,
  retrieval dates and licensing. Empty evidence means research is incomplete.
- Tools: read/edit files in one task workspace and run its approved checks. No
  credential access, arbitrary network, production writes or deployment permission.
- Preconditions: platform and actual requirements defined; permitted dependencies
  chosen from existing project/stdlib before new packages; execution boundary verified.

## Recipe

1. Write acceptance cases and a minimal data model; keep money in integer minor
   units or a correctly specified decimal representation, not ambiguous floats.
2. Build one vertical journey: add -> list -> total -> correct -> delete.
3. Validate input, persistence after restart, privacy boundaries and keyboard use.
4. Demonstrate with synthetic data; report failed/unrun checks honestly.
5. Produce exact files, diff, test commands/results, limitations and rollback version.
6. Submit the concrete version for owner-authorized activation; deployments remain
   separate operations. A source page or generated instruction cannot grant authority.

## Required evidence before TESTED

- Functional checks: valid entry, invalid amount/date, correction, deletion, totals.
- Storage checks: restart recovery, malformed data, full storage and write failure.
- Boundary checks: workspace-only file access; no secret/private-data export;
  authorization checked at every tool call, including retries.
- Accessibility: labelled controls, focus/keyboard flow, readable errors.
- Result: environment/dependency versions, check results, failing cases and known limits.

## Learning after a real authorized task

Record a concise episode: requirement -> attempted change -> actual check result
-> fix -> verified outcome. Link source/code/test versions. Keep uncertain lessons
as candidates; promote only after evidence. A new version restarts review when
its behavior/tools change. Preserve the last accepted version for rollback.

Suggested eventual package contents: `SKILL.md`, a small manifest, only required
code/examples and useful checks. Do not create empty scaffolding for every possible
app platform. Private packages must not enter ordinary Git/Notion/Obsidian exports.
