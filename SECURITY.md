# Security Policy

## Reporting a problem

Report security problems privately through **Security → Report a vulnerability**
on this repository, not in a public issue. Examples of what counts:

- an example or script that can print, log or leak the API key;
- a script that follows a redirect and sends the `Authorization` header to another host;
- a test or CI step that reaches the network or needs a real key.

请通过本仓库的 **Security → Report a vulnerability** 私下报告安全问题，不要发在公开 Issue 里。
报告里请用占位符代替真实的 key、`Authorization` 头、私有 Base URL 和未脱敏的提示词或回复。

We aim to reply within 5 working days.

## If a real key was exposed / key 泄露了怎么办

1. Revoke the key in the GPTZZZ console and create a new one. Deleting the file or
   the commit does not revoke it. / 立即在 GPTZZZ 控制台作废并新建 key；删除文件或提交不等于作废。
2. Check the key's recent usage for calls you did not make. / 检查这个 key 最近的用量有没有异常调用。
3. Remove public copies (issues, logs, screenshots, CI output). / 删除 Issue、日志、截图、CI 输出里的公开副本。

## How the examples handle the key

- Every example reads the key from the `GPTZZZ_API_KEY` environment variable only.
  There is no `--api-key` flag and nothing reads `.env` automatically.
- `examples/selftest.sh` passes the header to curl through a pipe (`-H @file`), so the
  key does not appear in the process list, and scrubs the key from anything it prints.
  Its bad-key check uses a hard-coded fake key, never yours.
- `examples/stdlib/` refuses HTTP redirects and never prints response bodies.
- The tests (`make test`) run against `tests/mock_gateway.py` on 127.0.0.1 with a fake
  key and assert that no example prints the key it was given. CI uses no secrets.

## Out of scope

Problems in the GPTZZZ service itself (report those through GPTZZZ support), in
Codex CLI, OpenCode or Cline, or anything that needs a malicious local administrator.
