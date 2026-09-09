# 从一条请求开始接入 GPTZZZ

此项目用 **GPTZZZ（gptzzz.ai）** 指代目标服务，站方页面使用 **KaiGPT** 名称。接入地址以 [gptzzz.ai 官网](https://gptzzz.ai/)和[站方接入教程](https://gptzzz.ai/blog/openai-api-quickstart/)为依据。此项目的验证范围是**本地模拟响应，真实账号可用性尚未测试**；本文不据此判断模型权限、实际费用或线上性能。

**1. 先保持请求最小**

从账号取得 API Key 和当前可用的模型 ID；模型 ID 没有默认值，产品展示名也不一定是接口 ID。进入项目根目录，在 Bash 或 zsh 中设置：

```sh
export GPTZZZ_BASE_URL='https://gptzzz.ai/v1'
export GPTZZZ_MODEL='替换为账号中的模型ID'
printf 'GPTZZZ API Key: '
read -r -s GPTZZZ_API_KEY
printf '\n'
export GPTZZZ_API_KEY

python3 scripts/chat.py --prompt '用一句话解释 API 中转站'
```

静默输入可以避免把密钥直接写进这条命令的历史记录，但环境变量仍需妥善保管；不要开启会回显变量的 shell 跟踪。不要将密钥写进源文件、提交到 Git 或贴进反馈截图。

Base URL 停在 `/v1`，目标是 `POST https://gptzzz.ai/v1/chat/completions`。请求使用 `Authorization: Bearer <API_KEY>` 和 `Content-Type: application/json`，最小正文如下，其中模型占位符由账号配置替换：

```json
{
  "model": "<MODEL_ID_FROM_ACCOUNT>",
  "messages": [
    {"role": "user", "content": "用一句话解释 API 中转站"}
  ],
  "stream": false
}
```

先不加入历史对话、工具或其他生成参数，让问题范围收敛到地址、鉴权、模型和消息结构。把完整接口路径填进 Base URL，可能造成重复拼接。

**2. 验证输出，而不只看进程结束**

先确认请求是否获得正常 HTTP 响应，再检查 JSON 是否包含可用结果。对本文的普通文本任务，应检查 `choices[0].message.content` 是否有文字、内容是否回应问题，并查看结束原因；`length` 表示输出触及限制，不能当成完整回答验收。HTTP 成功但结构异常，应单独记录。

当前示例 CLI 只输出文字结果或简要错误，不展示结束原因、`model`、`usage` 或请求 ID。上述扩展验收需要从账户调用记录查看，或在受控环境中扩展脱敏采集；没有采集的字段应记为“未采集”，不能断言服务端没有返回。模型字段可能使用别名，不能单靠名称证明上游来源；用量字段也不等同于实际账单。

**3. 一次只扩大一个变量**

基线成立后，再逐项增加提示词长度、对话轮数或业务输入，每次保留前一版请求作对照。非流式文本成功不能证明流式、工具调用、其他资源路径同样可用，也不宜立即提高并发。

需要辅助查询模型时，可运行：

```sh
python3 scripts/list_models.py
```

该辅助入口对应 `GET /v1/models`，依据是[站方错误码文档](https://gptzzz.ai/docs/api-error-codes/)中的建议，**尚未用真实账号实测**。若失败，回到控制台核对模型 ID 与权限，不要因此推断整个聊天服务不可用。

**4. 留下可复现的请求日志**

记录时间与时区、脚本版本、脱敏后的最终 URL、模型 ID、HTTP 状态、耗时、结束原因和可用的请求 ID。提示词涉及业务数据时，只留复现必需的脱敏片段；日志不保存 Authorization。遇到失败时同时记录是否已收到响应头、部分正文以及是否曾重发，便于按[排错教程](troubleshooting.md)继续定位。
