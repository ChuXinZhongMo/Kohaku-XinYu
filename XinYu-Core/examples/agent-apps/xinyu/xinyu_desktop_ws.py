from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import websockets
from websockets.exceptions import ConnectionClosed

from xinyu_desktop_events import (
    DESKTOP_EVENT_VERSION,
    CursorExpiredError,
    DesktopEventBus,
    DesktopEventSubscription,
    render_replay_unavailable_event,
)


LOGGER = logging.getLogger("xinyu.desktop.ws")
DEFAULT_DESKTOP_WS_HOST = "127.0.0.1"
DEFAULT_DESKTOP_WS_PORT = 8766
DEFAULT_DESKTOP_WS_PATH = "/desktop/events"
DEFAULT_REPLAY_LIMIT = 500
DEFAULT_MAX_WS_MESSAGE_BYTES = 512 * 1024


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)


def render_stream_ready_event(
    *,
    since_accepted: bool,
    replayed_count: int,
    latest_event_id: str,
) -> dict[str, Any]:
    return {
        "id": f"evt-stream-ready-{int(time.time() * 1000)}",
        "type": "desktop.event_stream.ready",
        "version": DESKTOP_EVENT_VERSION,
        "ts": _now_iso(),
        "source": "core",
        "privacy": "internal_summary",
        "payload": {
            "sinceAccepted": bool(since_accepted),
            "replayedCount": max(0, int(replayed_count)),
            "latestEventId": latest_event_id or "none",
        },
    }


class DesktopWSServer:
    """Expose the XinYu desktop event bus as a loopback WebSocket stream."""

    def __init__(
        self,
        *,
        bus: DesktopEventBus,
        host: str = DEFAULT_DESKTOP_WS_HOST,
        port: int = DEFAULT_DESKTOP_WS_PORT,
        path: str = DEFAULT_DESKTOP_WS_PATH,
        token: str = "",
        replay_limit: int = DEFAULT_REPLAY_LIMIT,
        ping_interval: float | None = 20,
        ping_timeout: float | None = 20,
        max_size: int | None = DEFAULT_MAX_WS_MESSAGE_BYTES,
    ) -> None:
        self.bus = bus
        self.host = host
        self.port = port
        self.path = path if path.startswith("/") else f"/{path}"
        self.token = token or ""
        self.replay_limit = max(0, replay_limit)
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_size = max_size
        self.server: Any | None = None

    @property
    def bound_port(self) -> int:
        if self.server is None:
            return self.port
        sockets = getattr(self.server, "sockets", None) or ()
        if not sockets:
            return self.port
        try:
            return int(sockets[0].getsockname()[1])
        except (IndexError, OSError, TypeError, ValueError):
            return self.port

    async def start(self) -> None:
        if self.server is not None:
            return
        self.server = await websockets.serve(
            self.handler,
            self.host,
            self.port,
            ping_interval=self.ping_interval,
            ping_timeout=self.ping_timeout,
            max_size=self.max_size,
        )
        LOGGER.info("XinYu desktop event stream listening on ws://%s:%s%s", self.host, self.bound_port, self.path)

    async def stop(self) -> None:
        if self.server is None:
            return
        self.server.close()
        await self.server.wait_closed()
        self.server = None
        LOGGER.info("XinYu desktop event stream stopped")

    async def handler(self, websocket: Any, path: str | None = None) -> None:
        request_path = self._connection_path(websocket, path)
        parsed = urlparse(request_path)
        if parsed.path != self.path:
            await websocket.close(code=4004, reason="Not Found")
            return

        query = parse_qs(parsed.query)
        if not self._authorized(websocket, query):
            LOGGER.warning("Desktop WS unauthorized access attempt")
            await websocket.close(code=4003, reason="Unauthorized")
            return

        since = self._first_query_value(query, "since")
        subscription: DesktopEventSubscription | None = None
        try:
            subscription = await self.bus.subscribe()
            await self._send_initial_stream_state(websocket, since)
            await self._live_push_loop(websocket, subscription)
        except ConnectionClosed:
            LOGGER.info("Desktop Shell disconnected")
        except Exception as exc:
            LOGGER.exception("Desktop WS internal error: %s", exc)
            await self._close_internal_error(websocket)
        finally:
            if subscription is not None:
                await subscription.close()

    async def _send_initial_stream_state(self, websocket: Any, since: str) -> None:
        latest_event_id = await self.bus.latest_event_id()
        if since:
            try:
                missed_events = await self.bus.replay_since(since, limit=self.replay_limit)
            except CursorExpiredError as exc:
                await self._send_json(websocket, render_replay_unavailable_event(since, reason=exc.reason))
                await self._send_json(
                    websocket,
                    render_stream_ready_event(
                        since_accepted=False,
                        replayed_count=0,
                        latest_event_id=latest_event_id,
                    ),
                )
                return

            await self._send_json(
                websocket,
                render_stream_ready_event(
                    since_accepted=True,
                    replayed_count=len(missed_events),
                    latest_event_id=str(missed_events[-1]["id"]) if missed_events else latest_event_id or since,
                ),
            )
            for event in missed_events:
                await self._send_json(websocket, event)
            return

        await self._send_json(
            websocket,
            render_stream_ready_event(
                since_accepted=False,
                replayed_count=0,
                latest_event_id=latest_event_id,
            ),
        )

    async def _live_push_loop(self, websocket: Any, subscription: DesktopEventSubscription) -> None:
        wait_closed = getattr(websocket, "wait_closed", None)
        closed_task = asyncio.create_task(wait_closed()) if callable(wait_closed) else None
        try:
            while True:
                event_task = asyncio.create_task(subscription.next())
                wait_set = {event_task}
                if closed_task is not None:
                    wait_set.add(closed_task)
                done, pending = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED)
                if closed_task is not None and closed_task in done:
                    event_task.cancel()
                    await self._quiet_cancel(event_task)
                    return
                if event_task in done:
                    event = event_task.result()
                    await self._send_json(websocket, event)
                for pending_task in pending:
                    if pending_task is not closed_task:
                        pending_task.cancel()
                        await self._quiet_cancel(pending_task)
        finally:
            if closed_task is not None:
                closed_task.cancel()
                await self._quiet_cancel(closed_task)

    async def _send_json(self, websocket: Any, payload: dict[str, Any]) -> None:
        await websocket.send(_json_dumps(payload))

    async def _close_internal_error(self, websocket: Any) -> None:
        try:
            await websocket.close(code=1011, reason="Internal Error")
        except ConnectionClosed:
            pass

    @staticmethod
    async def _quiet_cancel(task: asyncio.Task[Any]) -> None:
        try:
            await task
        except (asyncio.CancelledError, ConnectionClosed):
            pass

    def _authorized(self, websocket: Any, query: dict[str, list[str]]) -> bool:
        if not self.token:
            return True
        return self._query_token(query) == self.token or self._authorization_bearer(websocket) == self.token

    @staticmethod
    def _query_token(query: dict[str, list[str]]) -> str:
        for key in ("token", "bridge_token", "xinyu_bridge_token"):
            value = DesktopWSServer._first_query_value(query, key)
            if value:
                return value
        return ""

    @staticmethod
    def _authorization_bearer(websocket: Any) -> str:
        headers = DesktopWSServer._request_headers(websocket)
        if not headers:
            return ""
        try:
            value = str(headers.get("Authorization") or headers.get("authorization") or "")
        except AttributeError:
            return ""
        if value.lower().startswith("bearer "):
            return value[7:].strip()
        return ""

    @staticmethod
    def _request_headers(websocket: Any) -> Any:
        request = getattr(websocket, "request", None)
        headers = getattr(request, "headers", None)
        if headers is not None:
            return headers
        return getattr(websocket, "request_headers", None)

    @staticmethod
    def _connection_path(websocket: Any, path: str | None) -> str:
        if path:
            return path
        request = getattr(websocket, "request", None)
        request_path = getattr(request, "path", None)
        if request_path:
            return str(request_path)
        direct_path = getattr(websocket, "path", None)
        return str(direct_path or "/")

    @staticmethod
    def _first_query_value(query: dict[str, list[str]], key: str) -> str:
        values = query.get(key) or []
        return str(values[0]).strip() if values else ""
