"""Responses API (POST /v1/responses) against GPTZZZ with the OpenAI Python SDK.

    pip install "openai>=1.40"
    read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
    python examples/python_responses.py "Explain HTTP 429 in one sentence."
    python examples/python_responses.py --stream "Count from 1 to 5."
    GPTZZZ_REASONING_EFFORT=low python examples/python_responses.py "Why is the sky blue?"

This is the endpoint Codex CLI uses. If this script works with your key and
model, the Codex config in examples/codex-config.toml should work too.

Differences from Chat Completions that trip people up:
  - the prompt goes in `input` (a string or a list of items), not `messages`;
  - reasoning effort is `reasoning={"effort": ...}`, not `reasoning_effort`;
  - usage is `input_tokens` / `output_tokens`, not `prompt_tokens` / `completion_tokens`;
  - a stream ends with a `response.completed` event, not `data: [DONE]`.
"""

import os
import sys

import openai
from openai import OpenAI

BASE_URL = os.environ.get("GPTZZZ_BASE_URL", "https://gptzzz.ai/v1")
MODEL = os.environ.get("GPTZZZ_MODEL", "gpt-5.6")
EFFORT = os.environ.get("GPTZZZ_REASONING_EFFORT", "").strip()  # e.g. low; empty = model default


def error_detail(e: openai.APIStatusError) -> str:
    """Readable message for both error shapes.

    OpenAI style: {"error": {"message": ...}} (the SDK unwraps it to the inner dict).
    GPTZZZ auth errors: {"code": "INVALID_API_KEY", "message": ...}.
    """
    body = e.body
    if isinstance(body, dict):
        inner = body.get("error")
        if isinstance(inner, dict) and inner.get("message"):
            return str(inner["message"])
        if body.get("message"):
            code = body.get("code")
            return f"{code}: {body['message']}" if code else str(body["message"])
    return str(e)


def print_usage(usage) -> None:
    if usage is None:
        print("[usage] none returned", file=sys.stderr)
        return
    print(
        f"[usage] input={usage.input_tokens} output={usage.output_tokens} total={usage.total_tokens}",
        file=sys.stderr,
    )


def main() -> int:
    api_key = os.environ.get("GPTZZZ_API_KEY")
    if not api_key:
        print("Set GPTZZZ_API_KEY first (see README).", file=sys.stderr)
        return 2

    args = sys.argv[1:]
    stream = "--stream" in args
    prompt = " ".join(a for a in args if a != "--stream") or "Reply with the single word: pong"

    client = OpenAI(base_url=BASE_URL, api_key=api_key, timeout=120)
    params = {"model": MODEL, "input": prompt}
    if EFFORT:
        params["reasoning"] = {"effort": EFFORT}

    try:
        if not stream:
            resp = client.responses.create(**params)
            if resp.status != "completed":
                print(f"status={resp.status}", file=sys.stderr)
            print(resp.output_text)
            print_usage(resp.usage)
            return 0 if resp.status == "completed" else 1

        completed = None
        for event in client.responses.create(stream=True, **params):
            if event.type == "response.output_text.delta":
                print(event.delta, end="", flush=True)
            elif event.type == "response.completed":
                completed = event.response
            elif event.type in ("response.failed", "response.incomplete", "error"):
                print(f"\n[{event.type}]", file=sys.stderr)
                return 1
        print(flush=True)
        if completed is None:
            # Codex reports this case as "stream closed before response.completed".
            print("Stream ended without response.completed.", file=sys.stderr)
            return 1
        print_usage(completed.usage)
        return 0
    except openai.APIStatusError as e:
        hint = " (no /responses on this endpoint?)" if e.status_code in (404, 405) else ""
        print(f"HTTP {e.status_code}: {error_detail(e)}{hint}", file=sys.stderr)
        return 1
    except openai.APIConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
