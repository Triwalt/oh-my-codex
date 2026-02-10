---
name: omx-help
description: "Guide on using oh-my-codex (omx). Use when the user asks 'help', 'what can you do', 'how do I use omx', 'what skills', or wants to understand workflows and command-style entry points."
---

# oh-my-codex (omx) Help

## What is omx?

omx is an orchestration layer for Codex CLI that gives you:
- Async Claude Code delegation for long-running coding tasks.
- Structured workflows for planning, autonomous build, review, analysis, TDD, and serial execution.
- Persistent workflow state across turns.
- Session notepad and project memory.

## OMC Compatibility (Command-Style Entry)

Treat these command-style prompts as skill triggers in Codex:

| Command-style prompt | Recommended skill |
|---|---|
| `/plan <task>` | `omx-plan` |
| `/serial <task>` | `omx-serial` |
| `/ralplan <task>` | `omx-ralplan` |
| `/ultrawork <task>` | `omx-ultrawork` |
| `/swarm <task>` | `omx-swarm` |
| `/pipeline <task>` | `omx-pipeline` |
| `/autopilot <task>` | `omx-autopilot` |
| `/cancel [mode]` | `omx-cancel` |

You can always call them explicitly with skill syntax too:
- `$omx-plan ...`
- `$omx-serial ...`
- `$omx-ralplan ...`
- `$omx-ultrawork ...`
- `$omx-swarm ...`
- `$omx-pipeline ...`
- `$omx-autopilot ...`
- `$omx-cancel ...`

## Available Skills

| Skill | Trigger Phrases | What It Does |
|---|---|---|
| `omx-autopilot` | "build me", "create", "autopilot" | Full autonomous execution: analyze -> plan -> implement -> verify |
| `omx-serial` | "serial", "single-agent", "/serial" | Deterministic linear workflow with anti-drift controls |
| `omx-plan` | "plan this", "how should we", "/plan" | Versioned planning with iteration support |
| `omx-ralplan` | "ralplan", "consensus plan", "/ralplan" | Iterative planner + architect + critic consensus loop |
| `omx-ultrawork` | "ultrawork", "parallel", "high throughput", "/ultrawork" | Parallel multi-agent orchestration optimized for Codex |
| `omx-swarm` | "swarm", "multi-worker", "/swarm" | Coordinated N-worker packet execution |
| `omx-pipeline` | "pipeline", "stages", "/pipeline" | Stage-based sequential/hybrid orchestration |
| `omx-cancel` | "cancel mode", "stop workflow", "/cancel" | Cancel running jobs and clear workflow state |
| `omx-research` | "research", "compare", "analyze options" | Multi-source research with citations |
| `omx-code-review` | "review code", "check my code" | Comprehensive code review via Claude Code |
| `omx-tdd` | "tdd", "test first", "red green" | Test-driven workflow |
| `omx-analyze` | "analyze", "debug", "investigate" | Deep debugging and architecture analysis |
| `omx-help` | "help", "what can you do" | This guide |

## MCP Tools (omx server)

### Claude Code Delegation
| Tool | Purpose |
|---|---|
| `claude_code` | Start an async Claude Code job (returns `jobId`) |
| `claude_code_status` | Wait/poll for job output |
| `claude_code_cancel` | Cancel a running job |
| `claude_code_list` | List jobs and statuses |

### State Management
| Tool | Purpose |
|---|---|
| `omx_state_read` | Read workflow state |
| `omx_state_write` | Save or merge state |
| `omx_state_clear` | Clear one workflow mode |
| `omx_state_list` | List active modes |

### Notes and Memory
| Tool | Purpose |
|---|---|
| `omx_note_read` / `omx_note_write` | Session notepad |
| `omx_memory_read` / `omx_memory_write` | Project memory |

## Codex-Specific Notes

- Prefer `omx-serial` for constrained linear tasks where predictability matters more than throughput.
- Prefer `omx-ultrawork` for fast parallel execution with ownership partitioning.
- Prefer `omx-swarm` for explicit worker count + packet queue control.
- Prefer `omx-pipeline` for traceable stage handoffs and auditability.
- Prefer `omx-ralplan` when requirements are high-risk and need consensus planning.
- If Claude Code is running with permission mode `respect`, write operations may pause for confirmation. For unattended workflows, configure `OMX_CLAUDE_PERMISSION_MODE=skip` in Codex MCP settings.

## References

- OMC feature inventory and port map: `C:/Users/19667/.codex/skills/omx-help/references/omc-feature-inventory.md`
