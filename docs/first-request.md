# 从一条请求开始接入 GPTZZZ（OpenAI 兼容接口）

> **English summary.** Set the key in an environment variable, list the model IDs your key can use with `GET /v1/models`, send one minimal chat request, and check the response fields before adding streaming, tools or a real workload. Keep the base URL at `https://gptzzz.ai/v1`; clients append `/chat/completions` or `/responses` themselves.

最后核对：2026-09-29 ｜ [← 返回 README](../README.md)

这一页只做一件事：用最少的变量发出第一条请求，并确认结果真的可用。后面的流式、工具调用、Codex CLI 等，都建立在这一步通过的基础上。

## 1. 准备：key 放进环境变量

```bash
read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY   # 粘贴 key 后回车，屏幕不显示，也不进 shell 历史
echo ${#GPTZZZ_API_KEY}                             # 只打印长度，确认没有粘贴成空值
```

- 不要把 key 写进代码、`.env` 以外的文件、截图或 Git 提交。本仓库的 `.gitignore` 已忽略 `.env`。
- 不要开 `set -x` 之类会回显变量的调试选项。
- 建议给测试单独建一个 key，用完可以在控制台作废。

## 2. 先查模型 ID，不要猜

```bash
bash examples/curl.sh models
```

返回的每一行就是一个可以填进 `model` 字段的 ID。能用哪些 ID 取决于 key 所在的分组，**产品页上的展示名不一定等于接口 ID**。2026-09-29 返回的对话模型包括 `gpt-6`、`gpt-6-sol`、`gpt-6-luna`、`gpt-6-astra`、`gpt-5.6`、`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna`、`gpt-5.5`、`gpt-5.4`、`gpt-5.4-mini`；`gpt-image-*` 是图像模型，不能用于对话。

`GET /v1/models` 一般不计费，适合用来确认 key 和地址都对。

## 3. 发一条最小请求

Base URL 写到 `/v1` 为止，路径由客户端拼接：`POST https://gptzzz.ai/v1/chat/completions`。

```bash
curl -sS https://gptzzz.ai/v1/chat/completions \
  -H "Authorization: Bearer $GPTZZZ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5.6", "messages": [{"role": "user", "content": "Reply with the single word: pong"}]}'
```

最小正文只有 `model` 和 `messages`。先别加系统提示、历史对话、工具或采样参数，这样出错时只需要排查地址、鉴权、模型三件事。

同一件事的其他写法：

| 写法 | 文件 | 依赖 |
|---|---|---|
| OpenAI 官方 Python SDK | [examples/python_chat.py](../examples/python_chat.py) | `pip install "openai>=1.40"` |
| Node.js 原生 `fetch` | [examples/node_chat.mjs](../examples/node_chat.mjs) | Node.js 18+，无 npm 依赖 |
| 只用 Python 标准库 | [examples/stdlib/chat.py](../examples/stdlib/chat.py) | Python 3.9+，无依赖；不自动重试、不跟随重定向。请求显式带 `User-Agent`（有些 CDN 会拒绝 urllib 的默认值），2026-09-29 复测通过，见[复测记录](compatibility-log.md) |

用 SDK 时，和 OpenAI 官方接口相比只改两处：`base_url="https://gptzzz.ai/v1"`，以及 key 从 `GPTZZZ_API_KEY` 读取。

## 4. 看结果，而不只看“没报错”

一条请求算通过，至少要满足：

| 检查项 | 在哪里看 | 说明 |
|---|---|---|
| HTTP 200 | 状态码 | 401 看 key，404 看路径和模型 ID，详见 [troubleshooting.md](troubleshooting.md) |
| 有文字 | `choices[0].message.content` | 空字符串也算失败 |
| 正常结束 | `choices[0].finish_reason` | `stop` 正常；`length` 表示被截断，不能当完整回答 |
| 有用量 | `usage.prompt_tokens`、`completion_tokens`、`total_tokens` | 推理模型的思考 token 计入 `completion_tokens` |

`model` 字段可能返回别名或实际路由到的型号，不能单靠它判断上游来源；`usage` 是本次请求的计量，最终以控制台账单为准。

## 5. 一次只加一个变量

第一条请求通过后，按下面的顺序逐项扩展，每一步都能用本仓库的示例单独验证：

1. 流式输出：`bash examples/curl.sh stream` 或 `python examples/python_stream.py`，确认最后是 usage 块和 `data: [DONE]`。
2. 工具调用：`python examples/python_tools.py`，确认 `finish_reason` 是 `tool_calls`，把结果发回去后能拿到最终回答。
3. JSON 模式：`python examples/python_json_mode.py`。
4. Responses API：`python examples/python_responses.py`。Codex CLI 只走这个接口。
5. 图片输入：`python examples/python_image.py`。

想一次查完，就跑 `bash examples/selftest.sh`（6 项，其中 5 次小额计费请求）。

## 6. 留一份可复现的记录

出问题时记下：时间和时区、脚本或 SDK 版本、脱敏后的完整 URL、模型 ID、HTTP 状态、耗时、`finish_reason`、响应头里的请求 ID（如果有）。**不要记录 `Authorization` 头和完整 key**，提示词只保留复现需要的部分。

从 Key、Base URL 到首个请求的完整接入步骤，见 GPTZZZ 站内教程：[API 中转站怎么用：从 Key、Base URL 到首个请求](https://gptzzz.ai/blog/api-zhongzhuan-how-to-use/?utm_source=github&utm_medium=repo&utm_campaign=gptzzz-examples&utm_content=first_request)（维护方撰写）。
