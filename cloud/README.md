# Oracle inference bridge

Updated 2026-09-14: public-text Groq is active through the desktop/Oracle bridge.
NVIDIA routes remain disabled after failed live reliability checks; there is one
active provider. Private context is denied. See
[LYA_MODEL_STRATEGY.md](../LYA_MODEL_STRATEGY.md) for the current policy, shortlist
and verification limits. The version-2 `provider.example.json` is disabled by
default and differs intentionally from protected active configuration. See
`review/2026-09-14-live-models/README.md` for live evidence and accuracy failures.

Prepared 2026-09-14. Uses one standard-library Python process per SSH request;
no HTTP listener, daemon, container, extra package or private-memory database.
The desktop remains responsible for identity, permissions and memory retrieval.

`inference.py` accepts one JSON object on stdin and returns one JSON response.
Only validated text messages are forwarded; no tools are enabled. Limits: 64 KiB
input, 12 messages, up to 2,048 completion tokens per route. Version 2 allows at
most two independent eligible attempts within its routing window and maintains a
daily attempt cap/cooldowns in private SQLite state. The desktop SSH timeout is
30 seconds. The attempt cap is not a dollar spending cap. Legacy single-provider
configuration still uses a 400-token default; it is not activated on this server.

`brain/oracle.py` is opt-in via ignored `desktop/oracle.local.json` containing
`host` and `key_file` (path within the project). Do not create that configuration
until the chosen provider has been configured and tested. Without it, the existing
local model selection remains unchanged. SSH uses the pinned local known-hosts
file and runs without a visible console window. The login key currently has full
Ubuntu account access; restricted deployment credentials are a later hardening
gate before wider distribution or mobile access.

Remote layout: `/home/ubuntu/lya/inference.py`; a later `provider.json` beside it
must be mode 600 and follow the version-2 template. Never commit or log that file.
The backend returns a configuration error until it exists. It supports fixed
Groq/NVIDIA/HF endpoints plus an operator-configured OmniRoute endpoint. No endpoint
is chosen by a model. Keep each gateway's upstream pinned and correctly declare
shared failure domains. Router state has counters/cooldowns, no prompt content.
Only the selected Groq credential was later transferred via encrypted SSH for
activation. NVIDIA and unrelated .env credentials were not persisted remotely.

`cloud/evaluate_models.py` is an explicit LIVE command, not an offline test. It
uses only the fixed synthetic rubric, stops on a failed request, and writes its
results to a new path under `review/`. It never executes generated code. Example:
`python -B -m cloud.evaluate_models --provider groq --output review/new-run/groq.json`.
Successful HTTP completion still requires answer review; it is not a pass score.

Provisional model recommendation: GPT-OSS 120B through Groq for text reasoning.
Reasoning, structured outputs and tool-use capabilities are documented, but LYA
has not benchmarked this model or enabled those tools. Compare it on an explicit
synthetic task set (planning, corrected facts, abstention, Tamil/English and quota
failures) before calling it the best fit. Keep the current single-client council
labelled as multiple perspectives, not independent confirmation.

- [Groq model capabilities](https://console.groq.com/docs/model/openai/gpt-oss-120b)
- [Groq account rate limits](https://console.groq.com/docs/rate-limits)
- [Groq data handling](https://console.groq.com/docs/your-data)
- [Gemini pricing and free-tier data use](https://ai.google.dev/gemini-api/docs/pricing)

Gemini is a candidate for a later multimodal comparison. Free API availability,
account limits, privacy terms and benchmark quality must be verified for the
specific model before activation. No provider is guaranteed perfect or unlimited.

Offline checks: `.venv-ui/Scripts/python.exe -B test_oracle.py` uses mocked network
and SSH, fake credentials and no real key reads. Real SSH smoke testing must be
reported separately from these component checks.
