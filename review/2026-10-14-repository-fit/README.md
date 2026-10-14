# REA and Awesome-Hacking: fit for LYA

Assessment date: 2026-10-14. Owner asked whether these repositories could help build LYA before the next implementation. This is a read-only upstream review and recommendation, not an integration or security certification.

Follow-up: owner then explicitly requested skill installation. The [installation record](INSTALLATION.md) supersedes the earlier no-installation status for the skill only; executable package acquisition was blocked by automatic approval review and remains pending approval.

## Recommendation

Use both selectively. Keep REA as an optional development investigation tool; use Awesome-Hacking as a reference index for choosing defensive checks. Neither establishes LYA's memory, authentication, recovery or deployment correctness.

| Repository | Verified purpose and terms | Recommended LYA use |
| --- | --- | --- |
| [morluto/rea](https://github.com/morluto/rea/tree/b8510ee00b7c4dc0624bed0e728649cf0606060f) | TypeScript/Node CLI and MCP analysis server. Upstream-authored code declares MIT; dependencies and external engines retain separate terms. | Later, investigate a specific authorized application or binary when its source is unavailable. Evaluate one static, synthetic JavaScript target first if that need arises. |
| [Hack-with-Github/Awesome-Hacking](https://github.com/Hack-with-Github/Awesome-Hacking/tree/b2bb13aa69b4f568a1bab0cbb17b7a00a350dc36) | Curated links to other security resource lists; root contains documentation, an image and repository metadata, rather than an executable assistant framework. Repository declares CC0-1.0. | Select references for API access control, application security, prompt injection and static analysis. Each linked project needs its own review before use. |

These are recommendations based on inspected source/documents, not measured results on LYA's hardware.

## Practical boundaries

- Current Python memory work already has readable source and focused tests. Direct inspection is the smaller solution; no REA dependency is needed for that work.
- REA's manifest declares Node `^22.19.0 || ^24.11.0 || >=26.0.0`, 39 direct runtime dependencies and optional Frida. Native analysis adds a selected engine such as Ghidra, Hopper or IDA. Commercial engines have separate licensing/cost requirements; do not install them under LYA's free-only rule without checking the actual option.
- REA's setup can change agent configuration and install workflow instructions. A future evaluation should use a disposable development environment, a pinned version and synthetic inputs, with no production credentials or private stores.
- REA's security policy explicitly says its bridges and temporary projects are not a sandbox. Runtime operations may launch/interact with targets using the user's privileges. A Python virtual environment does not restrict filesystem/process access. Do not treat the existing WSL lab as safe for arbitrary unknown executables.
- Upstream says analysis is local, but tool results reach the calling agent and its model provider. Keep private binaries, memory databases, credentials and personal captures out of any trial.
- Awesome-Hacking is discovery material, not a vetted bundle or permission to run every listed tool. Do not automatically download, execute or ingest its linked projects as trusted agent instructions. Use security exercises on owned or explicitly authorized lab targets.
- Preserve upstream notices if reusing code. Neither repository's license applies automatically to linked tools, dependencies or software being analyzed.

## Evidence and limits

Inspected upstream heads: REA `b8510ee00b7c4dc0624bed0e728649cf0606060f`; Awesome-Hacking `b2bb13aa69b4f568a1bab0cbb17b7a00a350dc36`. REA head metadata reports 2026-10-14; Awesome-Hacking head reports 2026-07-26. These observations do not predict future maintenance or prove the npm release matches source.

Read repository metadata/root listings; REA README, package manifest, LICENSE, SECURITY, installation and third-party-notice excerpts, JavaScript graph documentation, static-analysis worker and prepare hook; Awesome-Hacking README and license header. REA manifest reported version 6.5.0. Sampled worker parses supplied source and applies analysis budgets; this limited inspection does not audit all providers or dependencies.

Primary references: [REA manifest](https://github.com/morluto/rea/blob/b8510ee00b7c4dc0624bed0e728649cf0606060f/package.json), [security boundary](https://github.com/morluto/rea/blob/b8510ee00b7c4dc0624bed0e728649cf0606060f/SECURITY.md), [setup scope](https://github.com/morluto/rea/blob/b8510ee00b7c4dc0624bed0e728649cf0606060f/docs/installation.md), [MIT license](https://github.com/morluto/rea/blob/b8510ee00b7c4dc0624bed0e728649cf0606060f/LICENSE), [third-party notices](https://github.com/morluto/rea/blob/b8510ee00b7c4dc0624bed0e728649cf0606060f/THIRD_PARTY_NOTICES.md), [resource index](https://github.com/Hack-with-Github/Awesome-Hacking/blob/b2bb13aa69b4f568a1bab0cbb17b7a00a350dc36/README.md), [CC0 license](https://github.com/Hack-with-Github/Awesome-Hacking/blob/b2bb13aa69b4f568a1bab0cbb17b7a00a350dc36/LICENSE).

GitHub CLI was unavailable; public reads used the GitHub connector and browser fetch after consulting the Agent Reach GitHub workflow. No clone, installation, upstream script/test execution, MCP registration, WSL operation, scan, account/key setup, private transfer or deployment occurred. Only this report and documentation continuity/index entries were added. Existing unrelated edits remain outside this assessment.

Next implementation remains current-revision owner-operated Ubuntu memory qualification, then synthetic TLS/lifecycle work and independent free recovery placement. Optional REA integration should wait for a concrete investigation task; selected security references can inform later scoped tests.

