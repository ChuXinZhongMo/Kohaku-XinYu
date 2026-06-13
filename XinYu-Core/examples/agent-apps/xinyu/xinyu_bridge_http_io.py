from __future__ import annotations

import asyncio
import json
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs

from xinyu_bridge_auth import bridge_request_authorized


class BridgeHTTPRequestError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def query_payload(parsed: Any) -> dict[str, Any]:
    return {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}


def request_authorized(headers: Any, bridge_token: str) -> bool:
    return bridge_request_authorized(headers, bridge_token)


def read_json_body(handler: Any, *, max_body_bytes: int) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length <= 0:
        raise BridgeHTTPRequestError(HTTPStatus.BAD_REQUEST, "empty request body")
    if content_length > max_body_bytes:
        raise BridgeHTTPRequestError(
            HTTPStatus.PAYLOAD_TOO_LARGE,
            f"request body is too large: {content_length} bytes",
        )
    raw = handler.rfile.read(content_length)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise BridgeHTTPRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return data


def send_json_response(handler: Any, status: HTTPStatus, data: dict[str, Any]) -> None:
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status.value, status.phrase)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Connection", "close")
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except OSError as exc:
        print(f"[xinyu_core_bridge] client disconnected before response body was sent: {exc}", flush=True)


def send_html_response(handler: Any, status: HTTPStatus, html: str) -> None:
    body = html.encode("utf-8")
    handler.send_response(status.value, status.phrase)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Connection", "close")
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except OSError as exc:
        print(f"[xinyu_core_bridge] client disconnected before HTML body was sent: {exc}", flush=True)


def run_on_loop(loop: asyncio.AbstractEventLoop, coro: Any, *, timeout: int) -> Any:
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        return future.result(timeout=timeout)
    except TimeoutError:
        future.cancel()
        raise
