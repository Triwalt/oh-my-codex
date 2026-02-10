---
name: omx-swarm
description: "N-worker coordinated execution for Codex using async claude_code jobs, task claiming, and ownership-safe parallelism."
---

# Swarm Mode

Swarm mode runs multiple workers on a shared task pool for high-throughput implementation.

## Command-Style Triggers

Treat these as swarm activation:
- `/swarm <task>`
- `/swarm N <task>`
- `$omx-swarm <task>`
- "swarm mode", "multi-worker", "parallel workers"

## Goals

1. Split a large task into independent work packets.
2. Execute packets in parallel with bounded worker count.
3. Prevent write conflicts through strict file ownership.
4. Recover from worker failures without losing overall progress.

## Workflow

### Phase 1: Decompose
1. Analyze task and produce packet list.
2. Each packet must include:
   - `packetId`
   - `objective`
   - `ownedFiles` (glob list)
   - `verifyCommand`
   - `riskLevel`
3. Persist state:
   `omx_state_write(mode: "swarm", data: { phase: "decomposed", active: true, packets: [...] })`

### Phase 2: Plan Worker Count
1. Choose worker count `N` from user input or default.
2. Clamp to safe bounds:
   - `N >= 1`
   - `N <= OMX_MAX_RUNNING_JOBS` (server cap, commonly 3)
   - `N <= number of packets`
3. Persist worker plan in state.

### Phase 3: Claim and Launch
1. Initialize task ledger with statuses: `pending | claimed | done | failed`.
2. Assign one pending packet per worker.
3. Launch each worker using `claude_code` with packet-specific prompt.
4. Persist job map:
   `omx_state_write(mode: "swarm", data: { phase: "running", jobs: [...] })`

### Phase 4: Monitor and Reclaim
1. Poll all running jobs with `claude_code_status`.
2. On success, mark packet `done`.
3. On failure, mark packet `failed`, collect error, and optionally requeue.
4. If a worker stalls, cancel and reclaim packet.

### Phase 5: Integrate
1. Merge packet outputs in deterministic order.
2. Resolve cross-packet conflicts before global verification.
3. Run project-level checks.

### Phase 6: Complete
1. Ensure all packets are `done` or explicitly accepted as failed.
2. Persist summary and clear state:
   - `omx_state_write(mode: "swarm", data: { phase: "complete" })`
   - `omx_state_clear(mode: "swarm")`

## Worker Prompt Template

```text
Your work folder is {workFolder}

SWARM PACKET: {packetId}
OBJECTIVE: {objective}
OWNED FILES ONLY: {ownedFiles}

Rules:
- Modify only owned files.
- Run packet verification: {verifyCommand}
- Report changed files and verification result.
```

## Rules

- Never run two workers on overlapping ownership sets.
- Keep packets small and mergeable.
- Prefer retry-once for transient failures; escalate persistent failures.
- Always run global verification after packet merge.
- If permission mode blocks delegated writes, stop scheduling new write packets and surface blocker details.

## Suggested State Schema

```json
{
  "active": true,
  "phase": "decomposed | running | integrating | verifying | complete",
  "workerCount": 3,
  "packets": [
    {
      "packetId": "P1",
      "objective": "Add request validation",
      "ownedFiles": ["src/api/**"],
      "verifyCommand": "npm test -- api",
      "status": "pending"
    }
  ],
  "jobs": [
    {
      "packetId": "P1",
      "jobId": "abcd1234",
      "status": "running"
    }
  ],
  "errors": []
}
```
