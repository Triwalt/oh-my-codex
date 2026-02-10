# oh-my-codex (omx)

Orchestration layer for [OpenAI Codex CLI](https://github.com/openai/codex) that adds:

- async Claude Code delegation (`claude_code` + `claude_code_status`)
- workflow state and session notes (`omx_state_*`, `omx_note_*`)
- per-project memory (`omx_memory_*`)

## Why this exists

MCP tool calls can time out on long running coding tasks. `omx` uses a job model:

1. `claude_code(...)` starts work and returns a job ID quickly.
2. `claude_code_status(jobId)` long-polls for progress.
3. Repeat status calls until done.

This keeps MCP calls short while the delegated task continues in the background.

## Production hardening in this fork

This version adds practical safety and reliability controls:

- configurable permission mode (`OMX_CLAUDE_PERMISSION_MODE=skip|respect`)
- strict `workFolder` validation (must be absolute existing directory)
- optional path allow-list (`OMX_ALLOWED_WORKFOLDER_ROOTS`)
- mode-name validation for state files (prevents path traversal)
- capped running jobs and bounded output buffers
- optional max runtime per job
- smoke test script (`npm run smoke`)
- safer installer defaults (does not overwrite AGENTS.md unless requested)
- Windows installer (`install.ps1`)

## Included workflows

This repository ships the following workflow skills:

- `omx-serial` (deterministic single-agent mode, serial-first reliability)
- `omx-plan` / `omx-ralplan`
- `omx-autopilot`
- `omx-pipeline`
- `omx-ultrawork` / `omx-swarm`
- `omx-cancel`
- `omx-research` / `omx-analyze` / `omx-code-review` / `omx-tdd`


## Requirements

- Node.js 20+
- Codex CLI (`npm install -g @openai/codex`)
- Claude Code (`npm install -g @anthropic-ai/claude-code`)

## Install

### Windows (recommended on Windows hosts)

```powershell
cd oh-my-codex
./install.ps1
```

Optional flags:

```powershell
./install.ps1 -InstallAgents -OverwriteSkills -PermissionMode skip
```

### macOS / Linux

```bash
cd oh-my-codex
bash install.sh
```

Optional env vars:

```bash
INSTALL_AGENTS=true OVERWRITE_SKILLS=true OMX_PERMISSION_MODE=skip bash install.sh
```

## Verify

```bash
cd mcp-server
npm install
npm run lint
npm run smoke
```

Optional (validate skills presence):

```bash
ls ../skills
```

## MCP tools (12)

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

## Config reference

The installer adds an `mcp_servers.omx` block to `~/.codex/config.toml`.

Useful env vars (inside `mcp_servers.omx.env`):

| Variable | Default | Purpose |
|---|---|---|
| `OMX_CLAUDE_PERMISSION_MODE` | `skip` | `skip` uses Claude's non-interactive dangerous mode; `respect` keeps permission flow. |
| `OMX_MAX_RUNNING_JOBS` | `3` | Concurrent `claude_code` jobs limit. |
| `OMX_MAX_COMPLETED_JOBS` | `100` | In-memory history size for completed jobs. |
| `OMX_MAX_OUTPUT_CHARS` | `200000` | Output cap per stream (`stdout`/`stderr`) per job. |
| `OMX_MAX_PROMPT_CHARS` | `120000` | Prompt length cap. |
| `OMX_MAX_WAIT_SECONDS` | `25` | Max long-poll wait for `claude_code_status`. |
| `OMX_MAX_JOB_RUNTIME_SECONDS` | `0` | Hard timeout for a job (`0` disables). |
| `OMX_ALLOWED_WORKFOLDER_ROOTS` | _(unset)_ | Optional path allow-list for `workFolder` (use OS path delimiter). |
| `MCP_OMX_DEBUG` | `false` | Verbose server logs to stderr. |
| `CLAUDE_CLI_NAME` | _(auto)_ | Override Claude CLI binary path. |

## Codex and oh-my-claudecode

`oh-my-claudecode` is built for Claude Code's workflow model, not Codex's native skill format.

You can still reuse ideas and prompts, but direct drop-in compatibility is limited. `omx` is the bridge approach: Codex orchestrates, Claude Code executes via MCP.

## License

MIT
