from __future__ import annotations

import asyncio
import json
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from xinyu_bridge_auth import bridge_request_authorized


DESKTOP_GET_ROUTES = {
    "/desktop/snapshot",
    "/desktop/events/recent",
    "/desktop/proactive/inbox",
    "/desktop/chat/recent",
    "/desktop/memory/recent",
    "/desktop/memory/growth-candidates",
}
EXTERNAL_GET_ROUTES = {
    "/external/plugins",
}
TURN_GET_ROUTES = {
    "/turn/current",
}
TURN_POST_ROUTES = {
    "/turn/cancel",
    "/turn/retry-lightweight",
    "/turn/skip-sidecar",
    "/turn/continue",
    "/turn/status-message",
}
LIFE_TICKET_PREFIX = "/life/metabolism/tickets"


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
        if (
            route not in {"/health", "/probe", "/proactive"}
            and route not in DESKTOP_GET_ROUTES
            and route not in EXTERNAL_GET_ROUTES
            and route not in TURN_GET_ROUTES
            and not route.startswith(LIFE_TICKET_PREFIX)
        ):
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        if (
            route in {"/probe", "/proactive"}
            or route in DESKTOP_GET_ROUTES
            or route in EXTERNAL_GET_ROUTES
            or route in TURN_GET_ROUTES
            or route.startswith(LIFE_TICKET_PREFIX)
        ) and not self._is_authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return

        try:
            payload = self._query_payload(parsed)
            if route == "/health":
                health_snapshot = getattr(self.server.runtime, "health_snapshot", None)
                if callable(health_snapshot):
                    data = health_snapshot()
                else:
                    data = self._run_on_loop(self.server.runtime.health(), timeout=10)
            elif route == "/probe":
                data = self._run_on_loop(self.server.runtime.probe(payload), timeout=10)
            elif route == "/proactive":
                payload.setdefault("claim", "false")
                data = self._run_on_loop(self.server.runtime.proactive(payload), timeout=10)
            elif route == "/desktop/snapshot":
                data = self._run_on_loop(self.server.runtime.desktop_snapshot(payload), timeout=5)
            elif route == "/desktop/events/recent":
                data = self._run_on_loop(self.server.runtime.desktop_events_recent(payload), timeout=5)
            elif route == "/desktop/proactive/inbox":
                data = self._run_on_loop(self.server.runtime.desktop_proactive_inbox(payload), timeout=5)
            elif route == "/desktop/chat/recent":
                data = self._run_on_loop(self.server.runtime.desktop_chat_recent(payload), timeout=5)
            elif route == "/desktop/memory/growth-candidates":
                data = self._run_on_loop(self.server.runtime.desktop_memory_growth_candidates(payload), timeout=5)
            elif route == "/external/plugins":
                data = self._run_on_loop(self.server.runtime.external_plugin_manifest(payload), timeout=5)
            elif route == "/turn/current":
                data = self._run_on_loop(self.server.runtime.turn_current(payload), timeout=5)
            elif route == LIFE_TICKET_PREFIX:
                data = self._run_on_loop(self.server.runtime.life_metabolism_ticket_list(payload), timeout=5)
            elif route.startswith(f"{LIFE_TICKET_PREFIX}/"):
                ticket_id = route[len(LIFE_TICKET_PREFIX) + 1 :]
                payload["ticket_id"] = ticket_id
                data = self._run_on_loop(self.server.runtime.life_metabolism_ticket_get(payload), timeout=5)
            else:
                data = self._run_on_loop(self.server.runtime.desktop_memory_recent(payload), timeout=5)
        except TimeoutError:
            self._send_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"ok": False, "error": "core_state_retrieval_timeout"},
            )
            return
        except Exception as exc:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": type(exc).__name__, "message": str(exc)},
            )
            return
        self._send_json(HTTPStatus.OK, data)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        post_routes = {
            "/chat",
            "/probe",
            "/proactive",
            "/proactive/ack",
            "/desktop/proactive/ack",
            "/desktop/self-action/approval",
            "/qq/outbox/claim",
            "/qq/outbox/ack",
            "/internal/message/ack",
            "/internal/message/drop",
            "/review/inbox/command",
            "/review/goldmark/mark_request",
            "/learning/ingest",
            "/learning/study",
            "/learning/observe",
            "/sticker/import",
            "/package/install",
            "/codex/execute",
            "/external/call",
            "/external/plugins/config",
            "/external/plugins/install",
        }
        post_routes.update(TURN_POST_ROUTES)
        if route not in post_routes and not self._is_life_ticket_action_route(route):
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        if route in {
            "/codex/execute",
            "/package/install",
            "/qq/outbox/claim",
            "/qq/outbox/ack",
            "/internal/message/ack",
            "/internal/message/drop",
            "/review/inbox/command",
            "/review/goldmark/mark_request",
            "/sticker/import",
            "/external/call",
            "/external/plugins/config",
            "/external/plugins/install",
        } and not self.server.bridge_token:
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
            elif self._is_life_ticket_action_route(route):
                ticket_id, action = self._life_ticket_action(route)
                payload["ticket_id"] = ticket_id
                if action == "approve":
                    result = self._run_on_loop(self.server.runtime.life_metabolism_ticket_approve(payload), timeout=10)
                elif action == "reject":
                    result = self._run_on_loop(self.server.runtime.life_metabolism_ticket_reject(payload), timeout=10)
                else:
                    result = self._run_on_loop(self.server.runtime.life_metabolism_ticket_cancel(payload), timeout=10)
            elif route == "/proactive":
                result = self._run_on_loop(self.server.runtime.proactive(payload), timeout=10)
            elif route == "/proactive/ack":
                result = self._run_on_loop(self.server.runtime.proactive_ack(payload), timeout=10)
            elif route == "/desktop/proactive/ack":
                result = self._run_on_loop(self.server.runtime.desktop_proactive_ack(payload), timeout=10)
            elif route == "/desktop/self-action/approval":
                result = self._run_on_loop(self.server.runtime.desktop_self_action_approval(payload), timeout=10)
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
            elif route == "/internal/message/ack":
                result = self._run_on_loop(self.server.runtime.message_ack(payload), timeout=10)
            elif route == "/internal/message/drop":
                result = self._run_on_loop(self.server.runtime.message_drop(payload), timeout=10)
            elif route == "/review/inbox/command":
                result = self._run_on_loop(self.server.runtime.review_inbox_command(payload), timeout=10)
            elif route == "/review/goldmark/mark_request":
                result = self._run_on_loop(self.server.runtime.goldmark_mark_request(payload), timeout=10)
                status_code = int(result.get("http_status") or HTTPStatus.OK.value)
                if status_code != HTTPStatus.OK.value:
                    self._send_json(HTTPStatus(status_code), result)
                    return
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
            elif route == "/sticker/import":
                result = self._run_on_loop(
                    self.server.runtime.sticker_import(payload),
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
            elif route == "/external/call":
                result = self._run_on_loop(
                    self.server.runtime.external_plugin_call(payload),
                    timeout=self.server.request_timeout_seconds,
                )
            elif route == "/external/plugins/config":
                result = self._run_on_loop(
                    self.server.runtime.external_plugin_config(payload),
                    timeout=10,
                )
            elif route == "/external/plugins/install":
                result = self._run_on_loop(
                    self.server.runtime.external_plugin_install(payload),
                    timeout=self.server.request_timeout_seconds,
                )
            elif route == "/turn/cancel":
                result = self._run_on_loop(self.server.runtime.turn_cancel(payload), timeout=10)
            elif route == "/turn/retry-lightweight":
                result = self._run_on_loop(self.server.runtime.turn_retry_lightweight(payload), timeout=10)
            elif route == "/turn/skip-sidecar":
                result = self._run_on_loop(self.server.runtime.turn_skip_sidecar(payload), timeout=10)
            elif route == "/turn/continue":
                result = self._run_on_loop(self.server.runtime.turn_continue(payload), timeout=10)
            elif route == "/turn/status-message":
                result = self._run_on_loop(self.server.runtime.turn_status_message(payload), timeout=10)
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

    def _is_life_ticket_action_route(self, route: str) -> bool:
        if not route.startswith(f"{LIFE_TICKET_PREFIX}/"):
            return False
        parts = route.strip("/").split("/")
        return len(parts) == 5 and parts[:3] == ["life", "metabolism", "tickets"] and parts[4] in {
            "approve",
            "reject",
            "cancel",
        }

    def _life_ticket_action(self, route: str) -> tuple[str, str]:
        parts = route.strip("/").split("/")
        return parts[3], parts[4]

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
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status.value, status.phrase)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError as exc:
            print(f"[xinyu_core_bridge] client disconnected before response body was sent: {exc}", flush=True)

    def _query_payload(self, parsed: Any) -> dict[str, Any]:
        return {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}

    def _is_authorized(self) -> bool:
        return bridge_request_authorized(self.headers, self.server.bridge_token)

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
