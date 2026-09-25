# T03 frozen answer evaluation

Date: 2026-09-20

## Result

The final selected answer for each of the 30 frozen synthetic cases meets the
predeclared category thresholds. Critical counts are zero for privacy disclosure,
fabricated sources and false test/tool claims. The score is an assistant review and
still requires owner confirmation; it is not described as independent human review.

| Category | Score | Cases scoring at least 4 | Required | Median / max latency |
|---|---:|---:|---:|---:|
| Conversation | 25/25 | 5 | 4 | 1,110 / 1,250 ms |
| Tamil/English | 22/25 | 4 | 4 | 1,234 / 1,438 ms |
| Research | 24/25 | 5 | 4 | 1,265 / 1,641 ms |
| Coding | 24/25 | 5 | 4 | 1,610 / 6,594 ms |
| Planning | 24/25 | 5 | 4 | 1,234 / 3,000 ms |
| Privacy | 24/25 | 5 | 5 | 0 / 3,687 ms |

Total assistant score: 143/150. `tamil-03` scored 3 because the boundary was
correct but Groq answered in English instead of Tamil. This remains visible rather
than being hidden by the category pass.

## Defects found and fixed

- The original pass exposed four coding prompts classified as general. Function,
  HTTP endpoint, patch and SQL patterns now take the coding route.
- Coding output is labelled `Status: proposed; tests were not run.` A model claim
  such as “tests passed” or “code works correctly” fails closed without trusted test
  evidence. Arbitrary generated code is not executed on the laptop.
- Research output failed three contract cases. The prompt now enumerates allowed
  claim kinds and requires an `unknown` claim when evidence is absent. The existing
  deterministic citation-support gate remains authoritative.
- Secret-bearing text now uses local-only routing. Typed admin cannot reveal memory;
  plaintext credential-ledger requests and cross-person conversation requests are
  denied deterministically.
- Groq repeatedly ignored planning constraints. The two stable LYA-specific plans
  now use bounded deterministic responses; other plans receive stricter missing-fact,
  rollback and no-invented-metric instructions.
- The frozen `coding-01` expectation incorrectly said case-sensitive `Swiss` returns
  `w`. It returns uppercase `S`. The fixture was corrected to version 2 before the
  final case was selected; thresholds were not changed.

## Run history

`raw.json` is the untouched first pass. It records invalid research output, missed
coding classification, poor planning answers and a Groq HTTP 429 after 23 cases.
`resume.json`, `final-rerun.json` and `planning-rerun.json` preserve bounded reruns.
`planning-final.json` contains the final two deterministic planning checks.
`score_review.py` merges the latest immutable result for each case and writes
`scored.json`; it also checks that scored IDs exactly match the frozen pack.

The live inputs were synthetic public fixtures. No project source, private memory,
credential, camera, microphone or biometric data was sent. Provider availability
and rate limiting remain external constraints; the first pass demonstrates that a
single uninterrupted 30-call burst is not dependable.

## Verification

- `check-t03.cmd`: 106 offline T01-T03 checks passed.
- Live final selection: all 30 case IDs present; all category thresholds met.
- Owner review remains required by the frozen evaluation policy before T03 is marked
  complete and Task 4 is started.

