# 兼容性复测记录

> **English summary.** One row per live check against `https://gptzzz.ai/v1`. Only results from real requests go here; mock-gateway runs do not count. When you re-test, add a row with the date, the key group, what you checked and the result, and update the table in the README only if something changed.

每次用真实 key 复测都记一行。只记真实请求的结果；本地 mock 网关（`make test`）的通过不算在这里。README 的兼容性表只在这里的结果发生变化时更新。

| 日期 | 分组 | 检查项 | 结果 | 备注 |
|---|---|---|---|---|
| 2026-09-29 复测 | 测试分组 | `selftest.sh`，`GPTZZZ_MODEL=gpt-5.6-terra` | 6 项全部通过 | `/v1/models` 返回 19 个 ID，比当天上午多了 `gpt-5.2`、`gpt-5.3-codex-spark`（这两个没测）；chat 的 usage 为 13+5=18；流式 17 行 `data:`，usage 块之后是 `data: [DONE]`；工具调用 `get_weather({"city":"Paris"})`；Responses `completed`，usage 输入 4393、输出 5 token（同一句提示走 Chat Completions，输入是 13 token）；错误的 key 返回 401 `{"code":"INVALID_API_KEY","message":"Invalid API key"}` |
| 2026-09-29 复测 | 测试分组 | `python_json_mode.py`（`gpt-5.6-terra`，openai 2.26.0） | 通过 | 返回 `items`（3 个状态码）和 `note`，脚本解析并校验结构通过 |
| 2026-09-29 复测 | 测试分组 | `python_responses.py`，非流式和 `--stream` | 通过 | 非流式 `status: completed`；流式收到 `response.completed`；两次 usage 输入都是 4394 token |
| 2026-09-29 复测 | 测试分组 | `python_image.py`（内置 16×16 红色 PNG，base64） | 通过 | 模型回答 `Red` |
| 2026-09-29 复测 | 测试分组 | `python_tools.py` 完整往返 | 通过 | 模型调用 `get_weather(Paris)` 和 `get_weather(Tokyo)`，脚本回传结果后拿到最终回答 |
| 2026-09-29 复测 | 测试分组 | `examples/stdlib/list_models.py` | 失败：HTTP 403 | gptzzz.ai 前面的 CDN（Cloudflare）拒绝 Python `urllib` 默认的 `User-Agent: Python-urllib/3.x`，返回 `error code: 1010`，请求没有到达网关。脚本提示检查账户和 key，但原因不在 key。同一时间 curl 和 OpenAI Python SDK 请求同一接口都正常 |
| 2026-09-29 复测（修复后） | 测试分组 | `examples/stdlib/list_models.py`、`chat.py`（`gpt-5.6-terra`） | 通过 | `gateway.py` 改为显式发送 `User-Agent: gptzzz-examples/2.0 (+https://github.com/gptzzz/gptzzz-examples)` 后，列出模型和对话都正常 |
| 2026-09-29 | 测试分组 | `GET /v1/models` | 通过 | 对话模型：`gpt-6`、`gpt-6-sol`、`gpt-6-luna`、`gpt-6-astra`、`gpt-5.6`、`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna`、`gpt-5.5`、`gpt-5.4`、`gpt-5.4-mini`；另有 `codex-auto-review` 和 `gpt-image-*` |
| 2026-09-29 | 测试分组 | Chat Completions（非流式） | 通过 | `gpt-5.6`，返回 `usage` |
| 2026-09-29 | 测试分组 | SSE 流式 + `include_usage` | 通过 | 最后一个数据块带 usage，然后是 `data: [DONE]` |
| 2026-09-29 | 测试分组 | 工具调用 | 通过 | `finish_reason: "tool_calls"`，`arguments` 是合法 JSON；只测了第一步（模型发起调用） |
| 2026-09-29 | 测试分组 | JSON 模式 | 通过 | `response_format: {"type": "json_object"}` |
| 2026-09-29 | 测试分组 | Responses API | 通过 | `POST /v1/responses`，`status: completed` |
| 2026-09-29 | 测试分组 | 图片输入 | 通过 | base64 data URL 通过；远程 URL 在网关能下载到图片时通过 |
| 2026-09-29 | 测试分组 | `/v1/embeddings` | 不提供 | 返回 503 |
| 2026-09-29 | 测试分组 | 错误的 key | 401 | 响应体 `{"code":"INVALID_API_KEY","message":...}`，不是 OpenAI 的 `{"error":{...}}` |
| 2026-09-29 | 测试分组 | `reasoning_effort` 逐档（Chat Completions） | 见备注 | `gpt-6-astra`：`low`～`max` 通过，`none`、`minimal` 400。`gpt-5.6`、`gpt-5.6-sol`、`gpt-5.6-terra`：`none`～`max` 通过，`minimal` 400。其余模型未逐档测 |
| 2026-09-28 | 测试分组 | `gpt-6-astra` + `reasoning_effort: "none"` | 结果不一致 | 同一天既有 200，也有 400；09-29 复测恢复为 400 |
| 2026-09-16 | 测试分组 | `gpt-6-astra` + `reasoning_effort: "none"` | 400 | 报错列出的可选值为 `low`、`medium`、`high`、`xhigh`、`max` |

## 尚未用真实 key 验证的

- Codex CLI、OpenCode、Cline 三个真实工具的端到端对话。
- `python_image.py --url`（远程图片 URL）这个脚本本身；接口能力见上表 2026-09-29 的图片输入一行。

（2026-09-29 复测已补上：`python_tools.py` 的完整往返，以及 `python_json_mode.py`、`python_responses.py`（含 `--stream`）、`python_image.py`（base64）三个示例本身，见上表。）

## 已知问题

- `examples/stdlib/` 的两个脚本最初用 urllib 默认的 `User-Agent`，2026-09-29 复测时被 CDN 返回 HTTP 403；改为显式发送 `User-Agent` 后同日复测通过。自己改写这类客户端时，也建议带上一个能说明身份的 `User-Agent`。

## 怎么复测

```bash
read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
bash examples/selftest.sh 2>&1 | tee /tmp/selftest.txt   # 输出里不含 key
```

把结果按上表格式加一行，再开 PR。只写你实际跑过的项。
