# omx Runtime Contract

Apply this contract before using any `omx-*` skill that mentions `omx_*` state tools or `claude_code*`.

## Runtime Preflight

1. Read the active config at `~/.codex/config.toml`.
2. Treat `omx` as available only when `mcp_servers.omx` is configured and the referenced server path exists.
3. Treat delegation as available only when `claude_code*` tools are actually callable.
4. Treat state as available only when `omx_state*` / `omx_note*` tools are callable.

## Fallback Rules

- If `omx` is unavailable, run the workflow with native Codex tools only.
- If delegation is unavailable, collapse `autopilot` / `pipeline` / `swarm` / `ultrawork` to serial local execution.
- If state is unavailable, do not invent remote state writes. Keep notes inline or use workspace-local scratch only if the user asked for persistence.
- If permissions or API failures happen more than once, stop scheduling new parallel write work and fall back to serial repair.

## Parallel Gate

Parallel execution is allowed only when all conditions below are true:

- delegation is available
- at least 2 non-overlapping ownership packets exist
- each packet has a packet-level verify command
- a global verify command exists

Otherwise, use serial mode.

## State Hygiene

- Write UTF-8 JSON only.
- Keep one active workspace per note bucket.
- Archive invalid or stale state instead of overwriting unreadable files in place.
- Clear or mark inactive any workflow state that is complete or older than 24 hours without progress.
- Prefer a clean empty state directory over keeping stale `active: true` files.

## Bench Metrics

Prefer measuring:

- success rate
- time-to-green
- retries
- prompt size
- tool failure rate
- human takeover rate
