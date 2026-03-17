---
name: omx-ultrawork
description: "Maximum-throughput parallel workflow for Codex. Recreates OMC ultrawork behavior with async claude_code jobs, file ownership partitioning, and strict verification."
---

# Ultrawork Mode

Ultrawork is the highest-throughput mode. It should be rare.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Hard Preconditions

Use ultrawork only when:

1. delegation is available
2. the parallel gate passes
3. the benefit of parallelism is likely to exceed orchestration cost

If not, downgrade immediately to `omx-serial` or `omx-autopilot`.

## Workflow

1. Split the task into 2-5 independent packets with explicit ownership and verify commands.
2. Launch bounded parallel jobs only for non-overlapping packets.
3. Keep healthy packets moving while isolating failures.
4. Integrate in a deterministic order.
5. Run shared verification before declaring success.

## Rules

- Never allow overlapping writes.
- Stop spawning new write jobs after repeated permission or API failures.
- Keep state minimal, resumable, and easy to clear.
