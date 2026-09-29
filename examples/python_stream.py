"""Streaming chat completion against GPTZZZ with the official OpenAI Python SDK.

    pip install "openai>=1.40"
    read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
    python examples/python_stream.py "Write a haiku about rate limits."

With stream_options={"include_usage": True} the server sends one extra chunk
after the text, with an empty `choices` list and the token usage. The SDK
consumes the final `data: [DONE]` line for you.
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

    client = OpenAI(base_url=BASE_URL, api_key=api_key, timeout=120)
    prompt = " ".join(sys.argv[1:]) or "Count from 1 to 10, one number per line."

    usage = None
    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    print(delta.content, end="", flush=True)
            if chunk.usage:
                usage = chunk.usage
    except openai.APIStatusError as e:
        print(f"\nHTTP {e.status_code}: {error_detail(e)}", file=sys.stderr)
        return 1
    except openai.APIConnectionError as e:
        print(f"\nConnection error (stream interrupted?): {e}", file=sys.stderr)
        return 1

    print(flush=True)
    if usage:
        print(
            f"[usage] prompt={usage.prompt_tokens} completion={usage.completion_tokens} total={usage.total_tokens}",
            file=sys.stderr,
        )
    else:
        print("[usage] no usage chunk received", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
