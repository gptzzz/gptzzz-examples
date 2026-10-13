---
name: gptzzz-error-triage
description: Diagnose a failing request to GPTZZZ or another OpenAI-compatible gateway from its HTTP status and response body (no status, 400, 401, 403, 404, 429, 5xx, streams that stop early). Use when an SDK, curl, Codex CLI, OpenCode or Cline reports an error against a custom base URL.
---

# Triage an OpenAI-compatible gateway error

Work from evidence: the exact request URL (without the key), the HTTP status and
the response body. Change one setting at a time. The defaults are GPTZZZ's
(`https://gptzzz.ai/v1`, key in `GPTZZZ_API_KEY`); the steps apply to any
OpenAI-compatible endpoint.

## Rules

- Never ask for the key in chat and never print it. `echo ${#GPTZZZ_API_KEY}`
  prints its length, which is enough to spot an empty or truncated key.
- Strip keys and `Authorization` headers from anything you quote back.
- Before retrying, remember that a request that timed out or got a 5xx may
  already have been processed and billed.

## 1. Did you get an HTTP status at all?

| Symptom | Check |
|---|---|
| `Could not resolve host` | DNS, or a company proxy blocking the domain |
| `SSL certificate problem` / `CERTIFICATE_VERIFY_FAILED` | System clock; a proxy that replaces certificates |
| `Connection refused` / `reset` | `HTTPS_PROXY` settings, local firewall |
| Timeout | Before sending: network. After sending: check usage in the console before resending |

If this repository is checked out, `bash examples/selftest.sh` runs six checks
and its exit code is the number of failures; which check fails tells you the layer.

## 2. Read the status and body

| Status | Likely cause | Fix |
|---|---|---|
| 400 `Unsupported value ... reasoning_effort` | The model rejects that effort level | Use a value the message lists. On 2026-09-29 `gpt-6-astra` accepted `low` to `max`; `gpt-5.6`, `gpt-5.6-sol`, `gpt-5.6-terra` accepted `none` to `max`; none accepted `minimal` |
| 400 mentioning `messages` / `input` | Chat Completions takes `messages`, Responses takes `input` | Match the body to the endpoint |
| 400 `Error while downloading file` | The gateway could not fetch a remote image URL | Send the image as a base64 data URL |
| 400 JSON parse error | Shell quoting broke the body | Build the body with a heredoc or `jq -n` |
| 401 `{"code":"INVALID_API_KEY",...}` | Wrong, revoked or truncated key; the variable is not visible to the process | Compare key length; restart the IDE from the shell that exported the key |
| 403 `error code: 1010`, HTML or plain text | The CDN rejected the client before the gateway saw it (seen with Python `urllib`'s default `User-Agent`) | Send an explicit `User-Agent`; the key is not the cause |
| 404 on `/v1/v1/...` | Base URL already ends in `/v1` and the client added another | Base URL is `https://gptzzz.ai/v1`, nothing after it |
| 404 mentioning the model | The model ID is not served to this key's group | Copy an ID from `GET /v1/models` |
| 404 / 503 on `/v1/embeddings` | Embeddings are not offered | Use a separate embeddings provider |
| 429 | Rate limit, or quota/balance exhausted | Rate limit: honour `Retry-After`, back off with jitter, cap attempts. Balance: waiting will not help; check the console |
| 500 / 502 / 503 | Gateway or upstream error | Note the UTC time and any request ID; retry a limited number of times |

GPTZZZ returns the flat `{"code": ..., "message": ...}` shape for some errors,
while OpenAI uses `{"error": {"message": ...}}`. A client that only reads the
OpenAI shape may show a generic "request failed"; read the raw body.

## 3. Streaming problems

| Symptom | Cause | Fix |
|---|---|---|
| Output arrives all at once | A reverse proxy buffers SSE | `proxy_buffering off;` in your own Nginx |
| Stream stops before `data: [DONE]` | Network cut or proxy idle timeout | Raise the client idle timeout for long reasoning runs |
| No usage block | `stream_options.include_usage` not set, or the stream was cut | Set it and re-check the last lines |

## 4. Client-specific checks

- Codex CLI: the provider must be in the user-level `~/.codex/config.toml`;
  provider IDs `openai`, `ollama` and `lmstudio` are reserved; `wire_api = "responses"`.
- OpenCode: the key is `"{env:GPTZZZ_API_KEY}"`; model IDs go in the provider's `models` map.
- Programs started from a desktop shortcut or IDE may not see variables you
  exported in a terminal.

## What to collect for a bug report

Time and time zone, client and version, the request URL without the key, model
ID, HTTP status, the response body with any key removed, and the output of
`selftest.sh` if available.
