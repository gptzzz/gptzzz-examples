"""Local HTTP stub tests only: no real API Key, gateway calls, or billing."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from gateway import GatewayClient, GatewayError, model_from_env, normalize_base_url


KEY = "local-test-key-not-a-real-credential"
MODEL = "local-stub-model"
PROMPT = "本地测试内容：请勿记入错误日志。"


@contextmanager
def stub(status=200, body=None, headers=None, delay=0, disconnect=False):
    requests = []
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8") if not isinstance(body, bytes) else body

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_POST(self):
            self.respond()

        def respond(self):
            payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            requests.append({"method": self.command, "path": self.path,
                             "headers": dict(self.headers), "body": payload})
            if disconnect:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if delay:
                time.sleep(delay)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:{}/v1".format(server.server_port), requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class GatewayTests(unittest.TestCase):
    def run_cli(self, script, base_url, extra=(), model=MODEL, key=KEY):
        env = dict(os.environ)
        env.update(GPTZZZ_BASE_URL=base_url, GPTZZZ_API_KEY=key,
                   NO_PROXY="127.0.0.1,localhost,::1", no_proxy="127.0.0.1,localhost,::1")
        if model is None:
            env.pop("GPTZZZ_MODEL", None)
        else:
            env["GPTZZZ_MODEL"] = model
        return subprocess.run([sys.executable, "-B", str(PROJECT / "scripts" / script), *extra],
                              env=env, text=True, capture_output=True, timeout=5)

    def setUp(self):
        self.proxy_patch = patch.dict(os.environ, {"NO_PROXY": "127.0.0.1,localhost,::1",
                                                   "no_proxy": "127.0.0.1,localhost,::1"})
        self.proxy_patch.start()

    def tearDown(self):
        self.proxy_patch.stop()

    def test_chat_path_authentication_and_json(self):
        with stub(body={"choices": [{"message": {"content": "本地回答"}}]}) as (url, seen):
            result = GatewayClient(KEY, url + "/").chat(PROMPT, MODEL)
            self.assertEqual(result, "本地回答")
            self.assertEqual(len(seen), 1)
            sent = seen[0]
            self.assertEqual((sent["method"], sent["path"]), ("POST", "/v1/chat/completions"))
            self.assertEqual(sent["headers"]["Authorization"], "Bearer " + KEY)
            self.assertEqual(sent["headers"]["Content-Type"], "application/json")
            self.assertEqual(json.loads(sent["body"]), {
                "model": MODEL, "messages": [{"role": "user", "content": PROMPT}], "stream": False})

    def test_list_models_and_cli_without_model_env(self):
        with stub(body={"data": [{"id": MODEL}, {"id": "another-local-stub"}]}) as (url, seen):
            result = self.run_cli("list_models.py", url, model=None)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, MODEL + "\nanother-local-stub\n")
            self.assertEqual(result.stderr, "")
            self.assertEqual(len(seen), 1)
            self.assertEqual((seen[0]["method"], seen[0]["path"]), ("GET", "/v1/models"))
            self.assertEqual(seen[0]["headers"]["Authorization"], "Bearer " + KEY)
            self.assertEqual(seen[0]["body"], b"")

    def test_chat_cli_success(self):
        with stub(body={"choices": [{"message": {"content": "CLI 本地回答"}}]}) as (url, seen):
            result = self.run_cli("chat.py", url, ("--prompt", PROMPT, "--timeout", "1"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "CLI 本地回答\n")
            self.assertEqual(result.stderr, "")
            self.assertEqual(len(seen), 1)

    def test_model_is_required_before_request(self):
        for values in ({}, {"GPTZZZ_MODEL": "   "}):
            with self.subTest(values=values), self.assertRaises(GatewayError):
                model_from_env(values)
        with stub(body={}) as (url, seen):
            result = self.run_cli("chat.py", url, ("--prompt", PROMPT), model=None)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("GPTZZZ_MODEL", result.stderr)
            self.assertEqual(seen, [])
            self.assertNotIn(PROMPT, result.stderr)

    def test_key_required_before_request(self):
        with stub(body={}) as (url, seen):
            result = self.run_cli("list_models.py", url, key="")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("GPTZZZ_API_KEY", result.stderr)
            self.assertEqual(seen, [])

    def test_timeout_and_no_automatic_retry(self):
        with stub(body={}, delay=0.25) as (url, seen):
            result = self.run_cli("chat.py", url, ("--prompt", PROMPT, "--timeout", "0.03"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("超时", result.stderr)
            self.assertEqual(len(seen), 1)
            self.assertNotIn(KEY, result.stderr)
            self.assertNotIn(PROMPT, result.stderr)

    def test_http_401_does_not_echo_body_or_secrets(self):
        secret_body = {"error": KEY + " | " + PROMPT + " | private-response"}
        with stub(status=401, body=secret_body) as (url, seen):
            result = self.run_cli("chat.py", url, ("--prompt", PROMPT))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("HTTP 401", result.stderr)
            self.assertEqual(result.stdout, "")
            for private in (KEY, PROMPT, "private-response"):
                self.assertNotIn(private, result.stderr)
            self.assertEqual(len(seen), 1)

    def test_invalid_json_is_a_friendly_error(self):
        for body in (b"not-json-private-response", b"\xff", b"[]"):
            with self.subTest(body=body), stub(body=body) as (url, seen):
                result = self.run_cli("list_models.py", url)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("JSON", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("private-response", result.stderr)
                self.assertEqual(len(seen), 1)

    def test_invalid_chat_shapes(self):
        for body in ({}, {"choices": []}, {"choices": {}}, {"choices": [None]},
                     {"choices": [{"message": None}]},
                     *({"choices": [{"message": {"content": content}}]}
                       for content in (None, "", "  ", [], {}, 42))):
            with self.subTest(body=body), stub(body=body) as (url, seen):
                with self.assertRaises(GatewayError):
                    GatewayClient(KEY, url).chat(PROMPT, MODEL)
                self.assertEqual(len(seen), 1)

    def test_invalid_model_list(self):
        for body in ({}, {"data": []}, {"data": {}}, {"data": [None]},
                     {"data": [{"id": ""}]}, {"data": [{"id": 123}]}):
            with self.subTest(body=body), stub(body=body) as (url, seen):
                with self.assertRaises(GatewayError):
                    GatewayClient(KEY, url).list_models()
                self.assertEqual(len(seen), 1)

    def test_redirects_never_reach_another_origin(self):
        with stub(body={"data": [{"id": "redirect-target"}]}) as (target_url, target_seen):
            for status in (301, 302, 303, 307, 308):
                with self.subTest(status=status), stub(status=status, body={},
                          headers={"Location": target_url + "/models"}) as (url, seen):
                    with self.assertRaisesRegex(GatewayError, "HTTP {}.*重定向".format(status)):
                        GatewayClient(KEY, url).list_models()
                    self.assertEqual(len(seen), 1)
            self.assertEqual(target_seen, [])

    def test_base_url_validation(self):
        for url in ("https://user:pass@example.com/v1", "https://user@example.com/v1",
                    "https://example.com/v1?x=1", "https://example.com/v1?",
                    "https://example.com/v1#part", "https://example.com/v1#",
                    "https://example.com/v1/chat/completions/",
                    "https://example.com/v1/%63hat/completions", "http://example.com/v1",
                    "http://192.168.1.1/v1", "ftp://localhost/v1", "/v1", "",
                    "https://example.com:bad/v1", "https://example.com:0/v1"):
            with self.subTest(url=url), self.assertRaises(GatewayError):
                normalize_base_url(url)
        for url in ("https://gptzzz.ai/v1", "https://example.com/proxy/v1",
                    "http://127.0.0.1:8000/v1", "http://localhost:8000/v1", "http://[::1]:8000/v1"):
            with self.subTest(url=url):
                self.assertEqual(normalize_base_url(url + "/"), url)

    def test_timeout_must_be_finite_and_positive(self):
        for timeout in ("0", "-1", "nan", "inf", "invalid"):
            with self.subTest(timeout=timeout):
                with self.assertRaises(GatewayError):
                    GatewayClient(KEY, timeout=timeout)
                result = self.run_cli("list_models.py", "http://127.0.0.1:1/v1", ("--timeout", timeout))
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

    def test_network_error_does_not_leak_configuration(self):
        with stub(disconnect=True) as (url, seen):
            result = self.run_cli("list_models.py", url)
            self.assertEqual(len(seen), 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("网络", result.stderr)
        self.assertNotIn(KEY, result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
