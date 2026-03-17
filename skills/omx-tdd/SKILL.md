---
name: omx-tdd
description: "Test-driven development workflow. Use when the user says 'tdd', 'test first', 'write tests first', 'red green refactor', or when implementing features where test coverage is critical."
---

# TDD Mode

Enforce Red -> Green -> Refactor.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Workflow

1. Red: write failing tests first and confirm they fail for the right reason.
2. Green: implement the minimum code needed to make them pass.
3. Refactor: improve quality without changing behavior.
4. Re-run tests after every phase.
5. If state tools are unavailable, track the current phase inline instead of forcing remote state writes.

## Rules

- Never implement before the tests exist.
- Keep the green phase minimal.
- Undo any refactor that breaks tests.
