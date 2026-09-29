# Changelog

All notable changes to this repository. Dates are UTC+8.

## [2.0.0] - 2026-09-29

The repository was renamed from `gptzzz-api-examples` to `gptzzz-examples`; the old
URL redirects here.

### Added
- `examples/curl.sh`: models, chat, streaming, tool calls, JSON mode, Responses API
  and image input in one script.
- `examples/selftest.sh`: six checks for any OpenAI-compatible endpoint; exit code is
  the number of failed checks.
- OpenAI Python SDK examples: `python_chat.py`, `python_stream.py`, `python_tools.py`
  (full tool round trip), `python_json_mode.py`, `python_responses.py` (with
  `--stream`), `python_image.py` (base64 or remote URL).
- `examples/node_chat.mjs`: Node.js 18+ `fetch`, no dependencies, optional SSE streaming.
- Config files for Codex CLI (`codex-config.toml`), OpenCode (`opencode.json`) and
  Cline (`cline.md`).
- `tests/mock_gateway.py`: an offline fake gateway on 127.0.0.1, and
  `tests/test_examples.py`, which runs every example against it.
- `Makefile` (`make test`, `make lint`, `make models`, `make selftest`), CI on Ubuntu
  and macOS with no secrets.
- `docs/troubleshooting.md` by HTTP status, `docs/compatibility-log.md`,
  `skills/openai-compatible-gateway/SKILL.md` and `AGENTS.md` for coding agents.
- `SECURITY.md`, `CONTRIBUTING.md`, issue template.

### Changed
- The 1.0.0 standard-library client moved to `examples/stdlib/` (`gateway.py`,
  `chat.py`, `list_models.py`), unchanged apart from the path. Its tests are in
  `tests/test_gateway.py`.
- `docs/first-request.md` rewritten; `GET /v1/models` is now verified with a real key
  (2026-09-29).
- `docs/validation.md` replaced by `docs/compatibility-log.md`.

### Removed
- `scripts/chat.mjs` (replaced by `examples/node_chat.mjs`; its tests now cover the new file).
- `articles/api-integration-guide.md`.

## [1.0.0] - 2026-09-09

- Minimal chat request and model list in Python (standard library) and Node.js, with
  local stub tests. Published as `gptzzz-api-examples`.
