"""Image input against GPTZZZ with the OpenAI Python SDK.

    pip install "openai>=1.40"
    read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
    python examples/python_image.py                         # built-in 16x16 red PNG
    python examples/python_image.py photo.jpg "What is in this picture?"
    python examples/python_image.py --url https://example.com/cat.png "Describe it."

Two ways to send an image in a chat message:
  - base64 data URL (default here): the bytes travel inside your request, so it
    works for local files and for images on private networks;
  - remote URL (--url): the gateway downloads the image itself, so the URL must
    be publicly reachable and the image host must allow the download. If it
    does not, the request fails with HTTP 400 even though your code is fine.
"""

import base64
import mimetypes
import os
import sys
from pathlib import Path

import openai
from openai import OpenAI

BASE_URL = os.environ.get("GPTZZZ_BASE_URL", "https://gptzzz.ai/v1")
MODEL = os.environ.get("GPTZZZ_MODEL", "gpt-5.6")
MAX_BYTES = 20 * 1024 * 1024

# 16x16 solid red PNG (the same one examples/curl.sh sends), so this runs without a file.
DEMO_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAFklEQVR42mO4I2JDEmIY1TCqYfhqAAAeBCwQ"
    "81sZJgAAAABJRU5ErkJggg=="
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


def image_part(args: list) -> tuple:
    """Return (content part, remaining args)."""
    if args[:1] == ["--url"]:
        if len(args) < 2:
            raise SystemExit("--url needs an https:// image URL")
        return {"type": "image_url", "image_url": {"url": args[1]}}, args[2:]
    if args and Path(args[0]).is_file():
        path = Path(args[0])
        if path.stat().st_size > MAX_BYTES:
            raise SystemExit(f"{path} is larger than {MAX_BYTES // (1024 * 1024)} MB")
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}, args[1:]
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{DEMO_PNG}"}}, args


def main() -> int:
    api_key = os.environ.get("GPTZZZ_API_KEY")
    if not api_key:
        print("Set GPTZZZ_API_KEY first (see README).", file=sys.stderr)
        return 2

    part, rest = image_part(sys.argv[1:])
    question = " ".join(rest) or "What colour is this image? Answer in one word."

    client = OpenAI(base_url=BASE_URL, api_key=api_key, timeout=120)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": [{"type": "text", "text": question}, part]}],
        )
    except openai.APIStatusError as e:
        hint = ""
        if e.status_code == 400 and part["image_url"]["url"].startswith("http"):
            hint = " (can the gateway download that URL? try a local file instead)"
        print(f"HTTP {e.status_code}: {error_detail(e)}{hint}", file=sys.stderr)
        return 1
    except openai.APIConnectionError as e:
        print(f"Connection error: {e}", file=sys.stderr)
        return 1

    print(resp.choices[0].message.content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
