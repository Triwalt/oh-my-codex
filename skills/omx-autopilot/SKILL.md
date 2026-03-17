---
name: omx-autopilot
description: "Full autonomous execution from idea to working code. Uses serial mode for linear tasks and ultrawork-style parallel execution for independent workstreams."
---

# Autopilot Mode

Autopilot is the end-to-end executor: understand -> plan -> implement -> verify -> done.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Default Stance

- Start in `serial`.
- Move to `pipeline` only when stage handoff adds clarity.
- Move to `swarm` or `ultrawork` only when the parallel gate passes.
- If omx runtime is unavailable, continue with native Codex and skip remote state or delegation.

## Workflow

1. Read the request, locate the work folder, and inspect key files.
2. Break the work into concrete steps with a clear verification command.
3. Execute in serial first: reproduce, edit minimally, re-run verification.
4. Escalate only after 2 focused retries or when file ownership boundaries are explicit.
5. Do not finish until verification is clean or blockers are explicit.

## Rules

- Ask at most one clarification round only when ambiguity changes implementation risk.
- Keep prompts short and verify-command-centric.
- Avoid concurrent writes to overlapping file groups.
- If state tools are available, keep state compact and clear it on success.
