"""Minimal chat completion against GPTZZZ with the official OpenAI Python SDK.

    pip install "openai>=1.40"
    read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
    python examples/python_chat.py "Explain HTTP 429 in one sentence."

The only GPTZZZ-specific parts are base_url and the environment variable that
holds the key. Everything else is standard OpenAI SDK code.
"""

import os
import sys

import openai
from openai import OpenAI

BASE_URL = os.environ.get("GPTZZZ_BASE_URL", "https://gptzzz.ai/v1")
MODEL = os.environ.get("GPTZZZ_MODEL", "gpt-5.6")


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


def main() -> int:
    api_key = os.environ.get("GPTZZZ_API_KEY")
    if not api_key:
        print("Set GPTZZZ_API_KEY first (see README).", file=sys.stderr)
        return 2

    client = OpenAI(base_url=BASE_URL, api_key=api_key, timeout=60)
    prompt = " ".join(sys.argv[1:]) or "Reply with the single word: pong"

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": prompt},
            ],
        )
    except openai.APIStatusError as e:
        print(f"HTTP {e.status_code}: {error_detail(e)}", file=sys.stderr)
        return 1
    except openai.APIConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1

    print(resp.choices[0].message.content)
    if resp.usage:
        u = resp.usage
        print(
            f"[usage] prompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
