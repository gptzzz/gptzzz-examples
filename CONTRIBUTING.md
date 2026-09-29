# Contributing / 参与贡献

Issues and pull requests are welcome, especially when a tool changes its config
format or an example stops working. 欢迎提 Issue 和 PR，尤其是某个工具改了配置格式、某个示例跑不通的时候。

## Before you open an issue / 提 Issue 之前

- Run `bash examples/selftest.sh` and paste its output. It never prints the key.
  先跑一遍 `bash examples/selftest.sh`，把输出贴上来；它不会打印 key。
- Remove API keys, `Authorization` headers and private prompts from anything you paste.
  贴任何日志之前，删掉 key、`Authorization` 头和私密提示词。
- Say which example, which runtime version (`python3 --version`, `node --version`,
  `codex --version`) and the date. 写清是哪个示例、运行时版本和日期。

## Pull requests / 提 PR

1. One change per PR. 一个 PR 只做一件事。
2. `make lint` and `make test` must pass. Both are offline and need no key.
   `make lint` 和 `make test` 必须通过，两者都离线运行，不需要 key。
3. A new example needs a route in `tests/mock_gateway.py` and a test in
   `tests/test_examples.py`, and must read the key only from `GPTZZZ_API_KEY`.
   新示例要在 mock 网关里加对应接口、在 `tests/test_examples.py` 里加测试，并且只从 `GPTZZZ_API_KEY` 读 key。
4. Changing the compatibility table in `README.md`? Add a row to
   `docs/compatibility-log.md` with the date and what you ran against the real
   endpoint. Mock-gateway results do not count.
   改 README 的兼容性表，要在 `docs/compatibility-log.md` 里加一行真实复测记录；mock 网关的结果不算。
5. No prices, discount figures or referral links. 不写价格、折扣数字和邀请链接。

By contributing you agree that your contribution is licensed under the MIT License.
