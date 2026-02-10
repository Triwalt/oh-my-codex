---
name: omx-pipeline
description: "Stage-based workflow orchestration for Codex. Supports sequential and hybrid parallel pipelines with explicit stage handoff."
---

# Pipeline Mode

Pipeline mode chains work through explicit stages so each stage receives prior outputs.

## Command-Style Triggers

Treat these as pipeline activation:
- `/pipeline <preset> <task>`
- `/pipeline <custom stages> <task>`
- `$omx-pipeline <task>`
- "run a pipeline", "stage-based workflow"

## Built-in Presets

- `review`: explore -> architect -> critic -> implement
- `implement`: plan -> implement -> verify
- `debug`: locate -> diagnose -> fix -> verify
- `research`: external research + codebase analysis -> synthesis
- `refactor`: map dependencies -> strategy -> execute -> regression checks
- `security`: audit -> fix -> re-audit

## Workflow

### Phase 1: Build Pipeline Graph
1. Parse preset or custom stage chain.
2. Validate stage dependencies.
3. Persist state:
   `omx_state_write(mode: "pipeline", data: { phase: "planned", active: true, stages: [...] })`

### Phase 2: Execute Stages
1. Run stage in order unless marked as a parallel stage group.
2. Delegate each stage to `claude_code`.
3. Capture stage output artifacts and decisions.
4. Feed structured context into next stage.

### Phase 3: Error Handling
On stage failure, choose one strategy:
- `retry`: rerun same stage once.
- `fallback`: escalate to stronger analysis/fix stage.
- `abort`: stop pipeline and report failure context.
Persist decision in state.

### Phase 4: Final Verification
1. Run final verification commands for task scope.
2. Confirm end-state matches acceptance criteria.
3. Clear state on success.

## Stage Handoff Contract

Each stage should pass this minimal context:

```json
{
  "originalTask": "...",
  "currentStage": "diagnose",
  "previousStages": [
    {
      "stage": "locate",
      "result": "...",
      "changedFiles": ["..."]
    }
  ],
  "constraints": ["..."],
  "acceptanceCriteria": ["..."]
}
```

## Rules

- Keep stage goals narrowly scoped.
- Do not skip verification stage for code-changing pipelines.
- Preserve an explicit decision log when fallback paths are used.
- Prefer short stages over one giant stage.

## Suggested State Schema

```json
{
  "active": true,
  "phase": "planned | running | verifying | complete | failed",
  "pipelineId": "uuid",
  "stages": [
    {
      "name": "locate",
      "type": "analysis",
      "status": "completed",
      "jobId": "abcd1234",
      "summary": "..."
    }
  ],
  "currentStageIndex": 1,
  "errorPolicy": "retry",
  "decisionLog": []
}
```
