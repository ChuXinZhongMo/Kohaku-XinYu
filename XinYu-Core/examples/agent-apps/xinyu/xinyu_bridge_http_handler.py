from __future__ import annotations

import json
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from xinyu_bridge_http_dispatch import dispatch_get_route, dispatch_post_route
from xinyu_bridge_http_io import (
    BridgeHTTPRequestError,
    query_payload,
    read_json_body,
    request_authorized,
    run_on_loop,
    send_html_response,
    send_json_response,
)
from xinyu_bridge_voice_flags import (
    VOICE_FLAGS_PANEL_ROUTE,
    VOICE_FLAGS_STATE_ROUTE,
    VOICE_FLAGS_UPDATE_ROUTE,
    apply_voice_flags_update,
    read_voice_flags_state,
    render_voice_flags_panel_html,
)
from xinyu_bridge_http_routes import (
    get_route_requires_auth,
    is_known_get_route,
    is_known_post_route,
    is_life_ticket_action_route,
    is_life_ticket_get_route,
    life_ticket_action,
    post_route_requires_bridge_token,
)
from xinyu_bridge_http_server import XinYuBridgeHTTPServer


class XinYuBridgeRequestHandler(BaseHTTPRequestHandler):
    server: XinYuBridgeHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        if route == VOICE_FLAGS_PANEL_ROUTE:
            send_html_response(self, HTTPStatus.OK, render_voice_flags_panel_html())
            return
        if route == VOICE_FLAGS_STATE_ROUTE:
            self._send_json(HTTPStatus.OK, read_voice_flags_state())
            return
        if not is_known_get_route(route):
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return
        if get_route_requires_auth(route) and not self._is_authorized():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
            return

        try:
            data = dispatch_get_route(
                runtime=self.server.runtime,
                route=route,
                payload=self._query_payload(parsed),
                run_on_loop=self._run_on_loop,
            )
            if data is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
                return
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
        if route == VOICE_FLAGS_UPDATE_ROUTE:
            if not self._is_authorized():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "unauthorized"})
                return
            try:
                env_file = Path(getattr(self.server.runtime, "xinyu_dir", ".")) / "xinyu.local.env"
                result = apply_voice_flags_update(self._read_json_body(), env_file=env_file)
            except json.JSONDecodeError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_json"})
                return
            except Exception as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"ok": False, "error": type(exc).__name__, "message": str(exc)},
                )
                return
            self._send_json(HTTPStatus.OK, result)
            return
        if not is_known_post_route(route):
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
            return

        if post_route_requires_bridge_token(route) and not self.server.bridge_token:
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
            dispatched = dispatch_post_route(
                runtime=self.server.runtime,
                route=route,
                payload=self._read_json_body(),
                run_on_loop=self._run_on_loop,
                request_timeout_seconds=self.server.request_timeout_seconds,
            )
            if dispatched is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})
                return
            if dispatched.status != HTTPStatus.OK:
                self._send_json(dispatched.status, dispatched.data)
                return
            result = dispatched.data
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
                self._send_json(
                    status,
                    {"ok": False, "accepted": False, "reply": "", "error": message, "notes": [message]},
                )
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
        return is_life_ticket_action_route(route)

    def _life_ticket_action(self, route: str) -> tuple[str, str]:
        return life_ticket_action(route)

    def _is_life_ticket_get_route(self, route: str) -> bool:
        return is_life_ticket_get_route(route)

    def log_message(self, format: str, *args: Any) -> None:
        message = format % args
        if "POST /qq/outbox/claim " in message and " 200 " in message:
            return
        print(f"[xinyu_core_bridge] {self.address_string()} - {message}", flush=True)

    def _read_json_body(self) -> dict[str, Any]:
        return read_json_body(self, max_body_bytes=self.server.max_body_bytes)

    def _send_json(self, status: HTTPStatus, data: dict[str, Any]) -> None:
        send_json_response(self, status, data)

    def _query_payload(self, parsed: Any) -> dict[str, Any]:
        return query_payload(parsed)

    def _is_authorized(self) -> bool:
        return request_authorized(self.headers, self.server.bridge_token)

    def _run_on_loop(self, coro: Any, *, timeout: int) -> Any:
        return run_on_loop(self.server.loop, coro, timeout=timeout)


_BridgeHTTPRequestError = BridgeHTTPRequestError
