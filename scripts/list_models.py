#!/usr/bin/env python3
"""Print model IDs returned by GET /models; does not require GPTZZZ_MODEL."""

import argparse
import sys

try:
    from .gateway import DEFAULT_TIMEOUT, GatewayClient, GatewayError, positive_timeout
except ImportError:
    from gateway import DEFAULT_TIMEOUT, GatewayClient, GatewayError, positive_timeout


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="列出当前 API Key 可见的模型 ID；不自动重试。")
    parser.add_argument("--timeout", type=positive_timeout, default=DEFAULT_TIMEOUT,
                        help="网络操作超时秒数，必须为有限正数（默认 30）。")
    args = parser.parse_args(argv)
    try:
        client = GatewayClient.from_env(timeout=args.timeout)
        print("\n".join(client.list_models()))
        return 0
    except GatewayError as exc:
        print("错误：{}".format(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("请求已中断；未自动重试。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
