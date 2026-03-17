---
name: omx-pipeline
description: "Stage-based workflow orchestration for Codex. Supports sequential and hybrid parallel pipelines with explicit stage handoff."
---

# Pipeline Mode

Pipeline mode is for explicit stage handoff: small stages, clear outputs, hard verification.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Use When

- diagnosis and implementation should be separated
- the task benefits from an audit trail
- serial execution is still preferred, but one large prompt would be too blurry

## Workflow

1. Pick a short stage chain such as `diagnose -> implement -> verify`.
2. Keep each stage scoped to one purpose and pass only the minimal context forward.
3. If delegation is unavailable, run the stages locally with native Codex prompts.
4. Retry a failed stage once; then either fall back to serial repair or stop with a concrete blocker.
5. Do not skip the final verification stage for code changes.

## Rules

- Prefer short stages over one giant stage.
- Use parallel stage groups only when the runtime contract says parallel is safe.
- If state tools are available, store only concise stage summaries and clear state on success.
