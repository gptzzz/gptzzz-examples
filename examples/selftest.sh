#!/usr/bin/env bash
# selftest.sh: six checks for an OpenAI-compatible endpoint (default: GPTZZZ).
#
#   read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
#   bash examples/selftest.sh
#
#   1  GET  /models                  your model ID is listed
#   2  POST /chat/completions        text + usage fields come back
#   3  POST /chat/completions SSE    final usage chunk, then data: [DONE]
#   4  POST /chat/completions tools  finish_reason tool_calls, arguments are JSON
#   5  POST /responses               status completed + usage (Codex CLI needs this)
#   6  GET  /models with a bad key   401 with a JSON body (shape is reported)
#
# Checks 2-5 send small billed requests. Check 6 uses a fake key, not yours.
#
# Key handling: the key is read from GPTZZZ_API_KEY only. It is never printed,
# and it is handed to curl through a pipe (-H @file) so it does not show up in
# the process list. Anything printed from a response is scrubbed of the key.
#
# Optional: GPTZZZ_BASE_URL (default https://gptzzz.ai/v1), GPTZZZ_MODEL
# (default gpt-5.6), GPTZZZ_TIMEOUT seconds per request (default 90).
# Needs bash, curl 7.55+ and jq. Exit code = number of failed checks.

set -uo pipefail
set +x

if [[ -z "${GPTZZZ_API_KEY:-}" ]]; then
  echo "GPTZZZ_API_KEY is not set. Run: read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY" >&2
  exit 64
fi
for bin in curl jq; do
  command -v "$bin" >/dev/null 2>&1 || { echo "missing dependency: $bin" >&2; exit 64; }
done

BASE_URL="${GPTZZZ_BASE_URL:-https://gptzzz.ai/v1}"
BASE_URL="${BASE_URL%/}"
MODEL="${GPTZZZ_MODEL:-gpt-5.6}"
TIMEOUT="${GPTZZZ_TIMEOUT:-90}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASSED=0
FAILED=0

# Print text with the key removed, truncated to one short line.
safe() {
  local s="$1"
  s="${s//"$GPTZZZ_API_KEY"/[REDACTED]}"
  s="$(printf '%s' "$s" | tr '\n' ' ' | cut -c1-240)"
  printf '%s' "$s"
}

pass() { PASSED=$((PASSED + 1)); printf '[PASS] %s\n' "$1"; }
fail() { FAILED=$((FAILED + 1)); printf '[FAIL] %s\n' "$1"; [[ -n "${2:-}" ]] && printf '       %s\n' "$(safe "$2")"; return 0; }

# api METHOD PATH [JSON_BODY]
# Writes the response body to $TMP/body and prints the HTTP status ("000" = no response).
api() {
  local method="$1" path="$2" body="${3:-}" code
  local opts=(-sS -N -o "$TMP/body" -w '%{http_code}' --max-time "$TIMEOUT" -X "$method")
  if [[ -n "$body" ]]; then
    printf '%s' "$body" > "$TMP/req.json"
    opts+=(-H 'Content-Type: application/json' --data-binary "@$TMP/req.json")
  fi
  code="$(curl "${opts[@]}" \
    -H @<(printf 'Authorization: Bearer %s\n' "$GPTZZZ_API_KEY") \
    "$BASE_URL$path" 2>"$TMP/curl.err")" || true
  printf '%s' "${code:-000}"
}

body() { cat "$TMP/body" 2>/dev/null; }
curl_err() { cat "$TMP/curl.err" 2>/dev/null; }

echo "Endpoint: $BASE_URL"
echo "Model:    $MODEL"
echo

# 1. /models lists the model ID
code="$(api GET /models)"
if [[ "$code" == "200" ]] && jq -e '.data | type == "array"' "$TMP/body" >/dev/null 2>&1; then
  count="$(jq '.data | length' "$TMP/body")"
  if jq -r '.data[].id' "$TMP/body" | grep -Fxq "$MODEL"; then
    pass "1 /models: $count models, $MODEL listed"
  else
    fail "1 /models: $count models, but $MODEL is not one of them (set GPTZZZ_MODEL)" \
      "$(jq -r '[.data[].id] | join(", ")' "$TMP/body")"
  fi
else
  fail "1 /models: HTTP $code" "$(body)$(curl_err)"
fi

# 2. Non-streaming chat with usage
req="$(jq -nc --arg m "$MODEL" '{model: $m, messages: [{role: "user", content: "Reply with the single word: pong"}]}')"
code="$(api POST /chat/completions "$req")"
if [[ "$code" == "200" ]] && jq -e '(.choices[0].message.content | type == "string" and length > 0)
    and (.usage.prompt_tokens | type == "number")
    and (.usage.completion_tokens | type == "number")
    and (.usage.total_tokens | type == "number")' "$TMP/body" >/dev/null 2>&1; then
  pass "2 chat: $(jq -r '"\"\(.choices[0].message.content | .[0:40])\" usage \(.usage.prompt_tokens)+\(.usage.completion_tokens)=\(.usage.total_tokens)"' "$TMP/body")"
else
  fail "2 chat: HTTP $code, missing text or usage fields" "$(body)$(curl_err)"
fi

# 3. Streaming: a usage chunk, then data: [DONE] as the last event
req="$(jq -nc --arg m "$MODEL" '{model: $m, stream: true, stream_options: {include_usage: true},
  messages: [{role: "user", content: "Count from 1 to 5."}]}')"
code="$(api POST /chat/completions "$req")"
last="$(tr -d '\r' < "$TMP/body" | grep '^data:' | tail -n 1)"
usage="$(tr -d '\r' < "$TMP/body" | grep '^data: *{' | sed 's/^data: *//' \
  | jq -c -R 'fromjson? | select(.usage != null) | .usage' 2>/dev/null | tail -n 1)"
if [[ "$code" == "200" && "$last" =~ ^data:\ *\[DONE\]$ && -n "$usage" ]]; then
  pass "3 stream: $(grep -c '^data:' "$TMP/body") data lines, usage chunk $usage, ends with [DONE]"
elif [[ "$code" == "200" ]]; then
  fail "3 stream: last event '${last:-none}', usage chunk '${usage:-none}'"
else
  fail "3 stream: HTTP $code" "$(body)$(curl_err)"
fi

# 4. Tool call
req="$(jq -nc --arg m "$MODEL" '{model: $m,
  messages: [{role: "user", content: "What is the weather in Paris? Use the get_weather tool."}],
  tools: [{type: "function", function: {name: "get_weather", description: "Get the current weather for a city",
    parameters: {type: "object", properties: {city: {type: "string"}}, required: ["city"]}}}]}')"
code="$(api POST /chat/completions "$req")"
if [[ "$code" == "200" ]] && jq -e '.choices[0].finish_reason == "tool_calls"
    and (.choices[0].message.tool_calls[0].function.arguments | fromjson | type == "object")' "$TMP/body" >/dev/null 2>&1; then
  pass "4 tools: $(jq -r '.choices[0].message.tool_calls[0].function | "\(.name)(\(.arguments))"' "$TMP/body")"
else
  fail "4 tools: HTTP $code, no tool_calls with JSON arguments" "$(body)$(curl_err)"
fi

# 5. Responses API
req="$(jq -nc --arg m "$MODEL" '{model: $m, input: "Reply with the single word: pong"}')"
code="$(api POST /responses "$req")"
if [[ "$code" == "200" ]] && jq -e '.status == "completed"
    and (.usage.input_tokens | type == "number") and (.usage.output_tokens | type == "number")' "$TMP/body" >/dev/null 2>&1; then
  pass "5 responses: completed, usage in=$(jq '.usage.input_tokens' "$TMP/body") out=$(jq '.usage.output_tokens' "$TMP/body")"
else
  fail "5 responses: HTTP $code (Codex CLI will not work without /responses)" "$(body)$(curl_err)"
fi

# 6. Bad key: expect 401 with a JSON body. Uses a fake key, never yours.
code="$(curl -sS -o "$TMP/body" -w '%{http_code}' --max-time "$TIMEOUT" \
  -H 'Authorization: Bearer invalid-key-for-selftest' "$BASE_URL/models" 2>"$TMP/curl.err")" || true
code="${code:-000}"
if [[ "$code" == "401" ]] && jq -e 'type == "object"' "$TMP/body" >/dev/null 2>&1; then
  if jq -e '.error | type == "object"' "$TMP/body" >/dev/null 2>&1; then
    shape='OpenAI shape {"error":{...}}'
  elif jq -e 'has("code") and has("message")' "$TMP/body" >/dev/null 2>&1; then
    shape='gateway shape {"code","message"}'
  else
    shape='other JSON shape'
  fi
  pass "6 bad key: 401, $shape: $(safe "$(body)")"
else
  fail "6 bad key: expected 401 with JSON, got HTTP $code" "$(body)$(curl_err)"
fi

echo
echo "$PASSED passed, $FAILED failed ($(date -u +%Y-%m-%dT%H:%MZ))"
exit "$FAILED"
