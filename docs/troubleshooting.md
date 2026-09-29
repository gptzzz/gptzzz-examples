# GPTZZZ 接口排错：按 HTTP 状态码分层排查

> **English summary.** First find out whether you got an HTTP status at all. No status means DNS, TLS, proxy or timeout; a status means read the body. GPTZZZ returns `401 {"code":"INVALID_API_KEY","message":...}` for a bad key (not OpenAI's nested `{"error":{...}}`), `400 Unsupported value` when a model rejects a reasoning effort, and does not offer `/v1/embeddings`. Fix 400/401/404 before retrying; retry 429 and 5xx only with a limit, because a timed-out request may already have been processed and billed.

最后核对：2026-09-29 ｜ [← 返回 README](../README.md)

## 第 0 步：先用自检脚本定位是哪一层

```bash
read -rs GPTZZZ_API_KEY && export GPTZZZ_API_KEY
bash examples/selftest.sh
```

| 自检结果 | 说明问题在哪 |
|---|---|
| 第 1 项就失败，HTTP 401 | key 本身（错、作废、复制不完整） |
| 第 1 项失败，`000` | 根本没连上：网络、DNS、代理、证书 |
| 第 1 项通过但提示模型不在列表 | `GPTZZZ_MODEL` 填了分组里没有的 ID |
| 第 1、2 项通过，第 3 项失败 | 流式被代理缓冲或截断 |
| 第 1～3 项通过，第 5 项失败 | 该模型不支持 Responses，或请求被改写；Codex CLI 会受影响 |
| 全部通过，你的客户端仍然报错 | 问题多半在客户端配置：Base URL、模型 ID、协议选项 |

自检全部通过、只有某个工具不行时，直接看 README 里对应工具的要点，不用往下查接口。

## 没有 HTTP 状态码

| 现象 | 先查什么 |
|---|---|
| `Could not resolve host` | DNS；公司网络或代理是否拦截了域名 |
| `SSL certificate problem` / `CERTIFICATE_VERIFY_FAILED` | 系统时间是否正确；中间人代理是否替换了证书（公司网络常见） |
| `Connection refused` / `Connection reset` | 代理设置（`HTTPS_PROXY`）；本机防火墙 |
| 超时 | 连接阶段超时查网络；已发出请求后才超时，服务端**可能已经处理并计费**，先查控制台记录再决定是否重发 |

## 400 Bad Request

| 错误信息里出现 | 原因 | 怎么改 |
|---|---|---|
| `Unsupported value: 'none' is not supported with the 'gpt-6-astra' model` | 这个模型不接受这一档推理强度 | 2026-09-29 实测：`gpt-6-astra` 只接受 `low` 到 `max`；`gpt-5.6`、`gpt-5.6-sol`、`gpt-5.6-terra` 接受 `none` 到 `max`；都不接受 `minimal`。其余模型以报错里列出的可选值为准 |
| `Error while downloading file` | 图片用的是远程 URL，网关下载不到 | 改用 base64 data URL（见 `examples/python_image.py`），或确认图片地址公网可访问、没有防盗链 |
| `messages` / `input` 字段相关 | Chat Completions 用 `messages`，Responses 用 `input`，混用会 400 | 对照 `examples/curl.sh` 里的 chat 和 responses 两段 |
| `temperature` / `top_p` 相关 | 推理模型在推理强度不是 `none` 时可能不接受采样参数 | 先去掉采样参数再试 |
| JSON 解析错误 | 请求体不是合法 JSON（shell 引号最常见） | 用 heredoc 或 `jq -n` 生成请求体，参考 `examples/curl.sh` |

## 401 Unauthorized

GPTZZZ 对无效 key 返回：

```json
{"code": "INVALID_API_KEY", "message": "..."}
```

这和 OpenAI 的 `{"error": {"message": ...}}` 结构不同。只认 OpenAI 结构的客户端，可能只显示一句笼统的“请求失败”，看不到这条信息。本仓库的 Python 和 Node 示例两种结构都能读出来。

排查顺序：

1. `echo ${#GPTZZZ_API_KEY}`：长度是 0 说明变量没进当前 shell；和控制台里的 key 长度不一样，说明复制不完整或带了空格、引号。
2. 从 IDE、桌面快捷方式启动的程序，不一定能看到你在终端里 `export` 的变量。
3. key 是否已在控制台作废或到期。

## 404 Not Found

先分清是**路径**错还是**模型**错：

| 情况 | 特征 | 修复 |
|---|---|---|
| 路径多了一层 `/v1` | 请求地址里有 `/v1/v1/` | Base URL 只写到 `/v1`；少数客户端（如 NextChat）会自己补 `/v1`，这时 Base URL 不带 `/v1` |
| 把完整路径填进了 Base URL | 地址以 `/chat/completions/chat/completions` 结尾 | Base URL 填 `https://gptzzz.ai/v1` |
| 模型不存在 | 错误信息里提到 model | 从 `bash examples/curl.sh models` 的输出复制 ID |
| `/v1/embeddings` | 调用向量接口 | GPTZZZ 不提供 embeddings，知识库、RAG 需要另配向量服务 |

## 429 Too Many Requests

429 可能是速率或并发限制，也可能是额度、余额不足。两者处理方法相反：

- 限流：看响应头里的 `Retry-After`，按指数退避加随机抖动重试，设最大次数。
- 额度：等待不会恢复，先去控制台核对余额和分组。

不要在多层同时重试（SDK 一层、业务代码一层、网关客户端再一层），否则一次失败会被放大成十几次请求。

## 5xx 与流式中断

| 现象 | 说明 | 怎么做 |
|---|---|---|
| 500 / 502 / 503 | 网关或上游暂时异常 | 记下 UTC 时间和请求 ID；限次重试 |
| 流式输出一次性吐出 | 中间的反向代理在缓冲 SSE | 自建 Nginx 时加 `proxy_buffering off;` |
| 流在 `[DONE]` 之前断开 | 网络中断，或代理空闲超时 | `bash examples/curl.sh stream` 看最后一行；长推理任务调大客户端的空闲超时 |
| 没有 usage 块 | 没开 `stream_options.include_usage`，或流被截断 | 本仓库的流式示例都开了这个选项 |

**重试之前先想清楚**：5xx 和读超时都不能证明服务端没有执行。请求可能已经完成并计费，重发会再计一次。

## Codex CLI 专项

| 现象 | 原因 |
|---|---|
| 配置了 provider，Codex 仍走默认服务 | 写在了项目级 `.codex/config.toml`（provider 相关键会被忽略），或 `model_provider` 写在了某个 `[表]` 后面 |
| `model_providers contains reserved built-in provider IDs` | provider ID 用了 `openai`、`ollama` 或 `lmstudio` |
| `stream disconnected before completion` | 流被截断；先跑 `python examples/python_responses.py --stream` 确认 |
| `Missing environment variable` | `env_key` 指向的变量在启动 Codex 的 shell 里没有设置 |

## 反馈问题时附什么

时间和时区、使用的示例或客户端及版本、脱敏后的完整请求 URL、模型 ID、HTTP 状态、错误正文（去掉 key）、`selftest.sh` 的输出。**不要附 key 和 `Authorization` 头。**

各状态码在 GPTZZZ 侧的含义和处理方式，另见站内的 [API 中转站错误码排查：400、401、404、429 与 5xx](https://gptzzz.ai/blog/api-relay-error-codes/?utm_source=github&utm_medium=repo&utm_campaign=gptzzz-examples&utm_content=troubleshooting)（维护方撰写）。
