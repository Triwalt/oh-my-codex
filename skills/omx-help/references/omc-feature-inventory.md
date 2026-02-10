# OMC Feature Inventory and Codex Port Map

Snapshot date: 2026-02-10
Source root: `C:/Users/19667/.claude/plugins/cache/omc/oh-my-claudecode/3.7.0`

## 1) OMC Command Inventory (Observed)

| Command | Purpose |
|---|---|
| analyze | Deep analysis and investigation |
| autopilot | Full autonomous execution from idea to working code |
| build-fix | Fix build and TypeScript errors with minimal changes |
| cancel | Cancel active modes (autopilot, ralph, ultrawork, ecomode, ultraqa, swarm, ultrapilot, pipeline) |
| code-review | Comprehensive code review |
| deepinit | Codebase initialization with AGENTS.md hierarchy |
| deepsearch | Thorough codebase search |
| doctor | Diagnose and fix OMC installation issues |
| ecomode | Token-efficient parallel execution mode |
| help | User help and guidance |
| hud | HUD display configuration |
| learn-about-omc | Usage analytics and recommendations |
| learner | Extract reusable skill from conversation |
| mcp-setup | Configure MCP servers |
| note | Save resilient session notes |
| omc-setup | One-time setup |
| pipeline | Sequential/branching agent pipelines |
| plan | Planning session with Planner |
| psm | Project session manager (worktree + tmux) |
| ralph | Persistent loop until completion |
| ralph-init | Initialize PRD for ralph loop |
| ralplan | Iterative planning with planner + architect + critic |
| release | Automated release workflow |
| research | Parallel scientist-agent research |
| review | Critic review of plans |
| security-review | Security-focused code review |
| swarm | N-agent shared task list with SQLite claiming |
| tdd | Test-driven development workflow |
| ultrapilot | Parallel autopilot with file ownership partitioning |
| ultraqa | QA cycle loop (test -> diagnose -> fix -> repeat) |
| ultrawork | Maximum-throughput parallel agent orchestration |

## 2) OMC Architecture Features (Observed)

- Multi-agent system with specialist roles (planner, critic, architect, executor, researcher, explorer, scientist, qa-tester, designer, writer, etc.).
- Tiered model routing (low/medium/high) by task complexity.
- Hook-driven automation (keyword detection, stop enforcement, todo continuation, rules injection, slash command expansion, persistent modes).
- Persistent runtime state in `.omc/` and `~/.claude/.omc/`.
- High-level workflows: ultrawork, swarm, pipeline, ralplan, ultrapilot, ultraqa.

## 3) Selected Features Reproduced in OMX

Priority was chosen for Codex-native practicality and immediate value.

### Reproduced / Added

1. `omx-ultrawork`
   - Parallel async delegation via `claude_code`.
   - Ownership-first packet decomposition.
   - Stateful monitoring and integration steps.

2. `omx-swarm`
   - N-worker coordination over shared packet ledger.
   - Claim/run/complete lifecycle with recovery behavior.
   - Worker-count clamped to OMX runtime limits.

3. `omx-pipeline`
   - Stage-based orchestration with handoff context.
   - Preset workflows (review/implement/debug/research/refactor/security).
   - Retry/fallback/abort error policy model.

4. `omx-plan` upgraded for versioned iteration
   - Supports `v1`, `v2`, ... plan deltas.
   - Better state persistence for multi-round planning.

5. `omx-ralplan`
   - Consensus planning loop: planner -> architect -> critic.
   - Max-iteration and unresolved-risk handling.

6. `omx-cancel`
   - Unified cancellation for running jobs and active workflow states.

7. `omx-serial`
   - Deterministic single-agent linear execution for Codex.
   - Anti-drift controls to reduce clarification loops in unattended runs.
   - Escalation gate to pipeline/ultrawork only when serial stalls.

8. `omx-help` upgraded
   - OMC-style command mapping (`/plan`, `/serial`, `/ralplan`, `/ultrawork`, `/swarm`, `/pipeline`, `/cancel`).

### Deferred (Next Waves)

- Full SQLite-backed atomic claiming for swarm packets.
- HUD and richer observability overlays.
- Hook-equivalent auto keyword detectors.
- Project session manager equivalent (worktree + tmux orchestration).
- UltraQA-style autonomous QA cycling mode.

## 4) Codex-Specific Optimization Decisions

- Use `claude_code` async jobs as the primary worker primitive (portable across Codex sessions).
- Bound parallelism to OMX server limits (`OMX_MAX_RUNNING_JOBS`) for stability.
- Favor explicit state tool calls over hidden hook side effects.
- Emphasize file ownership partitioning before parallel writes.
- Keep workflow controls in skill-level instructions so users can trigger with explicit `$omx-*` or command-like prompts.
- Prefer deterministic stage handoff contracts in pipeline mode for traceability.
- Add serial anti-drift execution path for low-overhead, linear tasks.

## 5) Migration Risk Notes

- If OMX runs Claude Code with permission mode `respect`, delegated write tasks may pause for confirmation.
- Parallel workflows should include an ownership map to avoid conflicting edits.
- Consensus planning can over-iterate; cap loops and surface unresolved tradeoffs explicitly.
- Swarm throughput depends on packet quality; poor decomposition reduces speedup.
- Serial mode can still drift when prompts are vague; keep task objective + verify command explicit.
