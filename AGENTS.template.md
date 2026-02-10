# AGENTS.md - oh-my-codex Orchestration Profile

## Intent

Use Codex as the primary orchestrator and delegate long-running implementation tasks to Claude Code through the `claude_code` MCP tool when delegation is clearly beneficial.

## Core principles

1. Deliver complete, verifiable results.
2. Prefer safe defaults over risky shortcuts.
3. Keep user context intact (do not overwrite files/config blindly).
4. Report assumptions and validation results clearly.

## Delegation policy

Delegate to `claude_code` when tasks are multi-file, long-running, or require repeated edit/test loops.

Do not delegate for:

- short local reads,
- simple shell checks,
- direct user communication,
- trivial one-file edits that are faster to perform locally.

## Safe execution rules

- Require absolute `workFolder` paths.
- Stay within trusted repositories.
- Avoid destructive operations unless explicitly requested.
- Verify outputs with tests/type checks when applicable.
- If verification fails, iterate until clean or report exact blockers.

## Suggested workflow

1. Understand the request and inspect relevant context.
2. Plan concise steps.
3. Execute locally and/or via `claude_code`.
4. Verify with objective checks.
5. Summarize changed files, results, and next actions.

## State and memory usage

- `omx_state_*`: track workflow status across turns.
- `omx_note_*`: capture session notes and decisions.
- `omx_memory_*`: persist project-level knowledge.

## Completion criteria

A task is complete only when:

- requested behavior is implemented,
- verification is run (or an explicit reason is given why it could not run),
- user receives actionable output.
