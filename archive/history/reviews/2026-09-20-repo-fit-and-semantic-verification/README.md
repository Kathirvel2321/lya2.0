# Repository fit and citation-support gate

Date: 2026-09-20

## Dependency decisions

The five suggested repositories were reviewed from their official GitHub pages and
GitHub repository metadata. They are not all core dependencies.

| Repository | Decision | LYA use | Reason |
|---|---|---|---|
| `ggml-org/whisper.cpp` | selected for T08 evaluation | offline speech-to-text and VAD | MIT, CPU-only Windows support, quantized models, lower runtime weight than the Python/PyTorch implementation |
| `openai/whisper` | do not install beside whisper.cpp | reference model and accuracy baseline only | MIT, but its Python/PyTorch and FFmpeg stack duplicates the selected speech engine and is heavier for this 8 GB laptop |
| `yt-dlp/yt-dlp` | defer to an authorized media-ingestion task | obtain metadata/subtitles or audio from a user-supplied URL | useful but unrelated to the brain; site terms, content rights, bounded downloads and unsafe execution options need a separate boundary |
| `gitroomhq/postiz-app` | optional separate service | social-post scheduling if explicitly requested later | AGPL-3.0, large TypeScript service with databases/integrations; it should not be embedded in LYA's brain |
| `remotion-dev/remotion` | optional separate renderer after license review | programmatic React video rendering | large Node/Chromium toolchain and GitHub reports no standard SPDX license; unnecessary for current tasks |

No repository was cloned or installed in this task. Local inspection found Node and
npm, but no `whisper-cli`, `yt-dlp`, FFmpeg or CMake command on the project shell's
PATH. The existing Agent Reach environment may have a private yt-dlp dependency;
that does not make it a project runtime dependency.

Safe configuration inspection detected non-empty `JINA_API_KEY` and `YOU_API_KEY`
entries without reading or recording their values. Routine LYA research deliberately
continues to use You.com's keyless MCP profile. Neither credential was transmitted.

## T03 implementation

`brain/verification.py` now applies a conservative local support gate to each factual
claim. Every number in the claim must occur in at least one cited source, and the
claim's content words must substantially overlap that source's declared claim and
excerpt. Unsupported paraphrases fail closed; the model must label conclusions as
`inference` or missing evidence as `unknown`. Visible output prefixes those kinds as
`Inference:` and `Uncertain:`.

This is a deterministic screening gate, not a general proof of textual entailment.
Human review remains required for the frozen quality evaluation and difficult
paraphrases.

## Checks

- `test_answer_verification.py`: 7 tests passed, including a weight claim incorrectly
  cited to a battery-only source.
- `check-t03.cmd`: all 100 offline T01-T03 checks passed.
- No provider, microphone, camera, biometric, private memory or real media was used.

## Remaining T03 gates

- Test proposed code in disposable storage before reporting it as working.
- Run and human-score all 30 frozen cases, recording quality and latency by category.
- Keep full-page retrieval and stronger entailment review as a measured follow-up;
  do not weaken the deterministic fail-closed gate.

## Primary sources

- https://github.com/ggml-org/whisper.cpp
- https://github.com/openai/whisper
- https://github.com/yt-dlp/yt-dlp
- https://github.com/gitroomhq/postiz-app
- https://github.com/remotion-dev/remotion

