# make test      offline: every example against tests/mock_gateway.py (no key, no cost)
# make lint      offline: syntax checks for every script and config file
# make models    real request: GET /v1/models with $GPTZZZ_API_KEY (usually free)
# make selftest  real requests: examples/selftest.sh (5 small billed requests)

PYTHON ?= python3
NODE   ?= node

.PHONY: help test lint models selftest mock

help:
	@sed -n '1,4p' Makefile

test:
	$(PYTHON) -m unittest discover -s tests -v
	$(NODE) --test tests/chat.test.mjs

lint:
	bash -n examples/curl.sh examples/selftest.sh
	@if command -v shellcheck >/dev/null 2>&1; then shellcheck examples/*.sh; else echo "shellcheck not installed, skipped"; fi
	$(PYTHON) -m py_compile examples/*.py examples/stdlib/*.py tests/*.py
	$(NODE) --check examples/node_chat.mjs
	$(PYTHON) -c "import json; json.load(open('examples/opencode.json'))"
	@$(PYTHON) -c "import sys, tomllib; tomllib.load(open('examples/codex-config.toml', 'rb'))" 2>/dev/null \
	  && echo "codex-config.toml parses" || echo "tomllib needs Python 3.11+, TOML check skipped"

models:
	@test -n "$$GPTZZZ_API_KEY" || { echo "run: read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY"; exit 2; }
	bash examples/curl.sh models

selftest:
	@test -n "$$GPTZZZ_API_KEY" || { echo "run: read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY"; exit 2; }
	bash examples/selftest.sh

mock:
	$(PYTHON) tests/mock_gateway.py --port 8787
