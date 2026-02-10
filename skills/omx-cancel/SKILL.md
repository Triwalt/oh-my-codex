---
name: omx-cancel
description: "Cancel active OMX workflows and running claude_code jobs. Use for /cancel, stop workflow, abort ultrawork/autopilot/ralplan sessions."
---

# Cancel Mode

Safely stop active workflows and jobs.

## Command-Style Triggers

Treat these as cancel requests:
- `/cancel`
- `/cancel <mode>`
- `$omx-cancel`
- "cancel mode", "stop workflow", "abort ultrawork"

## Workflow

### Step 1: Inspect
1. Read active modes with `omx_state_list`.
2. Read running jobs with `claude_code_list(status: "running")`.

### Step 2: Cancel Jobs
1. Cancel each running job via `claude_code_cancel(jobId)`.
2. Record cancelled job IDs in response.

### Step 3: Clear State
- If a specific mode is provided, clear only that mode.
- If no mode is provided, clear all active modes returned by `omx_state_list`.

### Step 4: Confirm
Return a compact summary:
- jobs cancelled
- modes cleared
- leftover blockers (if any)

## Rules

- Prefer precise cancellation when user names a mode.
- Do not clear unrelated long-term notes/memory unless explicitly asked.
- Always report what remains active after cancellation.
