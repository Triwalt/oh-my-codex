---
name: omx-serial
description: "Deterministic single-agent serial workflow for Codex. Optimized for stability, low drift, and reliable time-to-green on linear tasks."
---

# Serial Mode

Serial mode runs a single workstream: reproduce -> fix -> verify -> done.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` before doing anything else.

## Use When

Choose serial mode when:

1. the task is linear or ownership is ambiguous
2. you want minimum orchestration overhead
3. parallel delegation is unavailable or unnecessary

## Workflow

1. Lock the objective, constraints, and verification command.
2. Run the verification command before editing whenever possible.
3. Apply the smallest useful code change.
4. Re-run the same verification command until it passes or 2 focused retries are exhausted.
5. Escalate only if the serial loop stalls and the runtime contract says parallel is safe.

## Reliability Rules

- Assume the task is actionable unless ambiguity creates destructive risk.
- Do not drift into unrelated modes or ask open-ended "what should I do" questions.
- Prefer editing only files tied to the active failure set.
- If state tools are available, write compact UTF-8 state. If not, skip persistence.

## Output

- PASS or FAIL
- changed files
- verification command and final result
- whether fallback or escalation was used
