---
name: omx-analyze
description: "Deep analysis and debugging via Claude Code. Use when the user says 'analyze', 'debug', 'investigate', 'why is this', 'what's causing', or needs deep understanding of code behavior, bugs, or architecture."
---

# Analyze Mode

Deep investigation: reproduce -> trace -> diagnose -> recommend.

Apply the runtime contract at `skills/omx-help/references/omx-runtime-contract.md` first.

## Workflow

1. Reproduce the issue or inspect the relevant code path.
2. Trace execution until the root cause is clear.
3. Explain why it happens, not just where.
4. If delegation is unavailable, do the investigation directly with native Codex.
5. Present actionable recommendations and ask before fixing.

## Rules

- Focus on root causes over symptoms.
- Use concrete evidence from code, tests, or runtime behavior.
- Keep analysis separate from implementation unless the user asks to fix it.
