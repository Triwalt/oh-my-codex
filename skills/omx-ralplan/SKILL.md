---
name: omx-ralplan
description: "Iterative consensus planning workflow inspired by OMC ralplan. Uses planner, architect, and critic loops until convergence."
---

# Ralplan Mode

Ralplan is the consensus planning loop for risky or cross-cutting work.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Iteration Lenses

1. Planner: propose the next candidate plan.
2. Architect: test feasibility, sequencing, and dependencies.
3. Critic: challenge risks, blind spots, and verification quality.

## Workflow

1. Capture goal, scope, constraints, and success criteria.
2. Run the three-lens loop for up to 5 iterations.
3. Make deltas explicit from one version to the next.
4. Stop when the user approves, the critic has no high-severity objections, or the iteration cap is reached.
5. If state tools are unavailable, keep the full decision trail inline instead of relying on remote state.

## Rules

- Ralplan is planning-only.
- Always include a verification strategy before calling the plan converged.
- End with a clear execution recommendation.
