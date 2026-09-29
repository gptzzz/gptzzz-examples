---
name: openai-compatible-gateway
description: Point a coding agent, SDK or CLI at an OpenAI-compatible gateway (GPTZZZ by default) and prove it works. Use when the user asks to configure a custom OpenAI base URL, set up Codex CLI or OpenCode with a third-party provider, or debug 401/404/stream errors against such an endpoint.
---

# Configure and verify an OpenAI-compatible gateway

This skill sets up a client to use an OpenAI-compatible endpoint and then checks
the result with a script instead of guessing. The defaults are GPTZZZ's
(`https://gptzzz.ai/v1`, key in `GPTZZZ_API_KEY`), but every step works for any
endpoint that implements the OpenAI API: change the base URL and variable name.

## Rules

- Never ask the user to paste the API key into the chat, and never write it into
  a file, a command line argument or a commit. It lives in an environment
  variable; the user sets it with `read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY`.
- Never print the key. To check it is set, print its length: `echo ${#GPTZZZ_API_KEY}`.
- Take model IDs from `GET /v1/models`, not from memory or marketing names.
- Say which requests cost money before running them. `GET /v1/models` is
  normally free; chat, streaming, tool, Responses and image requests are billed.

## Steps

1. **Confirm the key is visible to the process that will use it.**
   `echo ${#GPTZZZ_API_KEY}` must print a non-zero length in the same shell
   (or IDE) that starts the client.
2. **List model IDs.** `bash examples/curl.sh models` from this repository, or:
   `curl -sS "$BASE/models" -H "Authorization: Bearer $GPTZZZ_API_KEY" | jq -r '.data[].id'`
3. **Write the client config** with the base URL ending in `/v1`:
   - Codex CLI: user-level `~/.codex/config.toml` only (project-level
     `.codex/config.toml` ignores provider keys). Copy `examples/codex-config.toml`.
     Keep `model` and `model_provider` above the first `[table]`. The provider ID
     must not be `openai`, `ollama` or `lmstudio`. `wire_api = "responses"` is
     the only supported value, so the gateway must serve `POST /v1/responses`.
   - OpenCode: merge `examples/opencode.json` into `~/.config/opencode/opencode.json`
     or the project's `opencode.json`; the key is `"{env:GPTZZZ_API_KEY}"`.
   - Python / Node SDKs: set `base_url` / `baseURL` and read the key from the
     environment; see `examples/python_chat.py` and `examples/node_chat.mjs`.
4. **Verify the endpoint**: `bash examples/selftest.sh` (six checks, five small
   billed requests). Exit code = number of failed checks.
5. **Verify the client** with one short request, for Codex:
   `codex exec "Reply with the single word: ready"`.
6. **If something fails**, match the symptom in `docs/troubleshooting.md`
   before changing more than one setting at a time.

## Known gateway specifics (GPTZZZ, checked 2026-09-29)

- A bad key returns `401 {"code":"INVALID_API_KEY","message":...}`, not
  OpenAI's `{"error":{...}}`; read both shapes when reporting errors.
- `/v1/embeddings` is not offered. Knowledge-base or RAG features need a
  separate embeddings provider.
- `gpt-6-astra` rejects `reasoning_effort: "none"`; `gpt-5.6`, `gpt-5.6-sol`
  and `gpt-5.6-terra` accept `none` to `max`. No tested model accepts `minimal`.
