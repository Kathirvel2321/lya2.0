# Private local model decision — 2026-09-19

## Decision

LYA now has an explicit local-only conversation path through the existing llama.cpp
server. Use `private mode` for a session, `public mode` to leave it, or prefix one
message with `private:` or `secret:`. The private path calls only
`http://127.0.0.1:8080/v1/chat/completions`. If that endpoint is unavailable, the
request is blocked and no cloud provider is tried. The native UI marks the result
`LOCAL ONLY · CLOUD BLOCKED`.

This controls LYA's model routing. It cannot protect against malware, screen capture,
keyboard logging, an already-compromised operating system, or a user explicitly
copying the answer elsewhere. Model output is not automatically saved as memory.

## Jev

Jev was not added. TypeSafe describes Jev as a hosted early-access System One model
that accepts unstructured state and returns typed probabilistic decisions; it gives
up free-form string generation. It can later help classify or score already-public,
sanitized workflow data, but it cannot be LYA's chat brain. It also cannot receive
secret text under the local-only rule: TypeSafe's privacy policy says the service
collects prompts and other input, may use input to provide/debug/improve the service,
and may disclose it to service providers. The policy says input is not used to train
or fine-tune models, which is useful but does not mean the input stayed on this PC.

Primary sources:

- https://typesafe.ai/blog/introducing-system-one-models-and-jev
- https://typesafe.ai/legal/privacy-policy

## AirLLM

AirLLM was not installed. Its useful trick is layer-by-layer disk-to-GPU streaming,
which reduces peak VRAM; it does not reduce the model's total weight files or make
generation interactive on this laptop. The project itself says the original model
is decomposed and saved layer-wise, requires sufficient disk, and is mainly bottlenecked
by loading weights from disk. Its July 2026 Kimi K3 release reports 292 seconds per
token for a very large checkpoint. A September 2026 Windows issue reports 28.6
seconds per token for a 3B model on a much stronger NVIDIA system. Those are upstream
reports, not measurements on this laptop, but they are enough to reject AirLLM for
LYA's interactive private chat unless a future local benchmark proves otherwise.

Primary sources:

- https://github.com/lyogavin/airllm
- https://github.com/lyogavin/airllm/releases
- https://github.com/lyogavin/airllm/issues/364

## What is actually wired

- `brain/workflow.py`: local-only mode, one-shot prefixes, loopback pin, fail-closed
  behavior, and 60-second local request bound.
- `tools/run-llama-local.ps1`: stable `lya-local` model alias on loopback.
- `run-local-model.cmd`: starts the server without changing Windows execution policy.
- `.env`: only the safe local model selector was changed to `lya-local`; credential
  values were not printed or copied.
- `desktop/app.py`: visibly labels local-only replies.
- `test_brain_workflow.py`: proves the cloud fixture receives zero calls in private
  mode and still receives zero calls when local inference fails.

The other model selectors found in `.env` belong partly to the legacy `brain/mind.py`
path. They are not automatically eligible in the tested Oracle router. A key or model
name in `.env` does not activate a safe provider route; each cloud provider still
needs an adapter, privacy policy, model ID, free-tier check and evaluation.

## Checks

- 26 Brain and Oracle tests passed.
- 10 native experience tests passed.
- A live synthetic request passed through the installed llama.cpp server with route
  `private-local`, a non-empty response, and a cloud client that would fail the test
  if called. The dedicated server was stopped and temporary server logs were removed.
- `git diff --check` passed for the changed code after removing an extra final blank
  line; line-ending notices remain informational.

The installed Qwen2.5 1.5B Q4 model remains below LYA's quality gate (3 pass, 1
partial, 4 fail in the earlier eight-case evaluation). Local privacy routing is now
working, but serious security advice still needs a stronger locally tested model and
human verification. The next candidate is Qwen3 4B Q4_K_M under llama.cpp, selected
for evaluation rather than AirLLM; it is not yet downloaded or approved.

