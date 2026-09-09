# GPTZZZ API 接入示例

用 Python 或 JavaScript 发出一条最小聊天请求，再按 HTTP 状态排查问题。项目面向 [GPTZZZ（gptzzz.ai）](https://gptzzz.ai/) 的兼容接口；站方页面使用 KaiGPT 名称。

**从这里开始：** [中文接入教程](docs/first-request.md) · [错误排查](docs/troubleshooting.md) · [配套文章：用最小请求定位 API 中转问题](articles/api-integration-guide.md)

## 项目包含什么

- Python 3.9+：最小聊天请求、模型 ID 查询，使用标准库。
- Node.js 20+：最小聊天请求，使用内置 `fetch`，无需安装 npm 包。
- 本地模拟测试：验证请求格式、错误响应、超时和重定向处理，不需要 API Key，不调用收费接口。
- 中文技术文档与一篇由既有 Semrush 草稿整理的文章，说明如何核查调用结果。

这是接入起点。默认不自动重试，不包含流式、工具调用、文件上传或模型性能评测。真实账户权限、模型 ID、费用和兼容范围需在当前账户中确认。

## 快速开始

下载仓库或使用 Git 克隆后，在项目根目录执行。以下设置适用于 Bash / zsh：

```sh
export GPTZZZ_BASE_URL='https://gptzzz.ai/v1'
export GPTZZZ_MODEL='替换为账号中的模型ID'
printf 'GPTZZZ API Key: '
read -r -s GPTZZZ_API_KEY
printf '\n'
export GPTZZZ_API_KEY
```

使用专用测试 Key。不要把密钥写进代码、截图、文章或 Git 提交；不要打开 shell 的变量跟踪。`.env.example` 只是配置说明，脚本不会自动读取 `.env`。

选择一种语言运行即可：

```sh
# Python
python3 scripts/chat.py --prompt '用一句话解释 API 中转站' --timeout 30

# JavaScript
node scripts/chat.mjs --prompt '用一句话解释 API 中转站' --timeout 30
```

**上面的两条命令会分别发起真实请求，可能产生费用。** 不需要为了验证同一个账户同时执行两种语言。成功时终端输出模型返回的文字，失败时给出简要排查提示与非零退出码。

查阅帮助不会发起网络请求：

```sh
python3 scripts/chat.py --help
node scripts/chat.mjs --help
```

可选的模型列表查询：

```sh
python3 scripts/list_models.py
```

该命令尝试站方错误文档提及的 `GET /v1/models`。这个资源尚未用真实账号验证；若不开放，回控制台复制模型 ID。聊天脚本不会猜测或自动选择模型。

## 地址与请求

| 项目 | 示例配置 |
|---|---|
| 基础地址 | `https://gptzzz.ai/v1` |
| 聊天路径 | `POST /chat/completions` |
| 鉴权 | `Authorization: Bearer <API_KEY>` |
| 正文 | `model`、`messages`、`stream: false` |
| 超时 | 默认 30 秒，可用 `--timeout` 设置 |

`GPTZZZ_BASE_URL` 不要填完整的 `/chat/completions` 地址。脚本拒绝含 URL 用户名、密码、查询参数、片段的基础地址，并拒绝自动跟随重定向。HTTP 仅供 loopback 地址上的本地模拟测试使用。

排错时会输出 HTTP 状态或通用网络提示，不输出服务端完整错误正文，避免把凭据和业务内容带入日志。若需要响应头、用量或结束原因，可在受控环境中扩展代码；请先脱敏。一次返回文字不等于内容正确或所有能力都已验收。

## 不用密钥也能运行的测试

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/chat.test.mjs
```

测试只监听本机临时端口并使用虚构凭据，校验请求路径、认证格式、中文正文、异常响应以及拒绝重定向等行为。测试结果和边界见 [验证记录](docs/validation.md)。

## 文章与来源

- [从一条请求开始接入 GPTZZZ](docs/first-request.md)：配置与验收步骤。
- [按错误发生的位置排查 GPTZZZ 请求](docs/troubleshooting.md)：400/401/403/404/429/5xx 与超时的检查顺序。
- [用最小请求定位 API 中转问题](articles/api-integration-guide.md)：基于已保存的 Semrush 原生稿 015，经 Codex 编辑、技术审校与项目适配。

协议事实依据 [站方接入文档](https://gptzzz.ai/docs/)、[最小请求教程](https://gptzzz.ai/blog/openai-api-quickstart/)和[错误码说明](https://gptzzz.ai/docs/api-error-codes/)，核对日期为 2026-09-09。文档可以变化，模型权限与用量以账户当时的结果为准。

## 参与改进

提交问题时提供运行时版本、复现步骤、HTTP 状态和脱敏后的请求结构。请移除 API Key、Authorization、私人提示词和账单信息。

代码采用 [MIT License](LICENSE)。
