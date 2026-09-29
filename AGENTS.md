# AGENTS.md

Notes for coding agents (Codex, OpenCode and others) working in this repository.

## What this repository is

Runnable examples for calling an OpenAI-compatible API (GPTZZZ by default) from
curl, Python and Node.js, plus config files for Codex CLI, OpenCode and Cline.
`examples/selftest.sh` checks any OpenAI-compatible endpoint.

If the user wants you to set up a client against their gateway, follow
`skills/openai-compatible-gateway/SKILL.md`.

## Commands

| Task | Command | Network / cost |
|---|---|---|
| All tests | `make test` | Offline. Uses `tests/mock_gateway.py` on 127.0.0.1 and a fake key |
| Syntax and config checks | `make lint` | Offline |
| Try examples by hand without a key | `make mock`, then `export GPTZZZ_BASE_URL=http://127.0.0.1:8787/v1 GPTZZZ_API_KEY=sk-mock-gptzzz-examples` | Offline |
| List real model IDs | `make models` | Real request, normally free |
| Real self-test | `make selftest` | Five small billed requests; ask the user first |

## Rules

- The API key is only ever read from `GPTZZZ_API_KEY`. Do not add a `--api-key`
  flag, do not read `.env` files automatically, and do not print the key.
  Tests assert that no example prints the key it was given.
- Tests must stay offline. New examples get a mock route in
  `tests/mock_gateway.py` and a test in `tests/test_examples.py`.
- The compatibility table in `README.md` lists only results from real requests.
  Mock-gateway passes do not go there; record real re-tests in
  `docs/compatibility-log.md`.
- No prices or discount figures anywhere in the repository.
- Keep examples short and dependency-free where possible: the curl, Node and
  `examples/stdlib/` examples need nothing beyond the runtime; the Python SDK
  examples need only `openai`.
