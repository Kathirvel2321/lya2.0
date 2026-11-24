# Cloudflare Code Mode: isolated news MCP trial

24 November 2026. This is a standalone local proof of concept, not part of LYA's running desktop, phone, news monitor or private memory. It uses generated news only; no model, provider, live news, MCP service, account, deployment or background process is connected.

`news.mjs` creates a real MCP server exposing the fixed read-only `list_news` fixture and wraps it using Cloudflare's actual `codeMcpServer()` from `@cloudflare/codemode`. `createWorkerNewsCodeServer(loader)` constructs Cloudflare's `DynamicWorkerExecutor` with outbound network blocked and a ten-second timeout, requiring an actual Worker Loader. It does not create a loader or fall back to running code locally.

`check.mjs` connects an actual MCP client through in-memory transport to the wrapped server. A deliberately restricted fake executor accepts one exact hard-coded sample plan and calls the SDK-provided MCP methods directly. It verifies the single advertised `code` tool, generated tool description, returned fake results, duplicate filtering, refusal of a different sample and refusal when a Worker Loader is missing. **The fake executor does not evaluate the sample code.** It proves SDK/MCP wiring, not generated-code execution, Worker isolation, an actual model or efficiency gains. No remote call occurs.

Run after installing the locked dependencies:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
node check.mjs
```

Dependencies are confined to this folder and ignored; the package and lock file pin the trial. Installation scripts were disabled. Cloudflare's MCP wrapper also required `@cfworker/json-schema`, an optional MCP SDK validation dependency; it is pinned explicitly. The initial Node smoke run failed because the Worker executor requires the `cloudflare:` runtime; moving that import inside the Worker-only constructor made the fake-wrapper test runnable without inventing a sandbox. The next attempt exposed the missing validator, then passed once it was installed. No package was added to the main LYA runtime.

Cloudflare's [Dynamic Workers pricing](https://developers.cloudflare.com/dynamic-workers/pricing/) says Dynamic Workers require the paid Workers plan. Local Workers development can run without deploying, but Cloudflare cautions its local `workerd` is not a hardened sandbox; see [local development security](https://developers.cloudflare.com/dynamic-workers/examples/dynamic-workers-starter/). Consequently this demo does not execute arbitrary/model-generated code on the user's host and does not deploy a Worker. The existing no-paid-resource instruction remains in force. Cloudflare marks Code Mode experimental; see its [MCP guide](https://developers.cloudflare.com/agents/model-context-protocol/guides/build-codemode-mcp-server/). The wrapper does not itself grant per-call approval: any future real write handler must enforce its existing authorization.

Next: choose and qualify an isolated no-paid-code-execution environment compatible with the owner's free-only constraints, then run the actual Worker Loader with the sample plan and explicit resource/egress controls. Only after that, connect a strictly public read-only LYA news adapter and compare results, latency and token usage with the existing monitor. Do not expose private memory, credentials, account tools, arbitrary network or write operations to this trial. No claim of live integration or production readiness is made.
