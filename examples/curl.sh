#!/usr/bin/env bash
# curl examples for GPTZZZ, an OpenAI-compatible API gateway.
#
# Every command except `models` sends a real, billed request.
#
#   read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY   # paste the key, nothing is echoed
#   bash examples/curl.sh              # models + chat
#   bash examples/curl.sh stream       # one example
#   bash examples/curl.sh all          # everything below
#
# Optional overrides:
#   GPTZZZ_BASE_URL  default https://gptzzz.ai/v1  (no trailing /chat/completions)
#   GPTZZZ_MODEL     default gpt-5.6               (pick one from `models`)
#
# jq is only used to pretty-print; the curl commands work without it.

set -euo pipefail

: "${GPTZZZ_API_KEY:?Set GPTZZZ_API_KEY first, e.g. read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY}"
BASE_URL="${GPTZZZ_BASE_URL:-https://gptzzz.ai/v1}"
BASE_URL="${BASE_URL%/}"
MODEL="${GPTZZZ_MODEL:-gpt-5.6}"

# Pretty-print a response with jq. Error bodies (OpenAI's {"error":{...}} or
# GPTZZZ's {"code":...,"message":...}) go to stderr as-is instead of through
# the filter, so a wrong key or model shows the real message.
pretty() {
  local body
  body="$(cat)"
  if ! command -v jq >/dev/null 2>&1; then
    printf '%s\n' "$body"
    return 0
  fi
  if printf '%s' "$body" | jq -e 'type == "object" and (has("error") or (has("code") and has("message")))' >/dev/null 2>&1; then
    printf 'API error: %s\n' "$body" >&2
    return 1
  fi
  printf '%s\n' "$body" | jq "${@:-.}"
}

# 1. List the model IDs your key can use. Model IDs differ between key groups.
models() {
  curl -sS "$BASE_URL/models" \
    -H "Authorization: Bearer $GPTZZZ_API_KEY" | pretty -r '.data[].id'
}

# 2. Chat completion (non-streaming). Look at .usage for token counts.
chat() {
  curl -sS "$BASE_URL/chat/completions" \
    -H "Authorization: Bearer $GPTZZZ_API_KEY" \
    -H "Content-Type: application/json" \
    -d @- <<JSON | pretty '{model, content: .choices[0].message.content, finish_reason: .choices[0].finish_reason, usage}'
{
  "model": "$MODEL",
  "messages": [
    {"role": "system", "content": "You are a concise assistant."},
    {"role": "user", "content": "Explain HTTP 429 in one sentence."}
  ]
}
JSON
}

# 3. Streaming (SSE). With include_usage, the last chunk before [DONE] carries usage.
stream() {
  curl -sSN "$BASE_URL/chat/completions" \
    -H "Authorization: Bearer $GPTZZZ_API_KEY" \
    -H "Content-Type: application/json" \
    -d @- <<JSON
{
  "model": "$MODEL",
  "stream": true,
  "stream_options": {"include_usage": true},
  "messages": [{"role": "user", "content": "Count from 1 to 5."}]
}
JSON
}

# 4. Tool (function) calling. Expect finish_reason "tool_calls" and JSON arguments.
tools() {
  curl -sS "$BASE_URL/chat/completions" \
    -H "Authorization: Bearer $GPTZZZ_API_KEY" \
    -H "Content-Type: application/json" \
    -d @- <<JSON | pretty '{finish_reason: .choices[0].finish_reason, tool_calls: .choices[0].message.tool_calls}'
{
  "model": "$MODEL",
  "messages": [{"role": "user", "content": "What is the weather in Paris? Use the tool."}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Get the current weather for a city",
      "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
      }
    }
  }]
}
JSON
}

# 5. JSON mode. The prompt must mention JSON.
json_mode() {
  curl -sS "$BASE_URL/chat/completions" \
    -H "Authorization: Bearer $GPTZZZ_API_KEY" \
    -H "Content-Type: application/json" \
    -d @- <<JSON | pretty -r '.choices[0].message.content'
{
  "model": "$MODEL",
  "response_format": {"type": "json_object"},
  "messages": [{"role": "user", "content": "Return a JSON object with keys ok (boolean) and lang (string, value \"en\")."}]
}
JSON
}

# 6. Responses API (this is the endpoint Codex CLI calls).
responses() {
  curl -sS "$BASE_URL/responses" \
    -H "Authorization: Bearer $GPTZZZ_API_KEY" \
    -H "Content-Type: application/json" \
    -d @- <<JSON | pretty '{status, output_text: ([.output[]? | select(.type == "message") | .content[]? | select(.type == "output_text") | .text] | join("")), usage}'
{
  "model": "$MODEL",
  "input": "Reply with the single word: pong"
}
JSON
}

# 7. Image input as a base64 data URL (a 16x16 solid-colour PNG).
#    A remote https image URL also works when the image host lets the gateway fetch it.
image() {
  local png="iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAFklEQVR42mO4I2JDEmIY1TCqYfhqAAAeBCwQ81sZJgAAAABJRU5ErkJggg=="
  curl -sS "$BASE_URL/chat/completions" \
    -H "Authorization: Bearer $GPTZZZ_API_KEY" \
    -H "Content-Type: application/json" \
    -d @- <<JSON | pretty -r '.choices[0].message.content'
{
  "model": "$MODEL",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "What colour is this image? One word."},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,$png"}}
    ]
  }]
}
JSON
}

run() { printf '\n== %s ==\n' "$1"; "$1"; }

case "${1:-default}" in
  default)   run models; run chat ;;
  all)       for f in models chat stream tools json_mode responses image; do run "$f"; done ;;
  models|chat|stream|tools|json_mode|responses|image) run "$1" ;;
  json)      run json_mode ;;
  *) echo "usage: $0 [models|chat|stream|tools|json|responses|image|all]" >&2; exit 2 ;;
esac
