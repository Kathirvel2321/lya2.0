# GitHub checkpoint publication - 2026-10-13

Owner explicitly requested staging, committing and pushing all current project work. Preserve working files and existing main branch; do not reset, clean, switch main, merge or deploy.

Planned publication:

- Parent main-checkout work (organization/archive moves, maintained docs, mobile history, memory/recovery/custody/witness prototypes, tests and recorded evidence) to `codex/lya-project-checkpoint-20261013`, starting from `1d7b5c1`.
- PR #3 visual model, native laptop evidence and offline glass preview to its existing `codex/lya-visual-prototype-20261013` branch, starting from `6ba5694`.

Remote main is left unchanged. Both publications use ordinary non-force pushes. The visual branch remains separate; no cross-branch merge or deployment.

Publication preflight: [preflight.json](preflight.json) checks 563 main and 65 visual candidate files for private-key blocks, GitHub/provider tokens and AWS access IDs; zero matches. This is a targeted publication check, not a complete security audit. Existing ignore rules keep local Python/model environments, keys, protected stores, recordings, private test folders and operator settings out. Portable Blender download/extraction sits outside both Git checkouts; the redundant `.blend1` backup stays local. Existing images/archive evidence are project artifacts or already tracked historical material; archives were inventoried but not executed.

Two embedded repositories have pre-existing dirty contents (`security/Silent-Face-Anti-Spoofing` and `lya-external-work`). Their directories and existing gitlinks are left intact; their nested changes are not captured by parent-repository staging or published to their upstream repositories. No external dependency repository is changed by this publication.

Validation scope: reuse the recorded completed development checks, check staged content and source syntax, and verify actual remote commit IDs after push. No full-repository rerun or additional deployment/device claim is made. Publication receipts will be recorded after the pushes succeed.

Resumed 2026-10-14 after the automatic approval reviewer previously could not run due to an account usage limit; the blocked action was not executed then. Rechecked the unchanged empty main index lock dated 2026-10-12 with no Git process running, removed only that stale lock under authorized execution, and staged the parent snapshot. [Staged validation](staged-validation.json): 566 parent files and 64 visual files scanned, zero specified token/key-pattern matches; 32 active parent Python files and four visual Python files parse. Staged whitespace checks pass. Remote main and visual head matched their starting commits, and the checkpoint branch did not exist. No archived script was executed.
