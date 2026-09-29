"""JSON mode against GPTZZZ with the official OpenAI Python SDK.

    pip install "openai>=1.40"
    read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
    python examples/python_json_mode.py "List three HTTP status codes a client should retry."

response_format={"type": "json_object"} asks for a single JSON object. Two
rules from the OpenAI API apply here too: the messages must mention JSON, and
the reply is only guaranteed to be valid JSON, not to follow any particular
schema. So this script parses the reply and checks the keys it needs itself.
"""

import json
import os
import sys

import openai
from openai import OpenAI

BASE_URL = os.environ.get("GPTZZZ_BASE_URL", "https://gptzzz.ai/v1")
MODEL = os.environ.get("GPTZZZ_MODEL", "gpt-5.6")

SYSTEM = (
    "You answer in JSON only. Return one object with two keys: "
    '"items" (an array of short strings) and "note" (one sentence).'
)


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
    question = " ".join(sys.argv[1:]) or "List three HTTP status codes a client should retry."

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": question},
            ],
        )
    except openai.APIStatusError as e:
        print(f"HTTP {e.status_code}: {error_detail(e)}", file=sys.stderr)
        return 1
    except openai.APIConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1

    choice = resp.choices[0]
    if choice.finish_reason == "length":
        print("The reply hit the token limit, so the JSON is probably cut off.", file=sys.stderr)
        return 1

    raw = choice.message.content or ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Reply is not valid JSON ({e}). First 200 chars: {raw[:200]!r}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        print(f"Valid JSON, but not the expected shape: {raw[:200]!r}", file=sys.stderr)
        return 1

    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
