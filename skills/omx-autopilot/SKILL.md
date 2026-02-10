---
name: omx-autopilot
description: "Full autonomous execution from idea to working code. Uses serial mode for linear tasks and ultrawork-style parallel execution for independent workstreams."
---

# Autopilot Mode

Autonomous execution for Codex: analyze -> plan -> implement -> verify -> done.

## Workflow

### Phase 1: Understand
1. Read the request and detect target work folder.
2. Explore key files and project conventions.
3. Ask at most one clarification round only when ambiguity materially changes implementation.

### Phase 2: Plan
1. Break work into concrete steps (max 10).
2. Detect parallelizable workstreams (independent file ownership).
3. Choose execution mode:
   - `serial`: default for linear or ambiguous-ownership tasks.
   - `parallel`: only when non-overlapping ownership is clear.
4. Persist plan state:
   `omx_state_write(mode: "autopilot", data: { phase: "planning", steps: [...], currentStep: 0, executionMode: "serial", active: true })`

### Phase 3: Implement
For each step:
1. Update progress state with `currentStep` and `completedSteps`.
2. If `executionMode = serial`, run single-track fix loop:
   - reproduce failures first,
   - apply minimal edits,
   - re-run same verification command,
   - avoid open-ended clarification drift.
3. If `executionMode = parallel` and 2+ independent streams exist, run ultrawork-style parallel jobs (bounded concurrency).
4. Poll jobs with `claude_code_status` and capture outputs.

### Phase 4: Verify
1. Run tests, typecheck, and lint (or project-specific verification commands).
2. If failures occur, delegate fixes and re-run verification.
3. Do not finish until verification is clean or blockers are explicit.

### Phase 5: Complete
1. Mark complete and clear state:
   - `omx_state_write(mode: "autopilot", data: { phase: "complete" })`
   - `omx_state_clear(mode: "autopilot")`
2. Report what changed, where, and how to run it.

## Codex Reliability Controls

- Treat task as actionable by default in serial mode; avoid repeated "what should I do" loops.
- Keep prompts short, explicit, and verify-command-centric.
- Use bounded retries (max 2) before escalating from serial to pipeline.
- Only escalate to parallel modes when ownership map is explicit.

## Rules

- Never stop mid-task without a concrete blocker report.
- Prefer serial execution unless ownership boundaries are clearly parallelizable.
- Avoid concurrent writes to the same file group.
- Track progress in state to survive context loss.
- Always verify implementation claims before finalizing.

## Suggested State Schema

```json
{
  "phase": "planning | implementing | verifying | complete",
  "executionMode": "serial | parallel",
  "steps": ["step description"],
  "currentStep": 0,
  "completedSteps": [],
  "parallel": {
    "enabled": false,
    "workers": [],
    "jobIds": []
  },
  "errors": [],
  "active": true
}
```
