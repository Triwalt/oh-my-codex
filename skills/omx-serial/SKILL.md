---
name: omx-serial
description: "Deterministic single-agent serial workflow for Codex. Optimized for stability, low drift, and reliable time-to-green on linear tasks."
---

# Serial Mode

Serial mode runs a single focused workstream: reproduce -> fix -> verify -> done.

## Command-Style Triggers

Treat these as serial activation:
- `/serial <task>`
- `$omx-serial <task>`
- "serial mode", "single-agent mode", "linear workflow"

## Why This Mode Exists

Use serial mode when:
1. Task scope is small-to-medium and mostly linear.
2. Parallel ownership partitioning is unclear.
3. You want the most predictable behavior with minimal orchestration overhead.

## Codex-Optimized Anti-Drift Controls

1. **Assume task is actionable by default.**
   - Do not ask open-ended clarification questions unless ambiguity causes destructive risk.
2. **Reproduce first.**
   - Run verification command before edits whenever possible.
3. **No workflow drift.**
   - Do not switch to unrelated modes or ask "what task should I do".
4. **Bound retries.**
   - Retry at most 2 focused fix loops before escalation.
5. **Close with hard verification.**
   - Finish only after verification is clean.

## Workflow

### Phase 1: Intake Lock
1. Capture task objective, constraints, and acceptance criteria.
2. Persist state:
   `omx_state_write(mode: "serial", data: { phase: "intake", active: true, objective: "..." })`
3. Unless safety-critical ambiguity exists, proceed without clarification round-trips.

### Phase 2: Baseline Verification
1. Identify verification command (tests/build/lint).
2. Run baseline check to reproduce failures.
3. Save failure summary to state.

### Phase 3: Single-Track Fix Loop
For each loop (max 2 retries):
1. Edit only files required by current failure set.
2. Re-run the same verification command.
3. Update state with attempt index and remaining failures.

### Phase 4: Escalation Gate
Escalate only if serial loop stalls:
- `pipeline` escalation: when diagnosis/implementation handoff is needed.
- `ultrawork` escalation: when independent ownership partitions are obvious.
Persist escalation decision before switching.

### Phase 5: Complete
1. On success, clear state:
   - `omx_state_write(mode: "serial", data: { phase: "complete" })`
   - `omx_state_clear(mode: "serial")`
2. Report:
   - changed files
   - verification command + result
   - whether escalation was used

## Suggested Delegation Prompt Skeleton

```text
SERIAL EXECUTION MODE

Task: {objective}
Work folder: {workFolder}
Constraints:
- Modify only: {allowed paths}
- Do not modify: {blocked paths}
- Verification command: {verifyCommand}

Rules:
- Assume task is fully actionable; do not ask for additional task clarification.
- Reproduce failures first, then apply minimal fixes.
- Re-run verification until clean or retry limit reached.
- Return PASS/FAIL, changed files, and final verification summary.
```

## Suggested State Schema

```json
{
  "active": true,
  "phase": "intake | baseline | fixing | verifying | escalated | complete | failed",
  "objective": "...",
  "constraints": [],
  "verifyCommand": "...",
  "attempt": 0,
  "maxAttempts": 2,
  "lastFailureSummary": "...",
  "escalation": {
    "used": false,
    "targetMode": null,
    "reason": null
  }
}
```
