"""Run every example against the local mock gateway (tests/mock_gateway.py).

Offline: no real key, no request leaves 127.0.0.1, nothing is billed.

    python3 -m unittest discover -s tests -v

Tests that need a tool that is not installed (bash + curl + jq for the shell
scripts, node for node_chat.mjs, the `openai` package for the SDK examples,
Python 3.11+ for tomllib) are skipped with a message instead of failing.
"""

from __future__ import annotations

import codecs
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mock_gateway import MOCK_KEY, MockGateway  # noqa: E402

HAVE_SHELL = all(shutil.which(b) for b in ("bash", "curl", "jq"))
HAVE_NODE = shutil.which("node") is not None
HAVE_OPENAI = importlib.util.find_spec("openai") is not None
WRONG_KEY = "sk-wrong-key-must-never-be-printed-0000"


class ExampleRun(unittest.TestCase):
    gw: MockGateway

    @classmethod
    def setUpClass(cls) -> None:
        cls.gw = MockGateway().__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.gw.__exit__(None, None, None)

    def run_example(self, *cmd: str, key: str = MOCK_KEY, model: str = "gpt-5.6", timeout: int = 60,
                    extra_env: dict | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("GPTZZZ_"):
                del env[k]
        env.update({
            "GPTZZZ_BASE_URL": self.gw.base_url,
            "GPTZZZ_API_KEY": key,
            "GPTZZZ_MODEL": model,
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        env.update(extra_env or {})
        proc = subprocess.run(list(cmd), cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
        # Whatever happens, no example may print the key it was given.
        if key:
            self.assertNotIn(key, proc.stdout + proc.stderr, f"{cmd} printed the API key")
        return proc


@unittest.skipUnless(HAVE_SHELL, "needs bash, curl and jq")
class ShellExamples(ExampleRun):
    def test_selftest_passes_all_six_checks(self):
        p = self.run_example("bash", "examples/selftest.sh")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("6 passed, 0 failed", p.stdout)
        self.assertIn("gateway shape", p.stdout)  # check 6 reports the {code, message} error body

    def test_selftest_wrong_key_fails_without_printing_it(self):
        p = self.run_example("bash", "examples/selftest.sh", key=WRONG_KEY)
        self.assertEqual(p.returncode, 5, p.stdout)  # checks 1-5 fail, check 6 uses its own fake key
        self.assertIn("INVALID_API_KEY", p.stdout)

    def test_selftest_unknown_model(self):
        p = self.run_example("bash", "examples/selftest.sh", model="no-such-model")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("no-such-model is not one of them", p.stdout)

    def test_selftest_requires_key(self):
        p = self.run_example("bash", "examples/selftest.sh", key="")
        self.assertEqual(p.returncode, 64)
        self.assertIn("GPTZZZ_API_KEY is not set", p.stderr)

    def test_curl_all(self):
        p = self.run_example("bash", "examples/curl.sh", "all")
        self.assertEqual(p.returncode, 0, p.stderr)
        for section in ("== models ==", "== chat ==", "== stream ==", "== tools ==",
                        "== json_mode ==", "== responses ==", "== image =="):
            self.assertIn(section, p.stdout)
        self.assertIn("data: [DONE]", p.stdout)
        self.assertIn('"tool_calls"', p.stdout)
        self.assertIn('"status": "completed"', p.stdout)

    def test_curl_wrong_key_shows_real_error(self):
        p = self.run_example("bash", "examples/curl.sh", "models", key=WRONG_KEY)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("INVALID_API_KEY", p.stderr)


@unittest.skipUnless(HAVE_NODE, "needs node 18+")
class NodeExample(ExampleRun):
    def test_plain(self):
        p = self.run_example("node", "examples/node_chat.mjs", "Hello")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "pong")
        self.assertIn("[usage] prompt=9 completion=2 total=11", p.stderr)

    def test_stream(self):
        p = self.run_example("node", "examples/node_chat.mjs", "--stream", "Count to 5")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "pong")
        self.assertNotIn("without data: [DONE]", p.stderr)
        self.assertIn("[usage]", p.stderr)

    def test_wrong_key(self):
        p = self.run_example("node", "examples/node_chat.mjs", "Hello", key=WRONG_KEY)
        self.assertEqual(p.returncode, 1)
        self.assertIn("HTTP 401: INVALID_API_KEY", p.stderr)


@unittest.skipUnless(HAVE_OPENAI, "needs the openai package: pip install 'openai>=1.40'")
class PythonSDKExamples(ExampleRun):
    def py(self, script: str, *args: str, **kw) -> subprocess.CompletedProcess:
        return self.run_example(sys.executable, f"examples/{script}", *args, **kw)

    def test_chat(self):
        p = self.py("python_chat.py", "Hello")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "pong")

    def test_chat_wrong_key_reads_gateway_error_shape(self):
        p = self.py("python_chat.py", "Hello", key=WRONG_KEY)
        self.assertEqual(p.returncode, 1)
        self.assertIn("HTTP 401: INVALID_API_KEY: Invalid API key", p.stderr)

    def test_chat_unknown_model_reads_openai_error_shape(self):
        p = self.py("python_chat.py", "Hello", model="no-such-model")
        self.assertEqual(p.returncode, 1)
        self.assertIn("HTTP 404", p.stderr)
        self.assertIn("does not exist", p.stderr)

    def test_stream_reports_usage_chunk(self):
        p = self.py("python_stream.py")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("[usage] prompt=9 completion=2 total=11", p.stderr)

    def test_tools_round_trip(self):
        p = self.py("python_tools.py", "What's the weather in Paris and in Tokyo?")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Paris: 18 C, cloudy", p.stdout)
        self.assertIn("Tokyo: 24 C, sunny", p.stdout)
        self.assertEqual(p.stderr.count("[tool] get_weather"), 2)
        # the second request carried both tool results back
        last_path, last_req = self.gw.requests[-1]
        self.assertEqual(last_path, "/v1/chat/completions")
        self.assertEqual([m["role"] for m in last_req["messages"]], ["user", "assistant", "tool", "tool"])

    def test_json_mode(self):
        p = self.py("python_json_mode.py")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["items"], ["429", "502", "503"])
        _, req = self.gw.requests[-1]
        self.assertEqual(req["response_format"], {"type": "json_object"})

    def test_responses(self):
        p = self.py("python_responses.py")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "pong")
        self.assertIn("[usage] input=9 output=2 total=11", p.stderr)

    def test_responses_stream(self):
        p = self.py("python_responses.py", "--stream", "Count to 5")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "pong")
        _, req = self.gw.requests[-1]
        self.assertTrue(req["stream"])

    def test_responses_effort_is_sent_as_reasoning_object(self):
        p = self.py("python_responses.py", extra_env={"GPTZZZ_REASONING_EFFORT": "low"})
        self.assertEqual(p.returncode, 0, p.stderr)
        _, req = self.gw.requests[-1]
        self.assertEqual(req["reasoning"], {"effort": "low"})
        p = self.py("python_responses.py", extra_env={"GPTZZZ_REASONING_EFFORT": "minimal"})
        self.assertEqual(p.returncode, 1)
        self.assertIn("HTTP 400", p.stderr)

    def test_image_base64(self):
        p = self.py("python_image.py")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "Red")
        _, req = self.gw.requests[-1]
        self.assertTrue(req["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,iVBOR"))

    def test_image_url_that_gateway_cannot_fetch(self):
        p = self.py("python_image.py", "--url", "https://images.example/private.png")
        self.assertEqual(p.returncode, 1)
        self.assertIn("can the gateway download that URL", p.stderr)


class StdlibExamples(ExampleRun):
    def test_list_models_and_chat(self):
        p = self.run_example(sys.executable, "examples/stdlib/list_models.py")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("gpt-5.6", p.stdout.split())
        p = self.run_example(sys.executable, "examples/stdlib/chat.py", "--prompt", "Hello")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "pong")


class ConfigFiles(unittest.TestCase):
    @unittest.skipIf(sys.version_info < (3, 11), "tomllib needs Python 3.11+")
    def test_codex_config(self):
        import tomllib

        cfg = tomllib.loads((EX / "codex-config.toml").read_text(encoding="utf-8"))
        self.assertEqual(cfg["model_provider"], "gptzzz")
        provider = cfg["model_providers"]["gptzzz"]
        self.assertEqual(provider["base_url"], "https://gptzzz.ai/v1")
        self.assertEqual(provider["wire_api"], "responses")
        self.assertEqual(provider["env_key"], "GPTZZZ_API_KEY")
        self.assertNotIn(cfg["model_provider"], {"openai", "ollama", "lmstudio"})

    def test_opencode_config(self):
        cfg = json.loads((EX / "opencode.json").read_text(encoding="utf-8"))
        provider = cfg["provider"]["gptzzz"]
        self.assertEqual(provider["npm"], "@ai-sdk/openai-compatible")
        self.assertEqual(provider["options"]["baseURL"], "https://gptzzz.ai/v1")
        self.assertEqual(provider["options"]["apiKey"], "{env:GPTZZZ_API_KEY}")
        self.assertTrue(provider["models"])


# Words that must never appear in this repository. Stored ROT13-encoded so this
# file does not itself mention them: the other brand, and a vendor this
# repository makes no claims about.
_BANNED_ROT13 = ["xnvtcg", "xnv tcg", "xnv·tcg", "pynhqr", "nageuebcvp", "/i1/zrffntrf"]
BANNED = [codecs.decode(w, "rot13") for w in _BANNED_ROT13]
LINK_RE = re.compile(r"\]\((https?://(?:www\.)?gptzzz\.ai[^)]*)\)|<(https?://gptzzz\.ai[^>]*)>")


class RepositoryRules(unittest.TestCase):
    def files(self):
        for path in ROOT.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                if path.suffix in {".md", ".py", ".sh", ".mjs", ".json", ".toml", ".yml", ".yaml", ".txt", ""}:
                    yield path

    def test_no_banned_words(self):
        short_brand = re.compile(r"\b" + codecs.decode("xnv", "rot13") + r"\b", re.I)
        for path in self.files():
            text = path.read_text(encoding="utf-8", errors="ignore")
            for word in BANNED:
                self.assertNotIn(word, text.lower(), f"{path.relative_to(ROOT)} mentions a banned word")
            self.assertIsNone(short_brand.search(text), f"{path.relative_to(ROOT)} mentions a banned word")

    def test_self_link_budget(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(len(LINK_RE.findall(readme)), 2, "README must link gptzzz.ai exactly twice (top line)")
        docs = sum(len(LINK_RE.findall(p.read_text(encoding="utf-8"))) for p in (ROOT / "docs").glob("*.md"))
        self.assertLessEqual(docs, 2, "docs/ may link gptzzz.ai at most twice")
        for path in list((ROOT / "examples").rglob("*.md")) + list((ROOT / "skills").rglob("*.md")):
            self.assertEqual(LINK_RE.findall(path.read_text(encoding="utf-8")), [], f"{path} links gptzzz.ai")

    def test_no_prices_or_discounts(self):
        pattern = re.compile(r"[¥$€]\s?\d|\d+\s?%\s?off\b|\d(\.\d)?\s?折|\d+\s?%\s?(折扣|优惠)", re.I)
        for path in ROOT.rglob("*.md"):
            for n, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                self.assertIsNone(pattern.search(line), f"{path.relative_to(ROOT)}:{n}: {line.strip()[:80]}")


if __name__ == "__main__":
    unittest.main()
