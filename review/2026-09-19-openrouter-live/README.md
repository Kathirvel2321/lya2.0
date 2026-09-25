# OpenRouter pinned-free live evaluation

Date: 2026-09-19

Only frozen synthetic public prompts were sent. Credentials and private LYA data are
absent from every report. The tested API key was read from ignored local `.env` and
never printed or written into an artifact.

## Routing verification fix

OpenRouter's current chat response exposes provider identity only when the
`X-OpenRouter-Metadata: enabled` header is requested. LYA now requires that metadata,
pins `provider.order`, disables gateway fallback and verifies the selected upstream.
Provider display names are compared to their configured slug after punctuation-only
normalization; the configured slug is still sent unchanged to OpenRouter.

## Nemotron 3 Ultra 550B

Exact free model: `nvidia/nemotron-3-ultra-550b-a55b:free`; pinned upstream: `nvidia`.
The corrected run verified NVIDIA and returned the first three answers. Latencies
were 5.6 s, 3.6 s and 31.4 s. The planning case then ended with
`provider_output_length` after 37.1 s. It fails the fixed eight-second latency and
complete-output gates and remains disabled.

## DeepSeek V4 Flash 0731

Exact free model: `deepseek/deepseek-v4-flash-0731:free`; pinned upstream:
`open-inference`. A metadata-only synthetic diagnostic returned HTTP 200, identified
OpenInference as the only selected provider and returned in 2.8 s. Repeated frozen
evaluation attempts were not reliable: after correcting the response-name/slug
comparison, two attempts failed the first case as `provider_unavailable` at 10.5 s
and 10.7 s. It remains disabled.

The laptop evaluator passes an eight-second socket timeout, but Windows urllib does
not guarantee a whole-request wall-clock deadline; one successful Nemotron request
took 31.4 s. The Oracle production entry point additionally uses a POSIX wall-clock
alarm. Any laptop request exceeding eight seconds is a failure regardless of why the
socket returned later.

## Decision

T02 is still incomplete. OpenRouter's adapter and provider-pinning checks work, but
no tested free route has passed the full eight-case suite and repeated latency gate.
Do not activate or deploy either route. Groq remains the sole active public provider;
private prompts remain local-only and fail closed.

Raw sanitized reports in this directory preserve every attempt. Official references:
[provider routing](https://openrouter.ai/docs/guides/routing/provider-selection),
[chat metadata](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request),
and [DeepSeek V4 Flash free model](https://openrouter.ai/deepseek/deepseek-v4-flash-0731:free).

