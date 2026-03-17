import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import process from "node:process";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const serverPath = join(__dirname, "server.mjs");

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function parseToolText(response) {
  const text = response?.result?.content?.[0]?.text;
  if (typeof text !== "string") return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

class RpcClient {
  constructor(proc) {
    this.proc = proc;
    this.nextId = 1;
    this.pending = new Map();

    const rl = createInterface({ input: proc.stdout });
    rl.on("line", (line) => {
      if (!line.trim()) return;
      let msg;
      try {
        msg = JSON.parse(line);
      } catch {
        return;
      }
      if (msg.id !== undefined && this.pending.has(msg.id)) {
        this.pending.get(msg.id).resolve(msg);
        this.pending.delete(msg.id);
      }
    });

    proc.stderr.on("data", (chunk) => {
      const text = chunk.toString();
      if (text.trim()) {
        process.stderr.write(`[server-stderr] ${text}`);
      }
    });

    proc.on("exit", (code) => {
      for (const { reject } of this.pending.values()) {
        reject(new Error(`Server exited early with code ${code}`));
      }
      this.pending.clear();
    });
  }

  send(method, params = undefined) {
    const id = this.nextId++;
    const payload = { jsonrpc: "2.0", id, method };
    if (params !== undefined) payload.params = params;

    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.proc.stdin.write(`${JSON.stringify(payload)}\n`);
    });
  }

  notify(method, params = undefined) {
    const payload = { jsonrpc: "2.0", method };
    if (params !== undefined) payload.params = params;
    this.proc.stdin.write(`${JSON.stringify(payload)}\n`);
  }
}

async function main() {
  const proc = spawn(process.execPath, [serverPath], {
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, MCP_OMX_DEBUG: "false" },
  });

  const client = new RpcClient(proc);

  try {
    const initialize = await client.send("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "smoke-test", version: "1.0.0" },
    });
    assert(initialize.result?.serverInfo?.name === "omx", "initialize failed");

    client.notify("notifications/initialized");

    const list = await client.send("tools/list", {});
    const tools = list.result?.tools || [];
    assert(Array.isArray(tools) && tools.length >= 12, "tools/list returned too few tools");

    const writeState = await client.send("tools/call", {
      name: "omx_state_write",
      arguments: {
        mode: "smoke_test",
        data: { phase: "testing", active: true },
      },
    });
    const writePayload = parseToolText(writeState);
    assert(writePayload?.ok === true, "omx_state_write failed");

    const readState = await client.send("tools/call", {
      name: "omx_state_read",
      arguments: { mode: "smoke_test" },
    });
    const readPayload = parseToolText(readState);
    assert(readPayload?.phase === "testing", "omx_state_read returned unexpected state");

    const invalidMode = await client.send("tools/call", {
      name: "omx_state_read",
      arguments: { mode: "../escape" },
    });
    assert(invalidMode.result?.isError === true, "invalid mode should fail");

    const relativePath = await client.send("tools/call", {
      name: "omx_memory_read",
      arguments: { workFolder: "relative/path" },
    });
    assert(relativePath.result?.isError === true, "relative workFolder should fail");

    const clearState = await client.send("tools/call", {
      name: "omx_state_clear",
      arguments: { mode: "smoke_test" },
    });
    const clearPayload = parseToolText(clearState);
    assert(clearPayload?.ok === true, "omx_state_clear failed");

    const writeNote = await client.send("tools/call", {
      name: "omx_note_write",
      arguments: {
        section: "working",
        workspace: "smoke-workspace",
        content: "smoke note entry",
      },
    });
    const writeNotePayload = parseToolText(writeNote);
    assert(writeNotePayload?.ok === true, "omx_note_write failed");

    const readNote = await client.send("tools/call", {
      name: "omx_note_read",
      arguments: {
        section: "all",
        workspace: "smoke-workspace",
      },
    });
    const notePayload = parseToolText(readNote);
    assert(notePayload?.version === 2, "omx_note_read should return notepad v2");
    assert(
      Array.isArray(notePayload?.working) &&
        notePayload.working.some((entry) => entry?.content === "smoke note entry"),
      "omx_note_read returned unexpected workspace notes",
    );

    console.log("Smoke test passed.");
  } finally {
    proc.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error(`Smoke test failed: ${err.message}`);
  process.exit(1);
});
