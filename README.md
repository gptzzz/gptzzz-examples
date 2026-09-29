# GPTZZZ API 中转站接入示例：curl / Python / Node.js 调用与 Codex CLI、OpenCode、Cline 配置

用 curl、Python、Node.js 调用 GPTZZZ 这个 API 中转站（OpenAI 兼容接口，base_url 写到 `https://gptzzz.ai/v1` 为止）的可运行示例，覆盖流式、工具调用、JSON 模式、Responses API 和图片输入，附 Codex CLI、OpenCode、Cline 配置；`selftest.sh` 的 6 项自检适用于任何 OpenAI 兼容接口。每个示例都在本地假网关上自动测试，兼容性表只写真实请求测过的结果。

Tested, runnable examples for **GPTZZZ**, an OpenAI-compatible API gateway (API relay): curl, the OpenAI Python SDK, Node.js `fetch`, a zero-dependency Python client, and config files for Codex CLI, OpenCode and Cline. `examples/selftest.sh` checks any OpenAI-compatible endpoint in six steps.

[![test](https://github.com/gptzzz/gptzzz-examples/actions/workflows/test.yml/badge.svg)](https://github.com/gptzzz/gptzzz-examples/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Links / 链接：** [GPTZZZ 接入文档 / Docs](https://gptzzz.ai/docs/?utm_source=github&utm_medium=repo&utm_campaign=gptzzz-examples&utm_content=top) · [gptzzz.ai](https://gptzzz.ai/?utm_source=github&utm_medium=repo&utm_campaign=gptzzz-examples&utm_content=top) · [English](#english) · [中文说明](#中文说明)

> **Disclosure:** This repository is maintained by the GPTZZZ team (the author works on GPTZZZ). GPTZZZ is an independent third-party service. It is not affiliated with, endorsed by, or sponsored by OpenAI, or by the Codex CLI, OpenCode or Cline projects; their names appear here only to describe compatibility.
>
> **披露：** 本仓库由 GPTZZZ 团队维护，作者参与 GPTZZZ 运营。GPTZZZ 是独立的第三方服务，与 OpenAI 以及 Codex CLI、OpenCode、Cline 项目均无隶属、背书或赞助关系，文中提到这些名称只是为了说明兼容方式。

---

## English

### Quick start

```bash
git clone https://github.com/gptzzz/gptzzz-examples.git
cd gptzzz-examples

read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY   # paste your key; nothing is echoed
bash examples/curl.sh models                        # list the model IDs your key can use
bash examples/selftest.sh                           # six checks (five small billed requests)
```

No key yet? `make test` runs every example against a local fake gateway (`tests/mock_gateway.py`, 127.0.0.1 only), with no key and no cost.

All scripts read the key from the `GPTZZZ_API_KEY` environment variable. None of them print it, and no file in this repository contains a key.

| Variable | Default | Purpose |
|---|---|---|
| `GPTZZZ_API_KEY` | (required) | Your API key |
| `GPTZZZ_BASE_URL` | `https://gptzzz.ai/v1` | Base URL, including `/v1` and nothing after it |
| `GPTZZZ_MODEL` | `gpt-5.6` | Model ID; pick one from `/v1/models` |
| `GPTZZZ_REASONING_EFFORT` | (model default) | Only used by `python_responses.py` |

Every example except `curl.sh models` sends a real request and uses paid tokens.

### Examples

| File | What it shows | Run |
|---|---|---|
| [`examples/curl.sh`](examples/curl.sh) | Models, chat, streaming, tool calls, JSON mode, Responses API, image input | `bash examples/curl.sh all` (or `models`, `chat`, `stream`, `tools`, `json`, `responses`, `image`) |
| [`examples/selftest.sh`](examples/selftest.sh) | Six checks for any OpenAI-compatible endpoint; exit code = failed checks | `bash examples/selftest.sh` |
| [`examples/python_chat.py`](examples/python_chat.py) | OpenAI Python SDK with `base_url`; reads both error shapes | `pip install "openai>=1.40"`, then `python examples/python_chat.py "Hello"` |
| [`examples/python_stream.py`](examples/python_stream.py) | Streaming, with the final usage chunk | `python examples/python_stream.py` |
| [`examples/python_tools.py`](examples/python_tools.py) | Full tool-call round trip: call, run locally, send result, final answer | `python examples/python_tools.py "Weather in Paris and Tokyo?"` |
| [`examples/python_json_mode.py`](examples/python_json_mode.py) | `response_format: json_object`, then parse and check the shape | `python examples/python_json_mode.py` |
| [`examples/python_responses.py`](examples/python_responses.py) | Responses API (`/v1/responses`, what Codex CLI uses), streaming and reasoning effort | `python examples/python_responses.py --stream "Count to 5"` |
| [`examples/python_image.py`](examples/python_image.py) | Image input as base64 (local file) or remote URL | `python examples/python_image.py photo.jpg "What is this?"` |
| [`examples/node_chat.mjs`](examples/node_chat.mjs) | Node.js 18+ `fetch`, no npm install, optional SSE streaming | `node examples/node_chat.mjs --stream "Count to 5"` |
| [`examples/stdlib/chat.py`](examples/stdlib/chat.py) | Python standard library only; no retries, refuses redirects. Sends an explicit `User-Agent`, because some CDNs refuse urllib's default `Python-urllib/3.x`. Re-tested 2026-09-29: passes; see the [compatibility log](docs/compatibility-log.md) | `GPTZZZ_MODEL=gpt-5.6 python3 examples/stdlib/chat.py --prompt "Hello"` |
| [`examples/codex-config.toml`](examples/codex-config.toml) | Codex CLI custom provider, `wire_api = "responses"` | Merge into `~/.codex/config.toml` |
| [`examples/opencode.json`](examples/opencode.json) | OpenCode custom provider via `@ai-sdk/openai-compatible` | Merge into `opencode.json` |
| [`examples/cline.md`](examples/cline.md) | Cline "OpenAI Compatible" provider settings | Follow the steps |

### Compatibility

Checked on 2026-09-29 with real requests and one key group. Every re-test is logged in [`docs/compatibility-log.md`](docs/compatibility-log.md); re-run `selftest.sh` and note the date before you rely on a result.

| Feature | Result |
|---|---|
| `GET /v1/models` | Pass |
| Chat completions | Pass |
| Streaming: usage chunk, then `data: [DONE]` | Pass |
| Tool calls (`finish_reason: "tool_calls"`, JSON arguments) | Pass |
| JSON mode (`response_format: json_object`) | Pass |
| Responses API (`POST /v1/responses`, used by Codex CLI) | Pass |
| Image input, base64 data URL | Pass |
| Image input, remote URL | Pass when the image host lets the gateway download it |
| Embeddings (`/v1/embeddings`) | Not offered |
| Wrong key | `401` with `{"code":"INVALID_API_KEY","message":...}`, not OpenAI's nested `{"error":{...}}`; the Python and Node examples read both shapes |
| Reasoning effort | `gpt-6-astra`: `low` to `max` (`none` rejected). `gpt-5.6`, `gpt-5.6-sol`, `gpt-5.6-terra`: `none` to `max`. None of these accepts `minimal`; other models were not tested value by value |

Chat model IDs returned on 2026-09-29: `gpt-6`, `gpt-6-sol`, `gpt-6-luna`, `gpt-6-astra`, `gpt-5.6`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini` (a re-test later that day also listed `gpt-5.2` and `gpt-5.3-codex-spark`, which were not tested). Your key group may see a different list; `gpt-image-*` models are image models, not chat models.

### Tool notes

**Codex CLI** ([`codex-config.toml`](examples/codex-config.toml))
- Put the provider in the user-level `~/.codex/config.toml`. Codex ignores `model_provider` and `model_providers` in a project's `.codex/config.toml`.
- The provider ID can't be `openai`, `ollama` or `lmstudio`; those are reserved.
- `base_url` includes `/v1`. Codex appends `/responses`, and `wire_api = "responses"` is the only supported value.
- Smoke test without the TUI: `codex exec "Reply with the single word: ready"`.

**OpenCode** ([`opencode.json`](examples/opencode.json))
- Merge the `provider.gptzzz` block into `~/.config/opencode/opencode.json` (global) or `opencode.json` in your project root. OpenCode merges config files, so you don't need to replace yours.
- `"apiKey": "{env:GPTZZZ_API_KEY}"` reads the key from the environment. Then run `/models` and pick a GPTZZZ model.
- `@ai-sdk/openai-compatible` calls `/v1/chat/completions`. Add models to the `models` map using IDs from `/v1/models`.

**Cline**: see [`examples/cline.md`](examples/cline.md). **Dify**: use the GPTZZZ model provider plugin, [gptzzz/dify-plugin-gptzzz](https://github.com/gptzzz/dify-plugin-gptzzz).

**Coding agents**: [`skills/openai-compatible-gateway/SKILL.md`](skills/openai-compatible-gateway/SKILL.md) tells an agent how to write these configs and verify them with `selftest.sh`; [`AGENTS.md`](AGENTS.md) covers working in this repository.

### Troubleshooting

| Symptom | Usual cause |
|---|---|
| 404 on `.../v1/v1/chat/completions` | The base URL already ends in `/v1` and the client added another |
| 401 `INVALID_API_KEY` | Wrong, revoked or truncated key; `echo ${#GPTZZZ_API_KEY}` prints the length, not the key |
| 400 `Unsupported value: 'none' is not supported with the 'gpt-6-astra' model` | That model rejects that reasoning effort; see the compatibility table |
| "Model not found" right after setup | The tool's default model ID isn't served to your key group; copy one from `/v1/models` |
| Codex keeps using its default provider | The provider block is in a project-level `.codex/config.toml`, or the ID is reserved |
| Stream ends without `[DONE]` | Network or proxy cut the connection; run `selftest.sh` check 3 |
| Knowledge base / RAG asks for embeddings | Embeddings aren't offered; use a separate embeddings provider |

More, by HTTP status: [`docs/troubleshooting.md`](docs/troubleshooting.md) (Chinese, with an English summary).

### Keeping your key safe

- The key lives only in the `GPTZZZ_API_KEY` environment variable. `read -rs` keeps it out of your shell history.
- `selftest.sh` hands the key to curl through a pipe, so it doesn't appear in the process list, and scrubs it from anything it prints. The tests check that no example prints the key.
- `.gitignore` excludes `.env` files. If a key ever lands in a commit, revoke it in the GPTZZZ console and create a new one; deleting the commit is not enough. See [SECURITY.md](SECURITY.md).

### Development

`make lint` and `make test` are offline and need no key: the tests start `tests/mock_gateway.py` on 127.0.0.1 and run every example against it (the SDK examples need `pip install "openai>=1.40"`). `make selftest` sends real, billed requests. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 中文说明

### 快速开始

```bash
git clone https://github.com/gptzzz/gptzzz-examples.git
cd gptzzz-examples

read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY   # 粘贴 key，屏幕上不会显示
bash examples/curl.sh models                        # 列出你的 key 能用的模型 ID
bash examples/selftest.sh                           # 6 项自检（其中 5 次是小额计费请求）
```

还没有 key？`make test` 会在本地假网关（`tests/mock_gateway.py`，只监听 127.0.0.1）上跑全部示例，不需要 key，也不花钱。

所有脚本只从环境变量 `GPTZZZ_API_KEY` 读取 key，不会打印 key，仓库里的任何文件都不含 key。可选变量：`GPTZZZ_BASE_URL`（默认 `https://gptzzz.ai/v1`，只写到 `/v1` 为止）、`GPTZZZ_MODEL`（默认 `gpt-5.6`）、`GPTZZZ_REASONING_EFFORT`（只有 `python_responses.py` 用）。

除 `curl.sh models` 外，每个示例都会发出真实请求并消耗 token。第一次接入建议先看 [docs/first-request.md](docs/first-request.md)。

### 示例一览：用 curl / Python / Node.js 调用中转 API

| 文件 | 内容 |
|---|---|
| [`examples/curl.sh`](examples/curl.sh) | 模型列表、对话、流式、工具调用、JSON 模式、Responses API、图片输入 |
| [`examples/selftest.sh`](examples/selftest.sh) | 6 项自检，任何 OpenAI 兼容接口都能用；退出码等于失败项数 |
| [`examples/python_chat.py`](examples/python_chat.py) | OpenAI 官方 Python SDK（`openai` 包）设置 `base_url`；两种错误格式都能读出（需 `pip install "openai>=1.40"`） |
| [`examples/python_stream.py`](examples/python_stream.py) | 流式输出，读取最后的 usage 块 |
| [`examples/python_tools.py`](examples/python_tools.py) | 完整的工具调用往返：模型发起调用 → 本地执行 → 回传结果 → 最终回答 |
| [`examples/python_json_mode.py`](examples/python_json_mode.py) | JSON 模式：`response_format: json_object`，解析后再校验结构 |
| [`examples/python_responses.py`](examples/python_responses.py) | Responses API（Codex CLI 用的接口），支持 `--stream` 和推理强度 |
| [`examples/python_image.py`](examples/python_image.py) | 图片输入：本地文件转 base64，或远程 URL |
| [`examples/node_chat.mjs`](examples/node_chat.mjs) | Node.js 18+ 原生 `fetch`，无依赖，`--stream` 切换流式 |
| [`examples/stdlib/`](examples/stdlib/chat.py) | 只用 Python 标准库的最小客户端：`chat.py`、`list_models.py`；不自动重试，拒绝重定向。请求会显式带上 `User-Agent`，因为有些 CDN 会拒绝 urllib 默认的 `Python-urllib/3.x`。2026-09-29 复测通过，见[复测记录](docs/compatibility-log.md) |
| [`examples/codex-config.toml`](examples/codex-config.toml) | Codex CLI 自定义 provider，`wire_api = "responses"` |
| [`examples/opencode.json`](examples/opencode.json) | OpenCode 自定义 provider，使用 `@ai-sdk/openai-compatible` |
| [`examples/cline.md`](examples/cline.md) | Cline 的 "OpenAI Compatible" 设置步骤（英文） |

### 兼容性（2026-09-29 用一个分组的 key 实测）

| 功能 | 结果 |
|---|---|
| `GET /v1/models` | 通过 |
| Chat Completions | 通过 |
| 流式：最后一个 usage 块，然后 `data: [DONE]` | 通过 |
| 工具调用（`finish_reason: "tool_calls"`，参数是合法 JSON） | 通过 |
| JSON 模式 | 通过 |
| Responses API（`POST /v1/responses`，Codex CLI 用的就是它） | 通过 |
| 图片输入：base64 | 通过 |
| 图片输入：远程 URL | 图片所在站点允许网关下载时通过 |
| Embeddings（`/v1/embeddings`） | 不提供 |
| 错误的 key | `401`，响应体为 `{"code":"INVALID_API_KEY","message":...}`，不是 OpenAI 的 `{"error":{...}}` 嵌套格式；Python 和 Node 示例两种格式都能解析 |
| 推理强度 | `gpt-6-astra` 接受 `low` 到 `max`，传 `none` 被拒；`gpt-5.6`、`gpt-5.6-sol`、`gpt-5.6-terra` 接受 `none` 到 `max`；以上都不接受 `minimal`；其余模型未逐档测试 |

接口会变化。每次复测都记在 [docs/compatibility-log.md](docs/compatibility-log.md)；依赖某项结果前，请重新运行 `selftest.sh` 并记下日期。当天返回的对话模型 ID 见上方英文部分；不同分组看到的列表可能不同，`gpt-image-*` 是图像模型，不能用于对话。

### Codex CLI、OpenCode、Cline 接入中转站要点

- **Codex CLI**：配置必须写在用户级 `~/.codex/config.toml`，项目内 `.codex/config.toml` 里的 `model_provider`、`model_providers` 会被忽略；provider ID 不能用 `openai`、`ollama`、`lmstudio`；`base_url` 要带 `/v1`；`wire_api = "responses"` 是唯一支持的取值。用 `codex exec "Reply with the single word: ready"` 快速验证。
- **OpenCode**：把 `provider.gptzzz` 这一段合并进 `~/.config/opencode/opencode.json` 或项目根目录的 `opencode.json`（OpenCode 会合并多个配置文件）。`"apiKey": "{env:GPTZZZ_API_KEY}"` 从环境变量读 key，然后运行 `/models` 选择模型。
- **Cline**：API Provider 选 "OpenAI Compatible"，Base URL 填 `https://gptzzz.ai/v1`，填入 key 和模型 ID。价格字段不确定就留空。详见 [`examples/cline.md`](examples/cline.md)。
- **Dify**：用 GPTZZZ 的模型供应商插件 [gptzzz/dify-plugin-gptzzz](https://github.com/gptzzz/dify-plugin-gptzzz)，已合并进 Dify 插件仓库。
- **让编程代理自己配**：把 [`skills/openai-compatible-gateway/SKILL.md`](skills/openai-compatible-gateway/SKILL.md) 交给 Codex、OpenCode 等代理，它会写配置并用 `selftest.sh` 验证。

### 常见问题：中转 base_url、404 与 401 排查

| 现象 | 常见原因 |
|---|---|
| 请求地址变成 `.../v1/v1/chat/completions`，返回 404 | Base URL 已经带了 `/v1`，客户端又拼了一次 |
| 401 `INVALID_API_KEY` | key 错误、已作废或复制不完整；`echo ${#GPTZZZ_API_KEY}` 只显示长度，不显示 key |
| 400 `Unsupported value: 'none' is not supported with the 'gpt-6-astra' model` | 该模型不接受这一档推理强度，见上面的兼容性表 |
| 刚配好就提示模型不存在 | 工具默认的模型 ID 不在你的分组里，从 `/v1/models` 复制一个 |
| Codex 一直走默认 provider | provider 写在了项目级配置里，或者用了保留 ID |
| 流式输出没有 `[DONE]` 就断了 | 网络或代理中断了连接；运行 `selftest.sh` 第 3 项排查 |
| 知识库 / RAG 要求配置嵌入模型 | 不提供 embeddings，请另选向量服务 |

按 HTTP 状态码分层的完整排查见 [docs/troubleshooting.md](docs/troubleshooting.md)。

### key 安全

- key 只放在环境变量里；`read -rs` 不会把它写进 shell 历史。
- `selftest.sh` 通过管道把 key 交给 curl，进程列表里看不到；输出内容里如果出现 key，会被替换成 `[REDACTED]`。测试会检查每个示例都不打印 key。
- `.gitignore` 已忽略 `.env` 类文件。如果 key 被提交进仓库，请立即在 GPTZZZ 控制台作废并重新生成，只删提交记录是不够的。详见 [SECURITY.md](SECURITY.md)。

### 开发与贡献

`make lint`、`make test` 都离线运行、不需要 key：测试会在 127.0.0.1 上启动假网关，逐个运行全部示例（SDK 示例需要先 `pip install "openai>=1.40"`）。`make selftest` 会发出真实的计费请求。提 Issue 或 PR 前请看 [CONTRIBUTING.md](CONTRIBUTING.md)，更新记录见 [CHANGELOG.md](CHANGELOG.md)。

本仓库原名 `gptzzz-api-examples`，旧地址会自动跳转到这里；原来的标准库示例移到了 `examples/stdlib/`。

---

### About GPTZZZ

GPTZZZ is an OpenAI-compatible API gateway at `https://gptzzz.ai/v1`, billed per token; current rates are on the pricing page of the GPTZZZ site.
The website, console and docs are in Simplified Chinese. GPTZZZ 的网站、控制台和文档目前为简体中文。
Code in this repository: [MIT License](LICENSE).
