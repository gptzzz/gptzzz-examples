// Tests for examples/node_chat.mjs against a local HTTP stub (127.0.0.1 only).
// No real key, no network, nothing billed.   node --test tests/
import { test } from "node:test";
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const SCRIPT = fileURLToPath(new URL("../examples/node_chat.mjs", import.meta.url));
const KEY = "sk-node-test-key-not-real-0000";

// Start a stub that answers every request with `handler(req, body, res)`.
async function withStub(handler, fn) {
  const seen = [];
  const server = createServer((req, res) => {
    let body = "";
    req.on("data", (c) => (body += c));
    req.on("end", () => {
      seen.push({ method: req.method, url: req.url, headers: req.headers, body: body ? JSON.parse(body) : null });
      handler(req, body ? JSON.parse(body) : null, res);
    });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  try {
    return await fn(`http://127.0.0.1:${server.address().port}/v1`, seen);
  } finally {
    await new Promise((r) => server.close(r));
  }
}

function run(args, env) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [SCRIPT, ...args], {
      env: { PATH: process.env.PATH, NO_PROXY: "127.0.0.1", ...env },
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    child.on("close", (code) => resolve({ code, stdout, stderr }));
  });
}

const json = (res, status, obj) => {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(obj));
};

test("plain request: path, auth header, body, usage line", async () => {
  await withStub(
    (req, body, res) =>
      json(res, 200, {
        choices: [{ message: { content: "你好" }, finish_reason: "stop" }],
        usage: { prompt_tokens: 3, completion_tokens: 1, total_tokens: 4 },
      }),
    async (base, seen) => {
      const r = await run(["Hello"], { GPTZZZ_BASE_URL: base + "/", GPTZZZ_API_KEY: KEY, GPTZZZ_MODEL: "m1" });
      assert.equal(r.code, 0, r.stderr);
      assert.equal(r.stdout.trim(), "你好");
      assert.match(r.stderr, /\[usage\] prompt=3 completion=1 total=4/);
      assert.equal(seen[0].method, "POST");
      assert.equal(seen[0].url, "/v1/chat/completions"); // trailing slash in the base URL is removed
      assert.equal(seen[0].headers.authorization, `Bearer ${KEY}`);
      assert.equal(seen[0].body.model, "m1");
      assert.equal(seen[0].body.stream, undefined);
      assert.ok(!r.stdout.includes(KEY) && !r.stderr.includes(KEY));
    },
  );
});

test("stream: prints deltas, reads the usage chunk, sees [DONE]", async () => {
  await withStub(
    (req, body, res) => {
      res.writeHead(200, { "Content-Type": "text/event-stream" });
      const send = (d) => res.write(`data: ${typeof d === "string" ? d : JSON.stringify(d)}\r\n\r\n`);
      res.write(": keep-alive comment\n\n");
      send({ choices: [{ delta: { role: "assistant", content: "" } }] });
      send({ choices: [{ delta: { content: "1 2 " } }] });
      send({ choices: [{ delta: { content: "3" }, finish_reason: "stop" }] });
      send({ choices: [], usage: { prompt_tokens: 5, completion_tokens: 3, total_tokens: 8 } });
      send("[DONE]");
      res.end();
    },
    async (base, seen) => {
      const r = await run(["--stream", "Count"], { GPTZZZ_BASE_URL: base, GPTZZZ_API_KEY: KEY });
      assert.equal(r.code, 0, r.stderr);
      assert.equal(r.stdout.trim(), "1 2 3");
      assert.match(r.stderr, /total=8/);
      assert.doesNotMatch(r.stderr, /without data: \[DONE\]/);
      assert.equal(seen[0].body.stream, true);
      assert.deepEqual(seen[0].body.stream_options, { include_usage: true });
    },
  );
});

test("stream cut before [DONE] is reported", async () => {
  await withStub(
    (req, body, res) => {
      res.writeHead(200, { "Content-Type": "text/event-stream" });
      res.end(`data: ${JSON.stringify({ choices: [{ delta: { content: "partial" } }] })}\n\n`);
    },
    async (base) => {
      const r = await run(["--stream", "x"], { GPTZZZ_BASE_URL: base, GPTZZZ_API_KEY: KEY });
      assert.equal(r.stdout.trim(), "partial");
      assert.match(r.stderr, /stream ended without data: \[DONE\]/);
    },
  );
});

test("401 with the gateway's {code, message} body", async () => {
  await withStub(
    (req, body, res) => json(res, 401, { code: "INVALID_API_KEY", message: "Invalid API key" }),
    async (base) => {
      const r = await run(["x"], { GPTZZZ_BASE_URL: base, GPTZZZ_API_KEY: KEY });
      assert.equal(r.code, 1);
      assert.match(r.stderr, /HTTP 401: INVALID_API_KEY: Invalid API key/);
      assert.ok(!r.stderr.includes(KEY));
    },
  );
});

test("404 with OpenAI's nested error body", async () => {
  await withStub(
    (req, body, res) => json(res, 404, { error: { message: "The model `x` does not exist", type: "invalid_request_error" } }),
    async (base) => {
      const r = await run(["x"], { GPTZZZ_BASE_URL: base, GPTZZZ_API_KEY: KEY, GPTZZZ_MODEL: "x" });
      assert.equal(r.code, 1);
      assert.match(r.stderr, /HTTP 404: The model `x` does not exist/);
    },
  );
});

test("missing key: exit 2 before any request", async () => {
  await withStub(
    (req, body, res) => json(res, 200, {}),
    async (base, seen) => {
      const r = await run(["x"], { GPTZZZ_BASE_URL: base });
      assert.equal(r.code, 2);
      assert.match(r.stderr, /Set GPTZZZ_API_KEY first/);
      assert.equal(seen.length, 0);
    },
  );
});
