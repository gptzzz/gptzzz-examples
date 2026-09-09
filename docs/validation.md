# 验证记录

核对日期：2026-09-09。

## 已执行

| 检查 | 结果 | 范围 |
|---|---|---|
| Python 标准库 unittest | 14 项通过 | 本机 HTTP stub、请求格式、模型列表与错误处理 |
| Node.js 内置 test runner | 5 项通过 | 本机 HTTP stub、中文正文、格式异常、超时、禁止重定向 |
| 文档地址与配置 | 已核对 | 根据 gptzzz.ai 的公开教程，不使用私有后台 |
| 配套文章来源 | 已核对 | 既有 Semrush 原生稿 015，经技术审校及项目适配 |

复现命令（无需 API Key）：

```sh
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/chat.test.mjs
```

本地测试使用虚构的模型名和凭据，不能用于真实接口。代码不自动重试、不跟随重定向；错误输出不包含服务端原始响应正文。

Python `--timeout` 是底层网络操作的超时时间，不是整次请求的严格总时限；JavaScript 的计时器覆盖请求与读响应阶段。两者超时均不能证明服务端没有处理或计费。

## 尚未执行

没有用真实账户运行 `/v1/chat/completions` 或 `/v1/models`，没有验证真实模型、价格、额度、延迟或可靠性。没有测试流式、工具调用、Responses API 或文件接口。

因此，本项目不提供线上成功率、速度排名、节省费用或搜索引擎收录保证。完成自己的小额测试后，可按教程保存一份脱敏记录，并注明实际日期、模型和环境。

## 事实依据

- [gptzzz.ai 接入文档](https://gptzzz.ai/docs/)
- [站方最小请求教程](https://gptzzz.ai/blog/openai-api-quickstart/)
- [站方错误码说明](https://gptzzz.ai/docs/api-error-codes/)
