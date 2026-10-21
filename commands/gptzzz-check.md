---
name: gptzzz-check
description: Check that GPTZZZ_API_KEY works against the GPTZZZ OpenAI-compatible endpoint and list the model IDs it can use. Billed requests only after the user agrees.
---

# Check the GPTZZZ connection

Use `BASE=${GPTZZZ_BASE_URL:-https://gptzzz.ai/v1}`. Never ask the user to paste the key into chat, and never print it.

1. Key present? Run `echo ${#GPTZZZ_API_KEY}`. If it prints `0`, stop: ask the user to run `read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY` in the shell that starts Cursor, then restart Cursor from that shell.
2. List models (normally free). In bash or zsh, pass the key through a pipe so it stays out of the process list:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' "$BASE/models" \
     -H @<(printf 'Authorization: Bearer %s\n' "$GPTZZZ_API_KEY")
   ```

   Report the HTTP status and the sorted `data[].id` values.
3. Ask before step 4: it is one small billed request.
4. Send one chat request with a model ID from step 2:

   ```bash
   curl -sS -w '\nHTTP %{http_code}\n' "$BASE/chat/completions" \
     -H @<(printf 'Authorization: Bearer %s\n' "$GPTZZZ_API_KEY") \
     -H 'Content-Type: application/json' \
     -d '{"model":"MODEL_ID","messages":[{"role":"user","content":"Reply with the single word: ready"}]}'
   ```

   Report the status, `choices[0].finish_reason` and `usage.total_tokens`.
5. If a step fails, follow the `gptzzz-error-triage` skill. Do not change more than one setting at a time.
