#!/usr/bin/env python3
"""Send one non-streaming text request. Requires GPTZZZ_API_KEY and GPTZZZ_MODEL."""

import argparse
import sys

try:
    from .gateway import DEFAULT_TIMEOUT, GatewayClient, GatewayError, model_from_env, positive_timeout
except ImportError:
    from gateway import DEFAULT_TIMEOUT, GatewayClient, GatewayError, model_from_env, positive_timeout


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="发送一次文本请求；不自动重试。")
    parser.add_argument("--prompt", required=True, help="发送给模型的文本。")
    parser.add_argument("--timeout", type=positive_timeout, default=DEFAULT_TIMEOUT,
                        help="网络操作超时秒数，必须为有限正数（默认 30）。")
    args = parser.parse_args(argv)
    try:
        model = model_from_env()
        client = GatewayClient.from_env(timeout=args.timeout)
        print(client.chat(args.prompt, model))
        return 0
    except GatewayError as exc:
        print("错误：{}".format(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("请求已中断；未自动重试，重新发送前请核对用量。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
