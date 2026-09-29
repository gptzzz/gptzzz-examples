# Cline -> GPTZZZ (OpenAI Compatible provider)

Cline talks to GPTZZZ through its generic **OpenAI Compatible** provider, which calls `POST /v1/chat/completions` with tool calls and streaming. Both passed our 2026-09-29 test (see the compatibility table in the README).

## Settings

Open the Cline settings panel (the gear icon) and set:

| Field | Value |
|---|---|
| API Provider | **OpenAI Compatible** |
| Base URL | `https://gptzzz.ai/v1` (keep `/v1`, nothing after it) |
| API Key | your GPTZZZ key |
| Model ID | an exact ID from `GET /v1/models`, e.g. `gpt-5.6` |

Then open **Model Configuration**:

| Field | What to put |
|---|---|
| Context Window Size / Max Output Tokens | Take the numbers for your model from the GPTZZZ docs or console. Don't guess: a wrong context size makes Cline truncate too early or overflow. |
| Supports Images | On, if you send screenshots. Base64 images and fetchable remote image URLs both passed our test. |
| Input / Output Price | Leave empty unless you know the per-token rate on your own account. GPTZZZ bills per token; rates are listed in the model plaza on the GPTZZZ site. Wrong numbers here make Cline's cost display confidently wrong. |

Click **Verify** (if your Cline version shows it) or send a short message such as "Reply with the single word: ready".

## The API key

Cline's OpenAI Compatible provider takes the key in the settings field, not from an environment variable. Paste it there, and keep it out of files in your workspace (`.clinerules`, READMEs, scripts). If you also use the scripts in this repo, they read the same key from `GPTZZZ_API_KEY`.

## Check the endpoint first

If Cline misbehaves, rule out the endpoint before changing Cline settings:

```bash
read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
GPTZZZ_MODEL=gpt-5.6 bash examples/selftest.sh
```

Checks 1-4 cover everything Cline's OpenAI Compatible provider uses.

## Symptoms

| Symptom | Usual cause |
|---|---|
| 404 on `.../v1/v1/chat/completions` | Base URL already ends in `/v1` and something added another one, or the full `/chat/completions` path was pasted into Base URL |
| "Invalid API Key", or a vague error on 401 | Wrong or revoked key. GPTZZZ returns `401 {"code":"INVALID_API_KEY","message":...}`, not OpenAI's nested `error` object, so a client that expects the OpenAI shape may show a generic message instead of this one |
| "Model not found" right after setup | The model ID isn't served to your key group; copy one from `/v1/models` |
| Agent stops mid-task after a tool call | Re-run `selftest.sh`; if check 4 passes, try a different model ID before blaming the endpoint |
