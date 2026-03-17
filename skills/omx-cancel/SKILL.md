---
name: omx-cancel
description: "Cancel active OMX workflows and running claude_code jobs. Use for /cancel, stop workflow, abort ultrawork/autopilot/ralplan sessions."
---

# Cancel Mode

Safely stop active workflows and clean stale local state.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Workflow

1. If omx runtime is live, inspect active modes and running jobs, then cancel precisely.
2. If omx runtime is unavailable, treat `/cancel` as local cleanup only.
3. Clear only the named mode when the user specifies one.
4. Never wipe unrelated notes or memory unless the user asks.
5. Return a compact summary of what was cancelled, cleared, or left untouched.
