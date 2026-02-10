---
name: omx-ultrawork
description: "Maximum-throughput parallel workflow for Codex. Recreates OMC ultrawork behavior with async claude_code jobs, file ownership partitioning, and strict verification."
---

# Ultrawork Mode

High-throughput multi-agent orchestration adapted for Codex.

## Command-Style Triggers

Treat the following as ultrawork activation:
- `/ultrawork <task>`
- `$omx-ultrawork <task>`
- "ultrawork", "parallel mode", "turbo mode", "high throughput"

## Core Behavior

1. Parallel execution for independent work packets.
2. Aggressive delegation via async `claude_code` jobs.
3. Ownership-first scheduling to avoid write conflicts.
4. Persistence until verification passes.
5. Explicit state tracking for resumability.

## Codex-Optimized Workflow

### Phase 1: Decompose
1. Split request into 2-5 independent work packets.
2. Assign ownership boundaries per packet:
   - file globs
   - verification command
   - risk level
3. Persist state:
   `omx_state_write(mode: "ultrawork", data: { phase: "decomposed", active: true, packets: [...] })`

### Phase 2: Launch Parallel Jobs
1. Start jobs with `claude_code` for non-overlapping packets.
2. Respect max parallelism from OMX server (`OMX_MAX_RUNNING_JOBS`, default 3).
3. Persist job map in state:
   `omx_state_write(mode: "ultrawork", data: { phase: "running", jobs: [{ packetId, jobId, owner }] })`

### Phase 3: Monitor and Recover
1. Poll each job using `claude_code_status`.
2. If one job fails, isolate the failing packet and continue healthy packets.
3. Record failures in state with remediation notes.

### Phase 4: Integrate
1. Merge outputs packet by packet.
2. Resolve cross-packet conflicts before verification.
3. Run shared checks (build, tests, lint).

### Phase 5: Verify and Complete
1. Verify packet-level checks and global checks.
2. Clear state when done:
   `omx_state_clear(mode: "ultrawork")`
3. Report throughput summary: packets, jobs, conflicts, verification status.

## Rules

- Ultrawork is orchestration-first; avoid ad-hoc serial coding when parallel decomposition is possible.
- Never run concurrent jobs that own overlapping files.
- Keep packets small enough for deterministic merge and rollback.
- If permission mode prevents delegated edits, stop spawning new write jobs and surface the blocker explicitly.

## Suggested State Schema

```json
{
  "active": true,
  "phase": "decomposed | running | integrating | verifying | complete",
  "packets": [
    {
      "id": "P1",
      "owner": "api-worker",
      "files": ["src/api/**"],
      "verify": "npm test -- api"
    }
  ],
  "jobs": [
    {
      "packetId": "P1",
      "jobId": "abcd1234",
      "status": "running"
    }
  ],
  "failures": [],
  "verification": {
    "global": "pending"
  }
}
```
