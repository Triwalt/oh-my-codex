---
name: omx-help
description: "Guide on using oh-my-codex (omx). Use when the user asks 'help', 'what can you do', 'how do I use omx', 'what skills', or wants to understand workflows and command-style entry points."
---

# oh-my-codex (omx) Help

omx is a workflow layer for Codex. It can run in 2 ways:

- full runtime mode: `omx` MCP plus delegation/state tools are available
- fallback mode: `omx-*` names act as shorthand for native Codex workflows

Before using any `omx-*` skill, apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md`.

## Command Map

| Prompt | Skill | Default fallback |
|---|---|---|
| `/serial <task>` | `omx-serial` | native serial execution |
| `/autopilot <task>` | `omx-autopilot` | serial-first native execution |
| `/pipeline <task>` | `omx-pipeline` | local staged prompting |
| `/swarm <task>` | `omx-swarm` | downgrade to serial if parallel gate fails |
| `/ultrawork <task>` | `omx-ultrawork` | downgrade to serial if parallel gate fails |
| `/plan <task>` | `omx-plan` | inline versioned plan |
| `/ralplan <task>` | `omx-ralplan` | inline planner/architect/critic loop |
| `/cancel [mode]` | `omx-cancel` | local cleanup only if no omx runtime |

## Mode Picks

- Prefer `omx-serial` by default.
- Use `omx-autopilot` for end-to-end execution when the task is still mostly linear.
- Use `omx-pipeline` when stage handoff matters more than speed.
- Use `omx-swarm` or `omx-ultrawork` only when the parallel gate passes.
- Use `omx-ralplan` only for high-risk planning problems.

## Operational Notes

- If active `~/.codex/config.toml` does not expose `mcp_servers.omx`, do not call nonexistent `omx_*` or `claude_code*` tools.
- If delegation errors or permission blocks repeat, stop spawning more work and collapse to serial.
- Keep notes workspace-scoped and archive stale state before reusing omx.

## References

- Runtime contract: `skills/omx-help/references/omx-runtime-contract.md`
- OMC feature inventory: `skills/omx-help/references/omc-feature-inventory.md`
