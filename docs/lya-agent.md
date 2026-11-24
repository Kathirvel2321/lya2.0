# lya_agent — LYA's desktop task agent (Phase 1)

`python -m lya_agent --task "..."` fills the `agent_command` placeholder in
`runner/config.local.json`:

```json
"agent_command": ["python", "-m", "lya_agent"]
```

The runner (runner/jobs.py) launches it with `shell=False`, passing the task
as one argv element, and kills the whole tree on timeout — unchanged.

## Safety model (read this first)

| Layer                | Mechanism                                                                                                 |
| -------------------- | --------------------------------------------------------------------------------------------------------- |
| Tool allowlist       | Only 7 in-process MCP tools exist; no Bash/file-write/web tool is registered                              |
| SDK deny-list        | ALL built-in Claude tools are in `disallowed_tools`                                                       |
| Hook deny-by-default | A `PreToolUse` hook denies anything not from `mcp__lya_desktop__`                                         |
| Gate                 | Every call routes through `security/gate.py`; NEVER tier always refuses                                   |
| Path guard           | Aliases → roots; traversal, UNC, ADS, reserved names, symlink escapes refused                             |
| Kill switch          | `data/LYA_KILL` file OR Ctrl+Alt+Shift+K global hotkey, checked before every step                         |
| Limits               | `--max-steps 15`, `--timeout-sec 120` hard wall-clock cap                                                 |
| Audit                | Every call and denial → `data/lya_agent_audit.jsonl` via `ChainedAudit`; `uia_type` logs only text length |
| Injection defence    | All tool output wrapped `<untrusted_data>`, truncated to 4000 chars                                       |
| Danger tier          | Plumbing exists; when no owner-confirm flow is wired, danger tools DENY                                   |

## Setup

```powershell
# from lya-main
pip install claude-agent-sdk pywinauto pytest
copy lya_agent\lya_agent.local.example.json lya_agent\lya_agent.local.json
# edit lya_agent.local.json: real apps + folders you allow
# ensure Claude Code CLI is installed and authenticated: claude --version
pytest tests/test_lya_agent.py -v
```

`lya_agent.local.json` is gitignored — never commit real paths of private
folders.

## Run one task manually

```powershell
cd lya-main
python -m lya_agent --task "Open Notepad and type hello" --max-steps 15 --timeout-sec 120
```

Or through the runner (Telegram): `/run <project> Open Notepad and type hello`.

## Stop it

- Create `data\LYA_KILL` (any content), or
- press **Ctrl+Alt+Shift+K** anywhere.
  The current step finishes; no new step starts; exit status is non-zero.

## Phase 2 (NOT built)

- Local/free brain (Ollama) behind the same Brain protocol
- Real owner-confirmation wiring for danger-tier tools
- More tools (move-file inside allowlisted roots, clipboard read)
