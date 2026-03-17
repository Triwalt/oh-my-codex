---
name: omx-code-review
description: "Comprehensive code review via Claude Code delegation. Use when the user asks for 'code review', 'review this', 'check my code', or wants quality/security/performance analysis of their code."
---

# Code Review Mode

Run a correctness-first review, using delegation only when the runtime contract allows it.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Workflow

1. Scope the review to files, diffs, or the whole project.
2. Review for correctness, security, performance, maintainability, error handling, and tests.
3. If delegation is unavailable, perform the review directly with native Codex.
4. Present findings ordered by severity, then ask whether to fix the highest-priority issues.

## Rules

- Focus on actionable findings over style nits.
- Prioritize security and correctness.
- Include file and line references whenever possible.
