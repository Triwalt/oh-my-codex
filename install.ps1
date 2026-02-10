param(
  [switch]$InstallAgents,
  [switch]$OverwriteSkills,
  [ValidateSet("skip", "respect")]
  [string]$PermissionMode = "respect"
)

$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "[omx] $msg" }
function Warn($msg) { Write-Host "[omx][warn] $msg" -ForegroundColor Yellow }

$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$codexDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$configPath = Join-Path $codexDir "config.toml"
$serverDir = Join-Path $codexDir "mcp-servers\omx"
$serverPath = Join-Path $serverDir "server.mjs"
$serverPathToml = ($serverPath -replace "\\", "/")

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw "Node.js is required (v20+)."
}

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
  Warn "Codex CLI not found. Install: npm install -g @openai/codex"
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  Warn "Claude CLI not found. Install: npm install -g @anthropic-ai/claude-code"
}

New-Item -ItemType Directory -Path $serverDir -Force | Out-Null
Copy-Item (Join-Path $repoDir "mcp-server\server.mjs") $serverPath -Force
Copy-Item (Join-Path $repoDir "mcp-server\package.json") (Join-Path $serverDir "package.json") -Force
Copy-Item (Join-Path $repoDir "mcp-server\smoke-test.mjs") (Join-Path $serverDir "smoke-test.mjs") -Force

Info "Installing MCP server dependencies..."
Push-Location $serverDir
npm install --omit=dev --silent | Out-Null
if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
Pop-Location

$skills = @(
  "omx-autopilot",
  "omx-serial",
  "omx-plan",
  "omx-ralplan",
  "omx-pipeline",
  "omx-swarm",
  "omx-ultrawork",
  "omx-cancel",
  "omx-research",
  "omx-code-review",
  "omx-tdd",
  "omx-analyze",
  "omx-help",
  "claude-code-mcp"
)

$skillsDir = Join-Path $codexDir "skills"
New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null

foreach ($skill in $skills) {
  $src = Join-Path $repoDir ("skills\" + $skill)
  $dst = Join-Path $skillsDir $skill

  if (-not (Test-Path $src)) {
    Warn "Skipping missing skill source: $src"
    continue
  }

  if (Test-Path $dst) {
    if ($OverwriteSkills) {
      $backup = "$dst.bak.$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
      Move-Item $dst $backup -Force
      Info "Backed up existing $skill to $backup"
    } else {
      Warn "Skill $skill already exists. Keeping existing copy (use -OverwriteSkills to replace)."
      continue
    }
  }

  Copy-Item $src $dst -Recurse -Force
}

if ($InstallAgents) {
  New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
  $agentsPath = Join-Path $codexDir "AGENTS.md"
  if (Test-Path $agentsPath) {
    $backup = "$agentsPath.bak.$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
    Copy-Item $agentsPath $backup -Force
    Info "Backed up existing AGENTS.md to $backup"
  }
  Copy-Item (Join-Path $repoDir "AGENTS.template.md") $agentsPath -Force
  Info "Installed AGENTS.md template"
} else {
  Warn "Skipped AGENTS.md install (use -InstallAgents to install)."
}

New-Item -ItemType Directory -Path $codexDir -Force | Out-Null
if (-not (Test-Path $configPath)) {
  New-Item -ItemType File -Path $configPath | Out-Null
}

$configText = Get-Content $configPath -Raw
if ($configText -match "(?m)^\[mcp_servers\.omx\]") {
  Warn "config.toml already contains [mcp_servers.omx]; not modifying existing block."
} else {
  @"

# oh-my-codex orchestration server
[mcp_servers.omx]
command = "node"
args = ["$serverPathToml"]
startup_timeout_sec = 15
tool_timeout_sec = 45

[mcp_servers.omx.env]
# skip: autonomous mode (fewer prompts)
# respect: ask Claude Code to use normal permission flow
OMX_CLAUDE_PERMISSION_MODE = "$PermissionMode"
OMX_MAX_RUNNING_JOBS = "3"
"@ | Add-Content $configPath

  Info "Added omx MCP server block to $configPath"
}

Info "Running initialize verification..."
$payload = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"install-verify","version":"1.0.0"}}}'
$out = $payload | node $serverPath 2>$null
if ($LASTEXITCODE -ne 0) { throw "initialize verification command failed" }
if ($out -match '"name":"omx"') {
  Info "Initialize verification passed"
} else {
  Warn "Initialize verification inconclusive."
}

Info "Running smoke test..."
Push-Location $serverDir
try {
  npm run smoke | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "smoke test failed" }
  Info "Smoke test passed"
}
finally {
  Pop-Location
}

Write-Host ""
Info "Installation complete."
Info "MCP server: $serverPath"
Info "Skills dir:  $skillsDir"
Info "Config:      $configPath"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1) Start Codex: codex"
Write-Host "  2) Ask: `"omx help`""
Write-Host "  3) Optional hardening: set OMX_ALLOWED_WORKFOLDER_ROOTS in mcp_servers.omx.env"
