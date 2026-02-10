---
name: omx-ralplan
description: "Iterative consensus planning workflow inspired by OMC ralplan. Uses planner, architect, and critic loops until convergence."
---

# Ralplan Mode

Consensus-driven planning loop for high-risk or cross-cutting work.

## Command-Style Triggers

Treat the following as ralplan activation:
- `/ralplan <task>`
- `$omx-ralplan <task>`
- "consensus plan", "iterate with critic", "ralplan"

## Loop Structure

Each iteration has three lenses:
1. Planner: produce or update candidate plan.
2. Architect: stress test technical feasibility and dependency order.
3. Critic: challenge risks, blind spots, and verification quality.

## Workflow

### Phase 1: Initialize
1. Capture goal, scope, constraints, and success criteria.
2. Persist initial state:
   `omx_state_write(mode: "ralplan", data: { phase: "iterating", iteration: 1, maxIterations: 5, active: true })`

### Phase 2: Iterative Consensus (max 5)
For iteration N:
1. Draft `Plan vN`.
2. Add architect review notes.
3. Add critic findings with severity tags.
4. Resolve findings and produce `Plan vN+1` when needed.
5. Persist progress after each iteration.

### Phase 3: Exit Conditions
Stop when one condition is met:
- User approves the plan.
- Critic has no high-severity objections.
- Max iteration reached (surface unresolved risks explicitly).

### Phase 4: Handoff
1. Save final plan snapshot to state.
2. Recommend execution with `omx-autopilot`.
3. Clear state only when user confirms finalization.

## Output Template

```markdown
## Goal
<target outcome>

## Consensus Iteration
vN / max 5

## Candidate Plan
<steps with file-level scope>

## Architect Review
- <dependency or feasibility notes>

## Critic Findings
- [high|medium|low] <finding>

## Decision Log
- <what changed this round and why>

## Open Risks
- <remaining risks>
```

## Rules

- Ralplan is planning-only; do not implement code in this mode.
- Keep deltas explicit between iterations.
- Always include verification strategy before marking consensus.
