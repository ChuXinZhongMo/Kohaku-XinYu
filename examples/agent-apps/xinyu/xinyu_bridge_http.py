from __future__ import annotations

import asyncio
import hmac
import json
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


class XinYuBridgeHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        *,
        runtime: Any,
        loop: asyncio.AbstractEventLoop,
        bridge_token: str,
        max_body_bytes: int,
        request_timeout_seconds: int,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.runtime = runtime
        self.loop = loop
        self.bridge_token = bridge_token
        self.max_body_bytes = max_body_bytes
        self.request_timeout_seconds = request_timeout_seconds


class XinYuBridgeRequestHandler(BaseHTTPRequestHandler):
    server: XinYuBridgeHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        if route not in {"/health", "/probe", "/proactive"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        if route in {"/probe", "/proactive"} and not self._is_authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return

        try:
            if route == "/health":
                health_snapshot = getattr(self.server.runtime, "health_snapshot", None)
                if callable(health_snapshot):
                    data = health_snapshot()
                else:
                    data = self._run_on_loop(self.server.runtime.health(), timeout=10)
            elif route == "/probe":
                payload = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
                data = self._run_on_loop(self.server.runtime.probe(payload), timeout=10)
            else:
                payload = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
                payload.setdefault("claim", "false")
                data = self._run_on_loop(self.server.runtime.proactive(payload), timeout=10)
        except Exception as exc:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": type(exc).__name__, "message": str(exc)},
            )
            return
        self._send_json(HTTPStatus.OK, data)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route not in {
            "/chat",
            "/probe",
            "/proactive",
            "/proactive/ack",
            "/qq/outbox/claim",
            "/qq/outbox/ack",
            "/learning/ingest",
            "/learning/study",
            "/learning/observe",
            "/package/install",
            "/codex/execute",
        }:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        if route in {"/codex/execute", "/package/install", "/qq/outbox/claim", "/qq/outbox/ack"} and not self.server.bridge_token:
            self._send_json(
                HTTPStatus.UNAUTHORIZED,
                {
                    "accepted": False,
                    "reply": "",
                    "notes": [f"{route.strip('/').replace('/', '_')}_requires_bridge_token"],
                },
            )
            return

        if not self._is_authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return

        try:
            payload = self._read_json_body()
            if route == "/probe":
                result = self._run_on_loop(self.server.runtime.probe(payload), timeout=10)
            elif route == "/proactive":
                result = self._run_on_loop(self.server.runtime.proactive(payload), timeout=10)
            elif route == "/proactive/ack":
                result = self._run_on_loop(self.server.runtime.proactive_ack(payload), timeout=10)
            elif route == "/qq/outbox/claim":
                fast_claim = getattr(self.server.runtime, "qq_outbox_claim_fast", None)
                if callable(fast_claim):
                    result = fast_claim(payload)
                else:
                    result = self._run_on_loop(self.server.runtime.qq_outbox_claim(payload), timeout=10)
            elif route == "/qq/outbox/ack":
                fast_ack = getattr(self.server.runtime, "qq_outbox_ack_fast", None)
                if callable(fast_ack):
                    result = fast_ack(payload)
                else:
                    result = self._run_on_loop(self.server.runtime.qq_outbox_ack(payload), timeout=10)
            elif route == "/learning/ingest":
                result = self._run_on_loop(
                    self.server.runtime.learning_ingest(payload),
                    timeout=self.server.request_timeout_seconds,
                )
            elif route == "/learning/study":
                result = self._run_on_loop(
                    self.server.runtime.learning_study(payload),
                    timeout=self.server.request_timeout_seconds,
                )
            elif route == "/learning/observe":
                result = self._run_on_loop(
                    self.server.runtime.learning_observe(payload),
                    timeout=self.server.request_timeout_seconds,
                )
            elif route == "/package/install":
                result = self._run_on_loop(
                    self.server.runtime.package_install(payload),
                    timeout=self.server.request_timeout_seconds,
                )
            elif route == "/codex/execute":
                result = self._run_on_loop(
                    self.server.runtime.codex_execute(payload),
                    timeout=self.server.request_timeout_seconds,
                )
            else:
                result = self._run_on_loop(
                    self.server.runtime.chat(payload),
                    timeout=self.server.request_timeout_seconds,
                )
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"accepted": False, "reply": "", "notes": ["invalid_json"]})
            return
        except TimeoutError:
            self._send_json(
                HTTPStatus.GATEWAY_TIMEOUT,
                {"accepted": False, "reply": "", "notes": ["bridge_request_timeout"]},
            )
            return
        except Exception as exc:
            status = getattr(exc, "status", None)
            message = getattr(exc, "message", "")
            if isinstance(status, HTTPStatus) and message:
                self._send_json(status, {"accepted": False, "reply": "", "notes": [message]})
                return
            print("[xinyu_core_bridge] request failed", flush=True)
            traceback.print_exc()
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"accepted": False, "reply": "", "notes": [f"{type(exc).__name__}: {exc}"]},
            )
            return

        self._send_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: Any) -> None:
        message = format % args
        if 'POST /qq/outbox/claim ' in message and " 200 " in message:
            return
        print(f"[xinyu_core_bridge] {self.address_string()} - {message}", flush=True)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            raise _BridgeHTTPRequestError(HTTPStatus.BAD_REQUEST, "empty request body")
        if content_length > self.server.max_body_bytes:
            raise _BridgeHTTPRequestError(
                HTTPStatus.PAYLOAD_TOO_LARGE,
                f"request body is too large: {content_length} bytes",
            )
        raw = self.rfile.read(content_length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise _BridgeHTTPRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
        return data

    def _send_json(self, status: HTTPStatus, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value, status.phrase)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError as exc:
            print(f"[xinyu_core_bridge] client disconnected before response body was sent: {exc}", flush=True)

    def _is_authorized(self) -> bool:
        token = self.server.bridge_token
        if not token:
            return True
        bearer = self.headers.get("Authorization", "")
        header_token = self.headers.get("X-XinYu-Bridge-Token", "")
        auth_token = ""
        if bearer.lower().startswith("bearer "):
            auth_token = bearer[7:].strip()
        return hmac.compare_digest(token, auth_token) or hmac.compare_digest(token, header_token)

    def _run_on_loop(self, coro: Any, *, timeout: int) -> Any:
        future = asyncio.run_coroutine_threadsafe(coro, self.server.loop)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise


class _BridgeHTTPRequestError(RuntimeError):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
