---
name: omx-plan
description: "Strategic planning for complex tasks. Supports versioned iteration and Codex-friendly command-style triggers such as /plan and plan v2."
---

# Planning Mode

Structured planning for Codex: scope -> analyze -> design -> iterate -> approve.

## Command-Style Triggers

Treat the following as planning mode requests:
- `/plan <task>`
- `$omx-plan <task>`
- "plan this", "how should we", "make a plan"
- "iterate plan", "revise plan v2", "update plan"

## Workflow

### Phase 1: Gather Context
1. Explore the codebase and constraints.
2. Identify explicit requirements and hidden assumptions.
3. Persist state:
   `omx_state_write(mode: "plan", data: { phase: "gathering", active: true })`

### Phase 2: Analyze
1. Break the problem into components and dependencies.
2. Identify risk, unknowns, and decision points.
3. If needed, delegate deep analysis to `claude_code` for codebase-specific facts.

### Phase 3: Draft Plan v1
1. Propose approach and rejected alternatives.
2. Define implementation order and touched files.
3. Persist draft metadata:
   `omx_state_write(mode: "plan", data: { phase: "drafted", iteration: 1, currentVersion: "v1" })`

### Phase 4: Iteration Loop (v2, v3, ...)
1. Collect user feedback and classify as scope, constraint, or quality concern.
2. Produce next version with a clear delta section.
3. Persist version history:
   `omx_state_write(mode: "plan", data: { phase: "iterating", iteration: N, currentVersion: "vN" })`
4. Continue until user approves or requests consensus planning (`omx-ralplan`).

### Phase 5: Approval and Handoff
1. Mark approved state:
   `omx_state_write(mode: "plan", data: { phase: "approved", approved: true })`
2. Offer execution via `omx-autopilot`.

## Output Template

```markdown
## Goal
<what we are building>

## Plan Version
vN

## Approach
<how and why>

## Steps
1. <step> - <files>
2. <step> - <files>

## Risks and Mitigations
- <risk> -> <mitigation>

## Verification
- <tests/checks>

## Delta From Previous Version
- <what changed since vN-1>
```

## Rules

- Planning mode does not implement code.
- Always include at least one alternative path.
- Name concrete files/functions/patterns whenever possible.
- Keep a versioned trail in `plan` state so iterations survive context loss.
