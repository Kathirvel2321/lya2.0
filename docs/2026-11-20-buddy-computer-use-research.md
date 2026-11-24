# LYA Buddy — Computer Use Research (2026-11-20)

Goal: let LYA act like a person at the laptop — open folders, files, apps,
and complete spoken/Telegram tasks autonomously.

## The three-layer modern stack

### 1. Agent brain (the loop)

- **Claude Agent SDK (Python)** — RECOMMENDED. Same agent loop, tools,
  sessions, permissions and hooks as Claude Code; programmable in Python;
  runs locally as a subprocess. Fits `runner/config.py agent_command`
  placeholder directly.
  - https://code.claude.com/docs/en/agent-sdk/overview
  - https://code.claude.com/docs/en/agent-sdk/python
- **Anthropic Computer Use toolset** (`computer_toolset_20260801`) —
  screenshot + mouse + keyboard tools; LYA executes every call itself, so
  the security gate stays in control.
  - https://docs.anthropic.com/en/docs/agents-and-tools/computer-use
- **OpenClaw** — open-source personal-AI runtime (gateway + Telegram +
  browser CDP + skills). Best reference architecture; LYA's runner is a
  hand-rolled mini-OpenClaw.
  - https://github.com/openclaw/openclaw

### 2. Hands — MCP (Model Context Protocol)

MCP is the standard tool protocol; Windows now ships the On-device Agent
Registry (ODR) for MCP connectors.

- https://learn.microsoft.com/en-us/windows/ai/mcp/overview
- Servers: `@modelcontextprotocol/server-filesystem` (scoped folders),
  `server-memory`, git, browser.
- Registry: https://github.com/modelcontextprotocol/servers
- On Windows wrap npx: `cmd /c npx -y @modelcontextprotocol/server-filesystem C:\allowed\path`

### 3. Windows execution

- `pywinauto` / `uiautomation` — drive real apps by control name (reliable)
- `pyautogui` — raw screenshot+click fallback
- Playwright / CDP Chrome — browser control (OpenClaw's approach)
- Existing `security/executors.py` + gate for shell actions

## Proposed LYA architecture

    voice/Telegram -> brain/capabilities -> runner (existing)
          |
          v
    agent_command = ["python", "-m", "lya_agent"]   (fills placeholder)
          |
          +-- Claude Agent SDK loop (plan -> act -> verify)
          +-- MCP: filesystem (allowlisted), windows-app (pywinauto), browser
          +-- Computer-use toolset only as last-resort fallback
          +-- every action through security/gate.py + chained_audit

## Implementation steps

1. `pip install claude-agent-sdk`; write `lya_agent` module reading
   `--task` from argv (matches runner/jobs.py contract).
2. Point `agent_command` in runner local config at it.
3. Add MCP filesystem server scoped to allowlisted paths; mirror
   runner/security.py allowlist rules.
4. New `skills/desktop.py` (pywinauto): open_app, focus_window,
   open_folder; register guarded capabilities in brain/capabilities.py
   so gate + audit cover them.
5. Wire computer-use toolset only for apps without UI Automation support;
   log every action (Anthropic best practice).
6. Keep owner-only runner, DANGEROUS-verb confirmations, audit chain —
   matches Microsoft's Windows agent guidance (containment, attribution,
   human confirmation):
   https://developer.microsoft.com/en-us/windows/agentic
