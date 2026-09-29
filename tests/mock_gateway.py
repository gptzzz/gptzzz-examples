#!/usr/bin/env python3
"""A local fake of an OpenAI-compatible gateway, for offline tests.

It listens on 127.0.0.1 only, accepts one fake key, and imitates the behaviour
recorded in README.md (checked against GPTZZZ on 2026-09-29):

  GET  /v1/models                      model list
  POST /v1/chat/completions            text, SSE stream (usage chunk, then [DONE]),
                                       tool calls and the follow-up answer,
                                       JSON mode, image input
  POST /v1/responses                   non-streaming and streaming (response.completed)
  POST /v1/embeddings                  503: not offered
  wrong key                            401 {"code": "INVALID_API_KEY", "message": ...}
  unknown model                        404 {"error": {...}} (OpenAI shape)

Nothing here talks to the network. Run it by hand to try the examples:

    python3 tests/mock_gateway.py --port 8787
    export GPTZZZ_BASE_URL=http://127.0.0.1:8787/v1 GPTZZZ_API_KEY=sk-mock-gptzzz-examples
    bash examples/selftest.sh
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

MOCK_KEY = "sk-mock-gptzzz-examples"
MODELS = ["gpt-6", "gpt-6-astra", "gpt-5.6", "gpt-5.6-sol", "gpt-5.4-mini"]
TEXT = "pong"


def _usage_chat(prompt_tokens: int = 9, completion_tokens: int = 2) -> Dict[str, int]:
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _usage_responses() -> Dict[str, int]:
    return {"input_tokens": 9, "output_tokens": 2, "total_tokens": 11}


class Handler(BaseHTTPRequestHandler):
    server_version = "mock-gateway/1.0"
    protocol_version = "HTTP/1.1"

    # ---- plumbing -------------------------------------------------------
    def log_message(self, fmt: str, *args: Any) -> None:  # keep test output quiet
        pass

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _start_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

    def _sse(self, data: Any, event: Optional[str] = None) -> None:
        chunk = ""
        if event:
            chunk += f"event: {event}\n"
        chunk += "data: " + (data if isinstance(data, str) else json.dumps(data)) + "\n\n"
        self.wfile.write(chunk.encode("utf-8"))
        self.wfile.flush()

    def _authorized(self) -> bool:
        if self.headers.get("Authorization", "") == f"Bearer {self.server.key}":  # type: ignore[attr-defined]
            return True
        self._send_json(401, {"code": "INVALID_API_KEY", "message": "Invalid API key"})
        return False

    def _read_json(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": {"message": "invalid JSON body", "type": "invalid_request_error"}})
            return None
        if not isinstance(data, dict):
            self._send_json(400, {"error": {"message": "body must be an object", "type": "invalid_request_error"}})
            return None
        return data

    def _check_model(self, req: Dict[str, Any]) -> bool:
        if req.get("model") in MODELS:
            return True
        self._send_json(404, {"error": {
            "message": f"The model `{req.get('model')}` does not exist or you do not have access to it.",
            "type": "invalid_request_error", "code": "model_not_found"}})
        return False

    # ---- routes ---------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        if not self._authorized():
            return
        if self.path.rstrip("/") == "/v1/models":
            data = [{"id": m, "object": "model", "created": 1790000000, "owned_by": "mock"} for m in MODELS]
            self._send_json(200, {"object": "list", "data": data})
        else:
            self._send_json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            return
        req = self._read_json()
        if req is None:
            return
        path = self.path.rstrip("/")
        self.server.requests.append((path, req))  # type: ignore[attr-defined]
        if path == "/v1/embeddings":
            self._send_json(503, {"error": {"message": "embeddings are not offered", "type": "service_unavailable"}})
        elif path == "/v1/chat/completions":
            if self._check_model(req):
                self._chat(req)
        elif path == "/v1/responses":
            if self._check_model(req):
                self._responses(req)
        else:
            self._send_json(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    # ---- chat completions ----------------------------------------------
    def _chat_reply(self, req: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Return (message, finish_reason) for a non-streaming or streaming reply."""
        messages: List[Dict[str, Any]] = req.get("messages") or []
        last = messages[-1] if messages else {}
        if req.get("tools") and last.get("role") == "user":
            city = "Paris"
            text = str(last.get("content", ""))
            calls = []
            for i, name in enumerate(c for c in ("Paris", "Tokyo") if c.lower() in text.lower()):
                calls.append({"id": f"call_mock_{i}", "type": "function",
                              "function": {"name": "get_weather", "arguments": json.dumps({"city": name})}})
            if not calls:
                calls = [{"id": "call_mock_0", "type": "function",
                          "function": {"name": "get_weather", "arguments": json.dumps({"city": city})}}]
            return {"role": "assistant", "content": None, "tool_calls": calls}, "tool_calls"
        if last.get("role") == "tool":
            results = [json.loads(m["content"]) for m in messages if m.get("role") == "tool"]
            summary = "; ".join(f"{r.get('city')}: {r.get('temp_c')} C, {r.get('condition')}" for r in results)
            return {"role": "assistant", "content": f"Weather (demo data): {summary}."}, "stop"
        if (req.get("response_format") or {}).get("type") == "json_object":
            content = json.dumps({"items": ["429", "502", "503"], "note": "Retry with backoff.",
                                  "ok": True, "lang": "en"})
            return {"role": "assistant", "content": content}, "stop"
        content = last.get("content")
        if isinstance(content, list) and any(p.get("type") == "image_url" for p in content if isinstance(p, dict)):
            url = next(p["image_url"]["url"] for p in content if isinstance(p, dict) and p.get("type") == "image_url")
            if not url.startswith("data:image/"):
                self._send_json(400, {"error": {"message": "Error while downloading file", "type": "invalid_request_error"}})
                return {}, ""
            return {"role": "assistant", "content": "Red"}, "stop"
        return {"role": "assistant", "content": TEXT}, "stop"

    def _chat(self, req: Dict[str, Any]) -> None:
        message, finish = self._chat_reply(req)
        if not finish:
            return  # an error was already sent
        created = int(time.time())
        if not req.get("stream"):
            self._send_json(200, {
                "id": "chatcmpl-mock", "object": "chat.completion", "created": created, "model": req["model"],
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                "usage": _usage_chat(),
            })
            return
        base = {"id": "chatcmpl-mock", "object": "chat.completion.chunk", "created": created, "model": req["model"]}
        self._start_sse()
        self._sse({**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]})
        text = message.get("content") or ""
        for piece in (text[i:i + 3] for i in range(0, len(text), 3)):
            self._sse({**base, "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}]})
        self._sse({**base, "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]})
        if (req.get("stream_options") or {}).get("include_usage"):
            self._sse({**base, "choices": [], "usage": _usage_chat()})
        self._sse("[DONE]")

    # ---- responses -------------------------------------------------------
    def _responses(self, req: Dict[str, Any]) -> None:
        effort = (req.get("reasoning") or {}).get("effort")
        if effort == "minimal":
            self._send_json(400, {"error": {
                "message": f"Unsupported value: 'minimal' is not supported with the '{req['model']}' model.",
                "type": "invalid_request_error", "param": "reasoning.effort"}})
            return
        item = {"id": "msg_mock", "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": TEXT, "annotations": []}]}
        response = {"id": "resp_mock", "object": "response", "created_at": int(time.time()),
                    "model": req["model"], "status": "completed", "output": [item],
                    "usage": {**_usage_responses(),
                              "input_tokens_details": {"cached_tokens": 0},
                              "output_tokens_details": {"reasoning_tokens": 0}}}
        if not req.get("stream"):
            self._send_json(200, response)
            return
        self._start_sse()
        in_progress = {**response, "status": "in_progress", "output": [], "usage": None}
        self._sse({"type": "response.created", "sequence_number": 0, "response": in_progress}, "response.created")
        self._sse({"type": "response.output_text.delta", "sequence_number": 1, "item_id": "msg_mock",
                   "output_index": 0, "content_index": 0, "delta": TEXT, "logprobs": []},
                  "response.output_text.delta")
        self._sse({"type": "response.output_item.done", "sequence_number": 2, "output_index": 0, "item": item},
                  "response.output_item.done")
        self._sse({"type": "response.completed", "sequence_number": 3, "response": response}, "response.completed")


class MockGateway:
    """Context manager: `with MockGateway() as gw: gw.base_url`."""

    def __init__(self, key: str = MOCK_KEY, port: int = 0) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.server.key = key  # type: ignore[attr-defined]
        self.server.requests = []  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/v1"

    @property
    def requests(self) -> list:
        return self.server.requests  # type: ignore[attr-defined]

    def __enter__(self) -> "MockGateway":
        self.thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline fake of an OpenAI-compatible gateway (127.0.0.1 only).")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--key", default=MOCK_KEY, help=f"accepted API key (default {MOCK_KEY})")
    args = parser.parse_args()
    with MockGateway(args.key, args.port) as gw:
        print(f"mock gateway on {gw.base_url} (key: {args.key}); Ctrl-C to stop", flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
