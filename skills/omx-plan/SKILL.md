---
name: omx-plan
description: "Strategic planning for complex tasks. Supports versioned iteration and Codex-friendly command-style triggers such as /plan and plan v2."
---

# Planning Mode

Planning mode is for scope -> analyze -> design -> iterate -> approve.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Workflow

1. Gather requirements, constraints, and hidden assumptions.
2. Break the work into concrete steps with file-level scope when possible.
3. Include at least one alternative path and why it is not the default.
4. Version the plan as `v1`, `v2`, and so on.
5. If state tools are unavailable, keep the version trail inline in the response instead of forcing remote state writes.

## Rules

- Planning mode does not implement code.
- Call out risks, unknowns, and verification early.
- End with a clear handoff recommendation, usually `omx-autopilot` or `omx-serial`.
