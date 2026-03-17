---
name: omx-swarm
description: "N-worker coordinated execution for Codex using async claude_code jobs, task claiming, and ownership-safe parallelism."
---

# Swarm Mode

Swarm mode is the explicit multi-worker mode. It is optional, not the default.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Hard Preconditions

Use swarm only when:

1. delegation is available
2. the task splits into 2 or more non-overlapping packets
3. each packet has its own verify command
4. a global verification step exists

If any precondition fails, downgrade to `omx-serial` or `omx-autopilot`.

## Workflow

1. Decompose work into small ownership-safe packets.
2. Clamp worker count to the safe job cap and packet count.
3. Launch one packet per worker and monitor for failures or stalls.
4. Reclaim failed packets once; persistent failures collapse to serial.
5. Merge deterministically and run global verification.

## Rules

- Never allow overlapping ownership.
- Stop scheduling new write packets after repeated tool or permission failures.
- Keep state compact and clear it when the run ends.
