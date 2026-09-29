// Chat completion against GPTZZZ with plain fetch. Node.js 18+, no npm install.
//
//   read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
//   node examples/node_chat.mjs "Explain HTTP 429 in one sentence."
//   node examples/node_chat.mjs --stream "Count from 1 to 10."
//
// Prefer the official SDK? `npm i openai`, then:
//   new OpenAI({ baseURL: "https://gptzzz.ai/v1", apiKey: process.env.GPTZZZ_API_KEY })

const BASE_URL = (process.env.GPTZZZ_BASE_URL ?? "https://gptzzz.ai/v1").replace(/\/+$/, "");
const MODEL = process.env.GPTZZZ_MODEL ?? "gpt-5.6";
const apiKey = process.env.GPTZZZ_API_KEY;

if (!apiKey) {
  console.error("Set GPTZZZ_API_KEY first (see README).");
  process.exit(2);
}

const args = process.argv.slice(2);
const stream = args.includes("--stream");
const prompt = args.filter((a) => a !== "--stream").join(" ") || "Reply with the single word: pong";

// Handles both error shapes: OpenAI's {"error": {"message": ...}} and the
// {"code": ..., "message": ...} that GPTZZZ returns for auth errors.
function errorDetail(text) {
  try {
    const data = JSON.parse(text);
    if (data?.error?.message) return data.error.message;
    if (data?.message) return data.code ? `${data.code}: ${data.message}` : data.message;
  } catch {
    // not JSON
  }
  return text.slice(0, 300);
}

const res = await fetch(`${BASE_URL}/chat/completions`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: MODEL,
    messages: [
      { role: "system", content: "You are a concise assistant." },
      { role: "user", content: prompt },
    ],
    ...(stream ? { stream: true, stream_options: { include_usage: true } } : {}),
  }),
  signal: AbortSignal.timeout(120_000),
});

if (!res.ok) {
  console.error(`HTTP ${res.status}: ${errorDetail(await res.text())}`);
  process.exit(1);
}

if (!stream) {
  const data = await res.json();
  console.log(data.choices[0].message.content);
  if (data.usage) {
    const u = data.usage;
    console.error(`[usage] prompt=${u.prompt_tokens} completion=${u.completion_tokens} total=${u.total_tokens}`);
  }
} else {
  // Server-sent events: lines of `data: {json}`, ending with `data: [DONE]`.
  const decoder = new TextDecoder();
  let buffer = "";
  let usage = null;
  let done = false;

  const handleLine = (raw) => {
    const line = raw.trim();
    if (!line.startsWith("data:")) return; // skip blank lines, comments, event: lines
    const payload = line.slice(5).trim();
    if (payload === "[DONE]") {
      done = true;
      return;
    }
    const chunk = JSON.parse(payload);
    const text = chunk.choices?.[0]?.delta?.content;
    if (text) process.stdout.write(text);
    if (chunk.usage) usage = chunk.usage;
  };

  for await (const part of res.body) {
    buffer += decoder.decode(part, { stream: true });
    let nl;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      handleLine(buffer.slice(0, nl));
      buffer = buffer.slice(nl + 1);
    }
  }
  handleLine(buffer + decoder.decode());
  process.stdout.write("\n");
  if (!done) console.error("[warn] stream ended without data: [DONE]");
  if (usage) {
    console.error(`[usage] prompt=${usage.prompt_tokens} completion=${usage.completion_tokens} total=${usage.total_tokens}`);
  }
}
