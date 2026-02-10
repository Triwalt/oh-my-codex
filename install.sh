#!/usr/bin/env bash
set -euo pipefail

# oh-my-codex installer
# Installs the omx MCP server and skills for Codex CLI.

CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_PATH="$CODEX_DIR/config.toml"
SERVER_DIR="$CODEX_DIR/mcp-servers/omx"
SERVER_PATH="$SERVER_DIR/server.mjs"

INSTALL_AGENTS="${INSTALL_AGENTS:-false}"          # true|false
OVERWRITE_SKILLS="${OVERWRITE_SKILLS:-false}"      # true|false
OMX_PERMISSION_MODE="${OMX_PERMISSION_MODE:-respect}" # skip|respect

if [[ "$OMX_PERMISSION_MODE" != "skip" && "$OMX_PERMISSION_MODE" != "respect" ]]; then
  echo "[omx] Error: OMX_PERMISSION_MODE must be 'skip' or 'respect'."
  exit 1
fi

info() { echo "[omx] $1"; }
warn() { echo "[omx][warn] $1"; }

if ! command -v node >/dev/null 2>&1; then
  echo "[omx] Error: Node.js is required (v20+)."
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  warn "Codex CLI not found. Install: npm install -g @openai/codex"
fi

if ! command -v claude >/dev/null 2>&1; then
  warn "Claude CLI not found. Install: npm install -g @anthropic-ai/claude-code"
fi

mkdir -p "$SERVER_DIR"
cp "$REPO_DIR/mcp-server/server.mjs" "$SERVER_PATH"
cp "$REPO_DIR/mcp-server/package.json" "$SERVER_DIR/package.json"
cp "$REPO_DIR/mcp-server/smoke-test.mjs" "$SERVER_DIR/smoke-test.mjs"

info "Installing MCP server dependencies..."
(
  cd "$SERVER_DIR"
  npm install --omit=dev --silent
)

SKILLS=(
  omx-autopilot
  omx-serial
  omx-plan
  omx-ralplan
  omx-pipeline
  omx-swarm
  omx-ultrawork
  omx-cancel
  omx-research
  omx-code-review
  omx-tdd
  omx-analyze
  omx-help
  claude-code-mcp
)

mkdir -p "$CODEX_DIR/skills"
for skill in "${SKILLS[@]}"; do
  src="$REPO_DIR/skills/$skill"
  dst="$CODEX_DIR/skills/$skill"

  if [[ ! -d "$src" ]]; then
    warn "Skipping missing skill source: $src"
    continue
  fi

  if [[ -d "$dst" ]]; then
    if [[ "$OVERWRITE_SKILLS" == "true" ]]; then
      backup="$dst.bak.$(date +%s)"
      mv "$dst" "$backup"
      info "Backed up existing $skill to $backup"
    else
      warn "Skill $skill already exists. Keeping existing copy (set OVERWRITE_SKILLS=true to replace)."
      continue
    fi
  fi

  cp -R "$src" "$dst"
done

if [[ "$INSTALL_AGENTS" == "true" ]]; then
  mkdir -p "$CODEX_DIR"
  if [[ -f "$CODEX_DIR/AGENTS.md" ]]; then
    backup="$CODEX_DIR/AGENTS.md.bak.$(date +%s)"
    cp "$CODEX_DIR/AGENTS.md" "$backup"
    info "Backed up existing AGENTS.md to $backup"
  fi
  cp "$REPO_DIR/AGENTS.template.md" "$CODEX_DIR/AGENTS.md"
  info "Installed AGENTS.md template"
else
  warn "Skipped AGENTS.md install (set INSTALL_AGENTS=true to install)."
fi

mkdir -p "$CODEX_DIR"
touch "$CONFIG_PATH"

if grep -q "\[mcp_servers\.omx\]" "$CONFIG_PATH" 2>/dev/null; then
  warn "config.toml already contains [mcp_servers.omx]; not modifying existing block."
else
  cat >> "$CONFIG_PATH" <<EOF

# oh-my-codex orchestration server
[mcp_servers.omx]
command = "node"
args = ["$SERVER_PATH"]
startup_timeout_sec = 15
tool_timeout_sec = 45

[mcp_servers.omx.env]
# skip: autonomous mode (fewer prompts)
# respect: ask Claude Code to use normal permission flow
OMX_CLAUDE_PERMISSION_MODE = "$OMX_PERMISSION_MODE"
OMX_MAX_RUNNING_JOBS = "3"
EOF
  info "Added omx MCP server block to $CONFIG_PATH"
fi

info "Running initialize verification..."
VERIFY_PAYLOAD='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"install-verify","version":"1.0.0"}}}'
VERIFY_OUT=$(printf "%s\n" "$VERIFY_PAYLOAD" | node "$SERVER_PATH" 2>/dev/null | head -c 400 || true)

if echo "$VERIFY_OUT" | grep -q '"name":"omx"'; then
  info "Initialize verification passed"
else
  warn "Initialize verification inconclusive. You can test manually with: codex"
fi

info "Running smoke test..."
(
  cd "$SERVER_DIR"
  npm run smoke --silent
)
info "Smoke test passed"

cat <<EOF

[omx] Installation complete.
[omx] MCP server: $SERVER_PATH
[omx] Skills dir:  $CODEX_DIR/skills
[omx] Config:      $CONFIG_PATH

Next steps:
  1) Start Codex: codex
  2) Ask: "omx help"
  3) Optional hardening: set OMX_ALLOWED_WORKFOLDER_ROOTS in mcp_servers.omx.env
EOF
