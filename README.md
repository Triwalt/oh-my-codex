# oh-my-codex (omx)

Orchestration layer for [OpenAI Codex CLI](https://github.com/openai/codex).

`omx` adds a practical workflow layer on top of Codex:
- async delegation to Claude Code (`claude_code` + `claude_code_status`)
- persistent workflow state (`omx_state_*`)
- session notes (`omx_note_*`)
- project memory (`omx_memory_*`)

---

## What Problem It Solves

Long coding tasks often exceed a single MCP call duration.

`omx` uses a job model:
1. `claude_code(...)` starts work and returns a `jobId` quickly.
2. `claude_code_status(jobId)` polls progress safely.
3. Repeat polling until completion.

This keeps orchestration responsive while delegated execution continues in background.

---

## Repository Layout

- `mcp-server/` - OMX MCP server implementation
- `skills/` - Codex skills (`omx-*` + `claude-code-mcp`)
- `install.sh` / `install.ps1` - installers
- `config.example.toml` - example Codex MCP config

---

## Included Workflows

- `omx-serial` - deterministic single-agent mode (serial-first reliability)
- `omx-plan` / `omx-ralplan`
- `omx-autopilot`
- `omx-pipeline`
- `omx-ultrawork` / `omx-swarm`
- `omx-cancel`
- `omx-research` / `omx-analyze` / `omx-code-review` / `omx-tdd`

Command-style triggers (examples):
- `/serial <task>`
- `/plan <task>`
- `/pipeline <task>`
- `/ultrawork <task>`
- `/cancel`

---

## Serial-First Recommendation

For Codex unattended execution, prefer:
1. **`omx-serial`** for linear tasks and small/medium scoped fixes.
2. **`omx-pipeline`** when stage traceability is required.
3. **`omx-ultrawork`** when ownership boundaries are clearly parallelizable.

Why: serial mode reduces "task clarification drift" and improves deterministic behavior.

---

## Production Hardening

This fork includes:
- `OMX_CLAUDE_PERMISSION_MODE=skip|respect`
- strict `workFolder` validation (absolute + existing dir)
- optional allow-list (`OMX_ALLOWED_WORKFOLDER_ROOTS`)
- mode-name validation for state files (path traversal protection)
- bounded running jobs / output buffers / prompt size
- optional max runtime per job
- smoke test script (`npm run smoke`)

---

## Requirements

- Node.js 20+
- Codex CLI (`npm install -g @openai/codex`)
- Claude Code (`npm install -g @anthropic-ai/claude-code`)

---

## Install

### Windows

```powershell
cd D:\MCPs\oh-my-codex
./install.ps1
```

Optional:

```powershell
./install.ps1 -InstallAgents -OverwriteSkills -PermissionMode skip
```

### macOS / Linux

```bash
cd /path/to/oh-my-codex
bash install.sh
```

Optional:

```bash
INSTALL_AGENTS=true OVERWRITE_SKILLS=true OMX_PERMISSION_MODE=skip bash install.sh
```

---

## Verify

```bash
cd mcp-server
npm install
npm run lint
npm run smoke
```

Optional quick checks:

```bash
ls ../skills
```

In Codex startup logs, you should see:
- `mcp: omx ready`

---

## MCP Tools (12)

- `claude_code`
- `claude_code_status`
- `claude_code_cancel`
- `claude_code_list`
- `omx_state_read`
- `omx_state_write`
- `omx_state_clear`
- `omx_state_list`
- `omx_note_read`
- `omx_note_write`
- `omx_memory_read`
- `omx_memory_write`

---

## Config Reference

Installer writes an `mcp_servers.omx` block into `~/.codex/config.toml`.

Key env vars in `[mcp_servers.omx.env]`:

| Variable | Default | Purpose |
|---|---|---|
| `OMX_CLAUDE_PERMISSION_MODE` | `skip` | `skip`: autonomous; `respect`: keep permission flow |
| `OMX_MAX_RUNNING_JOBS` | `3` | Max concurrent delegated jobs |
| `OMX_MAX_COMPLETED_JOBS` | `100` | Completed job history cap |
| `OMX_MAX_OUTPUT_CHARS` | `200000` | `stdout`/`stderr` cap per job |
| `OMX_MAX_PROMPT_CHARS` | `120000` | Prompt length cap |
| `OMX_MAX_WAIT_SECONDS` | `25` | Poll wait cap for status calls |
| `OMX_MAX_JOB_RUNTIME_SECONDS` | `0` | Job hard timeout (`0` disables) |
| `OMX_ALLOWED_WORKFOLDER_ROOTS` | _(unset)_ | Optional trusted roots allow-list |
| `MCP_OMX_DEBUG` | `false` | Verbose server logs |
| `CLAUDE_CLI_NAME` | _(auto)_ | Override Claude CLI executable |

---

## Compatibility Note

`oh-my-claudecode` is designed for Claude Code-native workflows.

`omx` is a bridge approach for Codex:
- Codex handles orchestration and workflow state
- Claude Code executes delegated coding tasks

---

## License

MIT
