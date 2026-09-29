"""Tool (function) calling round trip against GPTZZZ with the OpenAI Python SDK.

    pip install "openai>=1.40"
    read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
    python examples/python_tools.py "What's the weather in Paris and in Tokyo?"

Flow: the model asks for get_weather(...), this script runs the function
locally, sends the result back as a `tool` message, and prints the model's
final answer. The weather data is fake; swap in your own function.
"""

import json
import os
import sys

import openai
from openai import OpenAI

BASE_URL = os.environ.get("GPTZZZ_BASE_URL", "https://gptzzz.ai/v1")
MODEL = os.environ.get("GPTZZZ_MODEL", "gpt-5.6")
MAX_ROUNDS = 4  # stop runaway tool loops

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name, e.g. Paris"},
                },
                "required": ["city"],
            },
        },
    }
]


def get_weather(city: str) -> dict:
    """Demo implementation. Returns made-up data."""
    fake = {"paris": (18, "cloudy"), "tokyo": (24, "sunny")}
    temp_c, condition = fake.get(city.strip().lower(), (20, "clear"))
    return {"city": city, "temp_c": temp_c, "condition": condition, "source": "demo data"}


TOOL_IMPL = {"get_weather": get_weather}


def run_tool(name: str, raw_args: str) -> str:
    try:
        args = json.loads(raw_args or "{}")
        result = TOOL_IMPL[name](**args)
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        result = {"error": f"{type(e).__name__}: {e}"}
    return json.dumps(result)


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
    question = " ".join(sys.argv[1:]) or "What's the weather in Paris right now?"
    messages = [{"role": "user", "content": question}]

    try:
        for _ in range(MAX_ROUNDS):
            resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
            msg = resp.choices[0].message

            if not msg.tool_calls:
                print(msg.content)
                return 0

            # Echo the assistant turn (with its tool_calls) back into the history.
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in msg.tool_calls
                    ],
                }
            )
            for call in msg.tool_calls:
                print(f"[tool] {call.function.name}({call.function.arguments})", file=sys.stderr)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": run_tool(call.function.name, call.function.arguments),
                    }
                )
    except openai.APIStatusError as e:
        print(f"HTTP {e.status_code}: {error_detail(e)}", file=sys.stderr)
        return 1
    except openai.APIConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1

    print(f"Stopped after {MAX_ROUNDS} tool rounds without a final answer.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
