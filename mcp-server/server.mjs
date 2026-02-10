#!/usr/bin/env node
// ==========================================================================
// omx - oh-my-codex MCP server
// Unified orchestration server: async Claude Code delegation, state
// management, session notepad, and project memory.
// ==========================================================================

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  readdirSync,
  unlinkSync,
  statSync,
} from "node:fs";
import { homedir } from "node:os";
import { join, dirname, isAbsolute, resolve, sep, delimiter } from "node:path";

// ==========================================================================
// Constants & Paths
// ==========================================================================
const HOME = homedir();
const OMX_DIR = join(HOME, ".codex", ".omx");
const STATE_DIR = join(OMX_DIR, "state");
const NOTEPAD_PATH = join(OMX_DIR, "notepad.json");

const MAX_COMPLETED_JOBS = parsePositiveInt(process.env.OMX_MAX_COMPLETED_JOBS, 100);
const MAX_RUNNING_JOBS = parsePositiveInt(process.env.OMX_MAX_RUNNING_JOBS, 3);
const MAX_OUTPUT_CHARS = parsePositiveInt(process.env.OMX_MAX_OUTPUT_CHARS, 200000);
const MAX_PROMPT_CHARS = parsePositiveInt(process.env.OMX_MAX_PROMPT_CHARS, 120000);
const MAX_WAIT_SECONDS = parsePositiveInt(process.env.OMX_MAX_WAIT_SECONDS, 25);
const MAX_NOTE_CHARS = parsePositiveInt(process.env.OMX_MAX_NOTE_CHARS, 4000);
const MAX_JOB_RUNTIME_SECONDS = parsePositiveInt(
  process.env.OMX_MAX_JOB_RUNTIME_SECONDS,
  0,
);
const CLAUDE_PERMISSION_MODE =
  (process.env.OMX_CLAUDE_PERMISSION_MODE || "skip").toLowerCase() === "respect"
    ? "respect"
    : "skip";
const SHOULD_SKIP_CLAUDE_PERMISSIONS = CLAUDE_PERMISSION_MODE === "skip";
const ALLOWED_WORKFOLDER_ROOTS = parseAllowedRoots(
  process.env.OMX_ALLOWED_WORKFOLDER_ROOTS,
);
const MODE_RE = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;

function parsePositiveInt(value, fallback) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function parseAllowedRoots(raw) {
  if (!raw) return [];
  return raw
    .split(delimiter)
    .map((v) => v.trim())
    .filter(Boolean)
    .map((v) => resolve(v));
}

function ensureDir(dir) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}
ensureDir(STATE_DIR);

// ==========================================================================
// Debug
// ==========================================================================
const DEBUG = process.env.MCP_OMX_DEBUG === "true";
function log(...args) {
  if (DEBUG) console.error("[omx]", ...args);
}

// ==========================================================================
// Claude CLI resolution
// ==========================================================================
function findClaudeCli() {
  const envName = process.env.CLAUDE_CLI_NAME;
  if (envName) return envName;
  const localPath = join(HOME, ".claude", "local", "claude");
  if (existsSync(localPath)) return localPath;
  return "claude";
}
const CLAUDE_CLI = findClaudeCli();

// ==========================================================================
// Job store (claude_code async)
// ==========================================================================
const jobs = new Map();

function pruneJobs() {
  const completed = [...jobs.entries()].filter(([, j]) => j.status !== "running");
  if (completed.length > MAX_COMPLETED_JOBS) {
    completed
      .sort((a, b) => (a[1].endTime || 0) - (b[1].endTime || 0))
      .slice(0, completed.length - MAX_COMPLETED_JOBS)
      .forEach(([id]) => jobs.delete(id));
  }
}

function countRunningJobs() {
  let running = 0;
  for (const job of jobs.values()) {
    if (job.status === "running") running += 1;
  }
  return running;
}

function uniqueJobId() {
  let id;
  do {
    id = randomUUID().slice(0, 8);
  } while (jobs.has(id));
  return id;
}

function appendBounded(current, chunk, limit) {
  const next = `${current}${chunk.toString()}`;
  if (next.length <= limit) return { value: next, truncated: false };
  return {
    value: next.slice(next.length - limit),
    truncated: true,
  };
}

function clearJobTimer(job) {
  if (job?._timeout) {
    clearTimeout(job._timeout);
    job._timeout = null;
  }
}

function armJobTimeout(job) {
  if (MAX_JOB_RUNTIME_SECONDS <= 0) return;
  job._timeout = setTimeout(() => {
    if (job.status !== "running" || !job._proc) return;
    const timedOutText = `\nJob timed out after ${MAX_JOB_RUNTIME_SECONDS} seconds.`;
    const nextErr = appendBounded(job.stderr, timedOutText, MAX_OUTPUT_CHARS);
    job.stderr = nextErr.value;
    job.stderrTruncated = job.stderrTruncated || nextErr.truncated;
    job.status = "failed";
    job.endTime = Date.now();

    try {
      job._proc.kill("SIGTERM");
    } catch {}

    setTimeout(() => {
      if (!job._proc) return;
      try {
        job._proc.kill("SIGKILL");
      } catch {}
    }, 5000);
  }, MAX_JOB_RUNTIME_SECONDS * 1000);
}

// ==========================================================================
// File helpers (state, notepad, memory)
// ==========================================================================
function readJSON(path, fallback) {
  try {
    return JSON.parse(readFileSync(path, "utf-8"));
  } catch {
    return fallback;
  }
}

function writeJSON(path, data) {
  ensureDir(dirname(path));
  writeFileSync(path, JSON.stringify(data, null, 2), "utf-8");
}

function normalizeMode(mode) {
  if (typeof mode !== "string" || !MODE_RE.test(mode)) {
    throw new Error(
      "mode must match /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/ (letters, numbers, _, -).",
    );
  }
  return mode;
}

function normalizePathForCompare(pathValue) {
  return process.platform === "win32" ? pathValue.toLowerCase() : pathValue;
}

function isInsideRoot(targetPath, rootPath) {
  const normalizedTarget = normalizePathForCompare(resolve(targetPath));
  const normalizedRoot = normalizePathForCompare(resolve(rootPath));
  if (normalizedTarget === normalizedRoot) return true;

  const rootWithSep = normalizedRoot.endsWith(sep)
    ? normalizedRoot
    : `${normalizedRoot}${sep}`;
  return normalizedTarget.startsWith(rootWithSep);
}

function assertAllowedWorkFolder(workFolder) {
  if (ALLOWED_WORKFOLDER_ROOTS.length === 0) return;
  if (ALLOWED_WORKFOLDER_ROOTS.some((root) => isInsideRoot(workFolder, root))) return;

  throw new Error(
    `workFolder is outside allowed roots. Allowed roots: ${ALLOWED_WORKFOLDER_ROOTS.join(", ")}`,
  );
}

function normalizeWorkFolder(workFolderInput) {
  const raw =
    typeof workFolderInput === "string" && workFolderInput.trim() !== ""
      ? workFolderInput.trim()
      : HOME;

  if (!isAbsolute(raw)) {
    throw new Error("workFolder must be an absolute path.");
  }

  const normalized = resolve(raw);
  let stat;
  try {
    stat = statSync(normalized);
  } catch {
    throw new Error(`workFolder does not exist: ${normalized}`);
  }

  if (!stat.isDirectory()) {
    throw new Error(`workFolder is not a directory: ${normalized}`);
  }

  assertAllowedWorkFolder(normalized);
  return normalized;
}

function statePath(mode) {
  return join(STATE_DIR, `${normalizeMode(mode)}.json`);
}

function memoryPath(workFolder) {
  return join(workFolder, ".omx", "memory.json");
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

// ==========================================================================
// Notepad helpers
// ==========================================================================
function readNotepad() {
  const raw = readJSON(NOTEPAD_PATH, {});
  return {
    priority: typeof raw.priority === "string" ? raw.priority : "",
    working: Array.isArray(raw.working) ? raw.working : [],
    manual: Array.isArray(raw.manual) ? raw.manual : [],
  };
}

function writeNotepad(np) {
  writeJSON(NOTEPAD_PATH, np);
}

// ==========================================================================
// MCP Server
// ==========================================================================
const server = new Server(
  { name: "omx", version: "1.1.0" },
  { capabilities: { tools: {} } },
);

// ==========================================================================
// Tool Catalogue
// ==========================================================================
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    // ------------------------------------------------------------------
    // CLAUDE CODE (async delegation)
    // ------------------------------------------------------------------
    {
      name: "claude_code",
      description:
        "Start a Claude Code task asynchronously. Returns a job ID immediately with no MCP timeout risk. " +
        "Use claude_code_status to wait for results. Use claude_code_cancel to abort.",
      inputSchema: {
        type: "object",
        properties: {
          prompt: {
            type: "string",
            description:
              "Task instructions for Claude Code. Keep prompts self-contained and include work folder context.",
          },
          workFolder: {
            type: "string",
            description: "Absolute path to working directory. Defaults to user home.",
          },
        },
        required: ["prompt"],
      },
    },
    {
      name: "claude_code_status",
      description:
        "Wait for a Claude Code job to finish (long polling). Returns partial output while running and full output when complete.",
      inputSchema: {
        type: "object",
        properties: {
          jobId: { type: "string", description: "Job ID from claude_code." },
          waitSeconds: {
            type: "number",
            description: `Max seconds to wait (default ${MAX_WAIT_SECONDS}, max ${MAX_WAIT_SECONDS}). 0 for instant check.`,
          },
        },
        required: ["jobId"],
      },
    },
    {
      name: "claude_code_cancel",
      description: "Cancel a running Claude Code job.",
      inputSchema: {
        type: "object",
        properties: {
          jobId: { type: "string", description: "Job ID to cancel." },
        },
        required: ["jobId"],
      },
    },
    {
      name: "claude_code_list",
      description: "List all Claude Code jobs with status. Newest first.",
      inputSchema: {
        type: "object",
        properties: {
          status: {
            type: "string",
            enum: ["all", "running", "completed", "failed", "cancelled"],
            description: "Filter by status. Default: all.",
          },
        },
      },
    },

    // ------------------------------------------------------------------
    // STATE MANAGEMENT
    // ------------------------------------------------------------------
    {
      name: "omx_state_read",
      description:
        "Read the state for a workflow mode (autopilot, plan, research, tdd, etc.). Returns JSON state or exists:false.",
      inputSchema: {
        type: "object",
        properties: {
          mode: {
            type: "string",
            description:
              "Mode name: letters/numbers with optional _ or -. Max length 64.",
          },
        },
        required: ["mode"],
      },
    },
    {
      name: "omx_state_write",
      description:
        "Write or update state for a workflow mode. Merges with existing state by default.",
      inputSchema: {
        type: "object",
        properties: {
          mode: { type: "string", description: "Mode name." },
          data: {
            type: "object",
            description: "State data to write or merge.",
            additionalProperties: true,
          },
          replace: {
            type: "boolean",
            description: "If true, replaces state entirely instead of merging. Default: false.",
          },
        },
        required: ["mode", "data"],
      },
    },
    {
      name: "omx_state_clear",
      description: "Clear or delete state for a workflow mode.",
      inputSchema: {
        type: "object",
        properties: {
          mode: { type: "string", description: "Mode name to clear." },
        },
        required: ["mode"],
      },
    },
    {
      name: "omx_state_list",
      description: "List all active workflow modes with state summaries.",
      inputSchema: { type: "object", properties: {} },
    },

    // ------------------------------------------------------------------
    // NOTEPAD
    // ------------------------------------------------------------------
    {
      name: "omx_note_read",
      description:
        "Read the session notepad. Sections: priority, working, manual, or all.",
      inputSchema: {
        type: "object",
        properties: {
          section: {
            type: "string",
            enum: ["all", "priority", "working", "manual"],
            description: "Section to read. Default: all.",
          },
        },
      },
    },
    {
      name: "omx_note_write",
      description:
        `Write session notes. content max length is ${MAX_NOTE_CHARS} characters.`,
      inputSchema: {
        type: "object",
        properties: {
          section: {
            type: "string",
            enum: ["priority", "working", "manual"],
            description: "Section to write to.",
          },
          content: { type: "string", description: "Content to write." },
        },
        required: ["section", "content"],
      },
    },

    // ------------------------------------------------------------------
    // PROJECT MEMORY
    // ------------------------------------------------------------------
    {
      name: "omx_memory_read",
      description:
        "Read project memory for a given work folder. Stores tech stack, conventions, build commands, and notes.",
      inputSchema: {
        type: "object",
        properties: {
          workFolder: {
            type: "string",
            description: "Absolute project root directory.",
          },
        },
        required: ["workFolder"],
      },
    },
    {
      name: "omx_memory_write",
      description:
        "Write or update project memory for a given work folder. Merges with existing memory by default.",
      inputSchema: {
        type: "object",
        properties: {
          workFolder: {
            type: "string",
            description: "Absolute project root directory.",
          },
          data: {
            type: "object",
            description:
              "Memory data to merge. Common keys: techStack, buildCommand, testCommand, conventions, structure, notes.",
            additionalProperties: true,
          },
          replace: {
            type: "boolean",
            description: "If true, replaces memory entirely instead of merging. Default: false.",
          },
        },
        required: ["workFolder", "data"],
      },
    },
  ],
}));

// ==========================================================================
// Tool Dispatch
// ==========================================================================
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      // ================================================================
      // CLAUDE CODE - async delegation
      // ================================================================
      case "claude_code": {
        const prompt = args?.prompt;
        if (typeof prompt !== "string" || prompt.trim() === "") {
          return reply("Error: prompt is required.", true);
        }
        if (prompt.length > MAX_PROMPT_CHARS) {
          return reply(
            `Error: prompt too large (${prompt.length} chars). Limit is ${MAX_PROMPT_CHARS}.`,
            true,
          );
        }

        if (countRunningJobs() >= MAX_RUNNING_JOBS) {
          return reply(
            `Error: max running jobs reached (${MAX_RUNNING_JOBS}). Wait for a job to finish or cancel one.`,
            true,
          );
        }

        const workFolder = normalizeWorkFolder(args?.workFolder);
        const jobId = uniqueJobId();

        const cliArgs = [];
        if (SHOULD_SKIP_CLAUDE_PERMISSIONS) {
          cliArgs.push("--dangerously-skip-permissions");
        }
        cliArgs.push("-p", prompt, "--output-format", "text");

        const job = {
          id: jobId,
          status: "running",
          stdout: "",
          stderr: "",
          stdoutTruncated: false,
          stderrTruncated: false,
          startTime: Date.now(),
          endTime: null,
          exitCode: null,
          promptPreview: prompt.slice(0, 200),
          workFolder,
          permissionMode: CLAUDE_PERMISSION_MODE,
          _proc: null,
          _timeout: null,
        };

        jobs.set(jobId, job);
        log(`Starting job ${jobId} in ${workFolder}`);

        try {
          const proc = spawn(CLAUDE_CLI, cliArgs, {
            cwd: workFolder,
            stdio: ["ignore", "pipe", "pipe"],
            env: { ...process.env, FORCE_COLOR: "0", NO_COLOR: "1" },
          });

          job._proc = proc;
          armJobTimeout(job);

          proc.stdout.on("data", (chunk) => {
            const next = appendBounded(job.stdout, chunk, MAX_OUTPUT_CHARS);
            job.stdout = next.value;
            job.stdoutTruncated = job.stdoutTruncated || next.truncated;
          });

          proc.stderr.on("data", (chunk) => {
            const next = appendBounded(job.stderr, chunk, MAX_OUTPUT_CHARS);
            job.stderr = next.value;
            job.stderrTruncated = job.stderrTruncated || next.truncated;
          });

          proc.on("close", (code) => {
            clearJobTimer(job);

            if (job.status === "running") {
              job.status = code === 0 ? "completed" : "failed";
            }
            if (job.exitCode === null) {
              job.exitCode = code;
            }
            if (job.endTime === null) {
              job.endTime = Date.now();
            }

            job._proc = null;
            log(`Job ${jobId} done: code=${code}`);
            pruneJobs();
          });

          proc.on("error", (err) => {
            clearJobTimer(job);
            job.status = "failed";
            const next = appendBounded(
              job.stderr,
              `\nSpawn error: ${err.message}`,
              MAX_OUTPUT_CHARS,
            );
            job.stderr = next.value;
            job.stderrTruncated = job.stderrTruncated || next.truncated;
            job.endTime = Date.now();
            job._proc = null;
          });
        } catch (err) {
          clearJobTimer(job);
          job.status = "failed";
          const next = appendBounded(
            job.stderr,
            `Failed to spawn Claude CLI: ${err.message}`,
            MAX_OUTPUT_CHARS,
          );
          job.stderr = next.value;
          job.stderrTruncated = job.stderrTruncated || next.truncated;
          job.endTime = Date.now();
        }

        return reply({
          jobId,
          status: job.status,
          permissionMode: CLAUDE_PERMISSION_MODE,
          message: `Job started. Call claude_code_status(jobId: "${jobId}") to wait for results.`,
        });
      }

      case "claude_code_status": {
        const jobId = args?.jobId;
        if (!jobId) return reply("Error: jobId is required.", true);

        const job = jobs.get(jobId);
        if (!job) {
          return reply(
            `Error: No job "${jobId}". Use claude_code_list to see all jobs.`,
            true,
          );
        }

        const waitSeconds = Math.min(
          Math.max(0, Number(args?.waitSeconds ?? MAX_WAIT_SECONDS)),
          MAX_WAIT_SECONDS,
        );

        if (job.status === "running" && waitSeconds > 0) {
          const deadline = Date.now() + waitSeconds * 1000;
          await new Promise((resolvePromise) => {
            const interval = setInterval(() => {
              if (job.status !== "running" || Date.now() >= deadline) {
                clearInterval(interval);
                resolvePromise();
              }
            }, 500);
          });
        }

        const elapsed = ((job.endTime || Date.now()) - job.startTime) / 1000;
        const result = {
          jobId: job.id,
          status: job.status,
          elapsedSeconds: Math.round(elapsed),
          workFolder: job.workFolder,
          permissionMode: job.permissionMode,
        };

        if (job.exitCode !== null) result.exitCode = job.exitCode;
        if (job.stdoutTruncated || job.stderrTruncated) {
          result.outputNotice = `Output is truncated to the last ${MAX_OUTPUT_CHARS} characters.`;
        }

        if (job.status === "running") {
          const tail = job.stdout.slice(-3000);
          result.outputTail =
            tail.length < job.stdout.length
              ? `...(${job.stdout.length} chars)...\n${tail}`
              : tail || "(no output yet)";
          result.hint = "Still running. Call claude_code_status again.";
        } else {
          result.output = job.stdout || "(no output)";
        }

        if (job.stderr && job.status !== "completed") {
          result.error = job.stderr.slice(-2000);
        }

        return reply(result);
      }

      case "claude_code_cancel": {
        const jobId = args?.jobId;
        if (!jobId) return reply("Error: jobId is required.", true);

        const job = jobs.get(jobId);
        if (!job) return reply(`Error: No job "${jobId}".`, true);
        if (job.status !== "running") return reply(`Job ${jobId} already ${job.status}.`);

        clearJobTimer(job);

        if (job._proc) {
          try {
            job._proc.kill("SIGTERM");
          } catch {}

          setTimeout(() => {
            if (!job._proc) return;
            try {
              job._proc.kill("SIGKILL");
            } catch {}
          }, 5000);
        }

        job.status = "cancelled";
        job.endTime = Date.now();
        job._proc = null;

        return reply(`Job ${jobId} cancelled.`);
      }

      case "claude_code_list": {
        const filter = args?.status || "all";
        const entries = [...jobs.values()]
          .filter((j) => filter === "all" || j.status === filter)
          .map((j) => ({
            jobId: j.id,
            status: j.status,
            elapsedSeconds: Math.round(((j.endTime || Date.now()) - j.startTime) / 1000),
            promptPreview: j.promptPreview,
            workFolder: j.workFolder,
          }))
          .reverse();

        return reply(entries.length > 0 ? entries : "No jobs found.");
      }

      // ================================================================
      // STATE MANAGEMENT
      // ================================================================
      case "omx_state_read": {
        const mode = normalizeMode(args?.mode);
        const data = readJSON(statePath(mode), null);
        return reply(data !== null ? data : { exists: false, mode });
      }

      case "omx_state_write": {
        const mode = normalizeMode(args?.mode);
        const data = args?.data;
        if (!isObject(data)) {
          return reply("Error: data must be a JSON object.", true);
        }

        let state;
        if (args?.replace) {
          state = { ...data, _mode: mode, _updatedAt: new Date().toISOString() };
        } else {
          const existing = readJSON(statePath(mode), {});
          state = {
            ...existing,
            ...data,
            _mode: mode,
            _updatedAt: new Date().toISOString(),
          };
        }

        writeJSON(statePath(mode), state);
        return reply({ ok: true, mode, state });
      }

      case "omx_state_clear": {
        const mode = normalizeMode(args?.mode);
        const path = statePath(mode);
        if (existsSync(path)) unlinkSync(path);
        return reply({ ok: true, mode, cleared: true });
      }

      case "omx_state_list": {
        const files = existsSync(STATE_DIR)
          ? readdirSync(STATE_DIR).filter((f) => f.endsWith(".json"))
          : [];

        const modes = files.map((f) => {
          const mode = f.replace(".json", "");
          const data = readJSON(join(STATE_DIR, f), {});
          return {
            mode,
            active: data.active !== false,
            phase: data.phase || data.current_phase || null,
            updatedAt: data._updatedAt || null,
          };
        });

        return reply(modes.length > 0 ? modes : "No active modes.");
      }

      // ================================================================
      // NOTEPAD
      // ================================================================
      case "omx_note_read": {
        const np = readNotepad();
        const section = args?.section || "all";

        if (section === "all") return reply(np);
        if (section === "priority") return reply({ priority: np.priority });
        if (section === "working") return reply({ working: np.working });
        if (section === "manual") return reply({ manual: np.manual });

        return reply("Error: invalid section.", true);
      }

      case "omx_note_write": {
        const section = args?.section;
        const content = args?.content;

        if (
          typeof section !== "string" ||
          typeof content !== "string" ||
          !["priority", "working", "manual"].includes(section)
        ) {
          return reply("Error: section must be priority|working|manual and content must be a string.", true);
        }

        if (content.length > MAX_NOTE_CHARS) {
          return reply(
            `Error: content too large (${content.length} chars). Limit is ${MAX_NOTE_CHARS}.`,
            true,
          );
        }

        const np = readNotepad();

        if (section === "priority") {
          np.priority = content;
        } else if (section === "working") {
          np.working.push({ content, timestamp: new Date().toISOString() });
          const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
          np.working = np.working.filter(
            (entry) =>
              isObject(entry) &&
              typeof entry.timestamp === "string" &&
              new Date(entry.timestamp).getTime() > cutoff,
          );
        } else {
          np.manual.push({ content, timestamp: new Date().toISOString() });
        }

        writeNotepad(np);
        return reply({ ok: true, section });
      }

      // ================================================================
      // PROJECT MEMORY
      // ================================================================
      case "omx_memory_read": {
        const workFolder = normalizeWorkFolder(args?.workFolder);
        const data = readJSON(memoryPath(workFolder), null);
        return reply(data !== null ? data : { exists: false, workFolder });
      }

      case "omx_memory_write": {
        const workFolder = normalizeWorkFolder(args?.workFolder);
        const data = args?.data;
        if (!isObject(data)) {
          return reply("Error: data must be a JSON object.", true);
        }

        const mp = memoryPath(workFolder);
        let memory;

        if (args?.replace) {
          memory = { ...data, _updatedAt: new Date().toISOString() };
        } else {
          const existing = readJSON(mp, {});
          memory = {
            ...existing,
            ...data,
            _updatedAt: new Date().toISOString(),
          };
          if (Array.isArray(existing.notes) && Array.isArray(data.notes)) {
            memory.notes = [...existing.notes, ...data.notes];
          }
        }

        writeJSON(mp, memory);
        return reply({ ok: true, workFolder });
      }

      // ================================================================
      default:
        return reply(`Unknown tool: ${name}`, true);
    }
  } catch (err) {
    log(`Tool ${name} failed`, err);
    return reply(`Error: ${err?.message || String(err)}`, true);
  }
});

// ==========================================================================
// Helpers
// ==========================================================================
function reply(data, isError = false) {
  const text = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  return {
    content: [{ type: "text", text }],
    ...(isError && { isError: true }),
  };
}

// ==========================================================================
// Start
// ==========================================================================
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  log(
    `omx MCP server running (maxRunningJobs=${MAX_RUNNING_JOBS}, permissionMode=${CLAUDE_PERMISSION_MODE})`,
  );
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
