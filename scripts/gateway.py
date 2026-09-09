"""Small standard-library client for a Chat Completions compatible gateway.

No request is retried automatically. Redirects are deliberately refused so that
an Authorization header cannot be forwarded to another endpoint.
"""

import ipaddress
import http.client
import json
import math
import os
import socket
from typing import List, Mapping, Optional
from urllib import error, parse, request


DEFAULT_BASE_URL = "https://gptzzz.ai/v1"
DEFAULT_TIMEOUT = 30.0
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class GatewayError(Exception):
    """An error message safe to display without response bodies or credentials."""


def positive_timeout(value: str) -> float:
    """Parse a finite timeout in seconds; also usable as an argparse type."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("timeout 必须为有限正数（秒）。") from None
    if not math.isfinite(number) or number <= 0:
        raise ValueError("timeout 必须为有限正数（秒）。")
    return number


def normalize_base_url(value: str) -> str:
    """Validate a base URL, allowing plain HTTP only for local loopback tests."""
    if not isinstance(value, str) or not value.strip():
        raise GatewayError("GPTZZZ_BASE_URL 不能为空。")
    value = value.strip()
    if any(character.isspace() or ord(character) < 32 for character in value):
        raise GatewayError("GPTZZZ_BASE_URL 不能包含空白或控制字符。")
    try:
        parts = parse.urlsplit(value)
        host = parts.hostname
        port = parts.port
    except ValueError:
        raise GatewayError("GPTZZZ_BASE_URL 格式无效，请检查主机和端口。") from None
    if not host or parts.scheme not in ("http", "https"):
        raise GatewayError("GPTZZZ_BASE_URL 必须是完整 HTTPS 地址。")
    if parts.username is not None or parts.password is not None:
        raise GatewayError("GPTZZZ_BASE_URL 不能包含用户名或密码。")
    if "?" in value or "#" in value:
        raise GatewayError("GPTZZZ_BASE_URL 不能包含查询参数或片段。")
    if port is not None and port == 0:
        raise GatewayError("GPTZZZ_BASE_URL 的端口必须大于 0。")
    if parts.scheme == "http":
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = host.lower() == "localhost"
        if not is_loopback:
            raise GatewayError("HTTP 仅允许 loopback 本地测试；远程地址必须使用 HTTPS。")
    path = parse.unquote(parts.path).rstrip("/").lower()
    if path.endswith("/chat/completions"):
        raise GatewayError("GPTZZZ_BASE_URL 应为 API 根路径，不能包含 /chat/completions。")
    return value.rstrip("/")


def model_from_env(environ: Optional[Mapping[str, str]] = None) -> str:
    """Return the explicitly configured model. There is no model default."""
    values = os.environ if environ is None else environ
    model = values.get("GPTZZZ_MODEL", "").strip()
    if not model:
        raise GatewayError("请设置 GPTZZZ_MODEL；先运行 list_models.py 获取可用模型 ID。")
    return model


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_error_message(status: int) -> str:
    if 300 <= status < 400:
        hint = "已拒绝 HTTP 重定向，请检查 GPTZZZ_BASE_URL 是否为正确的 API 根地址。"
    elif status == 401:
        hint = "请检查 GPTZZZ_API_KEY 是否有效。"
    elif status == 403:
        hint = "请检查账户、API Key 和模型的访问权限。"
    elif status == 404:
        hint = "请检查 GPTZZZ_BASE_URL、接口路径和模型 ID。"
    elif status in (400, 422):
        hint = "请检查模型 ID 和请求参数是否受该接口支持。"
    elif status == 429:
        hint = "请检查账户额度和速率限制；未自动重试。"
    elif status in (408, 504):
        hint = "请求超时；服务端可能已经处理请求，重新发送前请核对用量。"
    elif 500 <= status < 600:
        hint = "服务端暂时异常；未自动重试，重新发送前请核对用量。"
    else:
        hint = "请检查服务状态与账户配置；未自动重试。"
    return "HTTP {}：{}".format(status, hint)


class GatewayClient:
    """A single-attempt client; successful output is returned, never logged."""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL,
                 timeout: float = DEFAULT_TIMEOUT):
        if not isinstance(api_key, str) or not api_key.strip():
            raise GatewayError("请设置 GPTZZZ_API_KEY。")
        api_key = api_key.strip()
        if any(ord(character) < 33 or ord(character) > 126 for character in api_key):
            raise GatewayError("GPTZZZ_API_KEY 格式无效，不能包含空白或非 ASCII 字符。")
        self._api_key = api_key
        self.base_url = normalize_base_url(base_url)
        try:
            self.timeout = positive_timeout(timeout)
        except ValueError as exc:
            raise GatewayError(str(exc)) from None
        self._opener = request.build_opener(_NoRedirect())

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None,
                 timeout: float = DEFAULT_TIMEOUT):
        values = os.environ if environ is None else environ
        return cls(values.get("GPTZZZ_API_KEY", ""),
                   values.get("GPTZZZ_BASE_URL", DEFAULT_BASE_URL), timeout)

    def _request_json(self, path: str, payload=None):
        headers = {"Authorization": "Bearer " + self._api_key,
                   "Accept": "application/json"}
        body = None
        method = "GET"
        if payload is not None:
            method = "POST"
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(self.base_url + path, data=body,
                              headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except error.HTTPError as exc:
            status = exc.code
            exc.close()
            raise GatewayError(_http_error_message(status)) from None
        except (TimeoutError, socket.timeout):
            raise GatewayError("请求超时；未自动重试。服务端可能已处理请求，重新发送前请核对用量。") from None
        except error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise GatewayError("请求超时；未自动重试。服务端可能已处理请求，重新发送前请核对用量。") from None
            raise GatewayError("网络连接失败，请检查网络、DNS、TLS 证书及 GPTZZZ_BASE_URL；未自动重试。") from None
        except (OSError, ValueError, UnicodeError, http.client.HTTPException):
            raise GatewayError("请求无法完成，请检查网络和 API 地址配置；未自动重试。") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise GatewayError("响应超过示例客户端的 8 MiB 限制；未自动重试。")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            raise GatewayError("服务返回了无效 JSON；未输出响应正文，请检查接口兼容性。") from None
        if not isinstance(result, dict):
            raise GatewayError("服务返回的 JSON 应为对象，请检查接口兼容性。")
        return result

    def chat(self, prompt: str, model: str) -> str:
        if not isinstance(model, str) or not model.strip():
            raise GatewayError("模型 ID 不能为空；请设置 GPTZZZ_MODEL。")
        if not isinstance(prompt, str) or not prompt.strip():
            raise GatewayError("--prompt 不能为空。")
        result = self._request_json("/chat/completions", {
            "model": model.strip(),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        })
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices:
            raise GatewayError("响应缺少非空 choices 数组，请检查模型及接口兼容性。")
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise GatewayError("响应缺少非空文本 content；本示例仅处理文本回复，不处理工具调用或多模态内容。")
        return content

    def list_models(self) -> List[str]:
        result = self._request_json("/models")
        data = result.get("data")
        if not isinstance(data, list) or not data:
            raise GatewayError("响应缺少非空 data 数组，未取得可用模型 ID。")
        models = []
        for item in data:
            model_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(model_id, str) or not model_id.strip():
                raise GatewayError("模型列表包含无效 ID，请检查接口兼容性。")
            models.append(model_id)
        return models
