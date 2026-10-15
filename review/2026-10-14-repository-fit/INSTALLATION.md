# Skill installation — 2026-10-14

Owner clarified that the requested action was to download and use the skill, not only assess it.

## Completed

- Installed the official `reverse-engineer-anything` skill using Codex's skill-installer helper.
- Destination: `C:/Users/kathirvel/.codex/skills/reverse-engineer-anything/`.
- Source: [morluto/rea skill at the reviewed commit](https://github.com/morluto/rea/tree/b8510ee00b7c4dc0624bed0e728649cf0606060f/.agents/skills/reverse-engineer-anything).
- All seven installed files match the pinned upstream Git blob hashes. The skill's local reference links resolve. Read its instructions and connection/recovery workflow.
- Downloaded Awesome-Hacking's pinned [README](upstream/awesome-hacking/README.md) and [CC0 license](upstream/awesome-hacking/LICENSE) as reference material. Both match upstream blob hashes. The repository has no installable skill; no custom skill was invented. The optional banner image was not downloaded.
- Validation: [install-validation.json](install-validation.json). No LYA runtime or dependency files changed.

The installed skill will be available for discovery on the next turn. Its instructions are already readable now. Instructions alone do not provide REA's executable tools or register an MCP server.

## REA command and Codex connection

Owner approved acquiring and running the pinned `rea-agents@6.5.0` package with dependency install scripts disabled and optional dependencies omitted. Its `doctor --client codex --json` command ran with the existing Node 22.23.2/npm runtime. Before configuration, the scoped registration check correctly reported Codex was missing the REA server.

A Codex-only dry-run proposed one configuration update at the user's `.codex/config.toml`, with backup `.codex/config.toml.rea.backup`; it adds the command `cmd.exe /d /c npx -y rea-agents@6.5.0 mcp`. It preserves unrelated configuration and requires no provider environment variables. With owner instruction to implement, the official setup command applied this one action and created the backup. Post-setup doctor returned exit code 0, overall `healthy: true`, and `registration:codex` healthy/aligned. The TOML and backup both parse; a structural comparison confirms the only change from the saved backup is adding the `rea` server, while preserving `node_repl`.

REA tools appeared in this current chat after setup: 207 `mcp__rea__*` tools are available, so this connection does not need an app restart. The installed REA skill also appears in the active skill catalog. The package's optional health check reports its bundled skill copy `missing` because setup used `--skill=false`; the separate Codex skill installation remains active. The doctor reports `environment_healthy: false` only because optional Ghidra, IDA and JADX integrations are not configured; those engines are not needed for static JavaScript inspection.

No target app/binary was analyzed because no target was provided. No private input was sent to a model. No WSL, credentials, native engines, LYA voice/UI/defaults or live deployment changed. [Sanitized setup and connection validation](rea-connection-validation.json) records the results.

