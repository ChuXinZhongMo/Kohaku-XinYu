from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

import xinyu_desktop_ws
from xinyu_desktop_events import CursorExpiredError, DesktopEventBus
from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE,
    DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY,
    DESKTOP_EVENT_STREAM_REPLAY_EVENTS,
    DESKTOP_EVENT_STREAM_RUNTIME_ATTR,
    desktop_event_stream_readiness,
)
from xinyu_desktop_service import (
    DesktopService,
    desktop_event_stream_service_readiness,
)
from xinyu_desktop_ws import DesktopWSServer
from xinyu_serviceization_contracts import service_contract_by_id


def test_desktop_event_bus_replay_limit_and_expired_cursor_contract() -> None:
    async def scenario() -> None:
        bus = DesktopEventBus(loop=asyncio.get_running_loop(), max_events=3)
        await bus.publish("event.one", {"value": 1}, event_id="evt-1")
        await bus.publish("event.two", {"value": 2}, event_id="evt-2")
        await bus.publish("event.three", {"value": 3}, event_id="evt-3")

        assert [event["id"] for event in await bus.replay_since("evt-1")] == ["evt-2", "evt-3"]
        assert [event["id"] for event in await bus.replay_since("evt-1", limit=1)] == ["evt-2"]
        assert await bus.latest_event_id() == "evt-3"

        await bus.publish("event.four", {"value": 4}, event_id="evt-4")
        assert [event["id"] for event in await bus.recent(limit=3)] == ["evt-2", "evt-3", "evt-4"]
        with pytest.raises(CursorExpiredError) as caught:
            await bus.replay_since("evt-1")
        assert caught.value.cursor == "evt-1"
        assert caught.value.reason == "cursor_not_in_buffer"

    asyncio.run(scenario())


def test_desktop_event_bus_subscriber_backpressure_drops_oldest_and_keeps_newest() -> None:
    async def scenario() -> None:
        bus = DesktopEventBus(loop=asyncio.get_running_loop(), subscriber_queue_size=1)
        subscription = await bus.subscribe()

        await bus.publish("event.old", {"value": 1}, event_id="evt-old")
        await bus.publish("event.new", {"value": 2}, event_id="evt-new")

        assert await subscription.next() == {
            "id": "evt-new",
            "type": "event.new",
            "version": 1,
            "ts": (await bus.recent(limit=1))[0]["ts"],
            "source": "core",
            "privacy": "internal_summary",
            "payload": {"value": 2},
        }
        await subscription.close()

    asyncio.run(scenario())


class _WebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.closed: list[tuple[int, str]] = []
        self.request_headers: dict[str, str] = {}

    async def send(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    async def close(self, *, code: int, reason: str) -> None:
        self.closed.append((code, reason))


def test_desktop_ws_initial_stream_replays_since_cursor_before_live_events() -> None:
    async def scenario() -> None:
        bus = DesktopEventBus(loop=asyncio.get_running_loop())
        await bus.publish("event.one", {"value": 1}, event_id="evt-1")
        await bus.publish("event.two", {"value": 2}, event_id="evt-2")
        await bus.publish("event.three", {"value": 3}, event_id="evt-3")
        websocket = _WebSocket()
        server = DesktopWSServer(bus=bus, replay_limit=2)

        await server._send_initial_stream_state(websocket, "evt-1")

        assert [item["type"] for item in websocket.sent] == [
            "desktop.event_stream.ready",
            "event.two",
            "event.three",
        ]
        assert "desktop.event_stream.ready" in DESKTOP_EVENT_STREAM_REPLAY_EVENTS
        assert "desktop.event_replay.available" not in DESKTOP_EVENT_STREAM_REPLAY_EVENTS
        ready = websocket.sent[0]["payload"]
        assert ready == {"sinceAccepted": True, "replayedCount": 2, "latestEventId": "evt-3"}
        assert [item["id"] for item in websocket.sent[1:]] == ["evt-2", "evt-3"]

    asyncio.run(scenario())


def test_desktop_ws_initial_stream_reports_replay_unavailable_then_ready() -> None:
    async def scenario() -> None:
        bus = DesktopEventBus(loop=asyncio.get_running_loop(), max_events=1)
        await bus.publish("event.new", {"value": 2}, event_id="evt-new")
        websocket = _WebSocket()
        server = DesktopWSServer(bus=bus)

        await server._send_initial_stream_state(websocket, "evt-expired")

        assert [item["type"] for item in websocket.sent] == [
            "desktop.event_replay.unavailable",
            "desktop.event_stream.ready",
        ]
        assert tuple(item["type"] for item in websocket.sent) == DESKTOP_EVENT_STREAM_REPLAY_EVENTS
        assert websocket.sent[0]["payload"] == {
            "cursor": "evt-expired",
            "reason": "cursor_not_in_buffer",
            "recommendedAction": "refresh_snapshot",
        }
        assert websocket.sent[1]["payload"] == {
            "sinceAccepted": False,
            "replayedCount": 0,
            "latestEventId": "evt-new",
        }

    asyncio.run(scenario())


def test_desktop_ws_handler_rejects_wrong_path_before_subscribing() -> None:
    async def scenario() -> None:
        bus = DesktopEventBus(loop=asyncio.get_running_loop())
        websocket = _WebSocket()
        server = DesktopWSServer(bus=bus, path="/desktop/events")

        await server.handler(websocket, "/wrong-path")

        assert websocket.closed == [(4004, "Not Found")]
        assert websocket.sent == []
        assert await bus.snapshot() == {
            "version": 1,
            "max_events": 1000,
            "buffer_size": 0,
            "latest_event_id": "",
            "subscriber_count": 0,
        }

    asyncio.run(scenario())


def test_desktop_ws_handler_rejects_missing_or_wrong_token() -> None:
    async def scenario() -> None:
        bus = DesktopEventBus(loop=asyncio.get_running_loop())
        server = DesktopWSServer(bus=bus, token="secret")

        missing_token = _WebSocket()
        await server.handler(missing_token, "/desktop/events")
        wrong_token = _WebSocket()
        await server.handler(wrong_token, "/desktop/events?token=wrong")

        assert missing_token.closed == [(4003, "Unauthorized")]
        assert wrong_token.closed == [(4003, "Unauthorized")]
        assert await bus.snapshot() == {
            "version": 1,
            "max_events": 1000,
            "buffer_size": 0,
            "latest_event_id": "",
            "subscriber_count": 0,
        }

    asyncio.run(scenario())


def test_desktop_ws_auth_accepts_query_and_bearer_tokens() -> None:
    server = DesktopWSServer(bus=object(), token="secret")
    bearer_socket = _WebSocket()
    bearer_socket.request_headers["Authorization"] = "Bearer secret"

    assert server._authorized(_WebSocket(), {"token": ["secret"]}) is True
    assert server._authorized(_WebSocket(), {"bridge_token": ["secret"]}) is True
    assert server._authorized(_WebSocket(), {"xinyu_bridge_token": ["secret"]}) is True
    assert server._authorized(bearer_socket, {}) is True
    assert server._authorized(_WebSocket(), {"token": ["wrong"]}) is False


def test_desktop_ws_start_stop_are_idempotent(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Socket:
        def getsockname(self) -> tuple[str, int]:
            return ("127.0.0.1", 9876)

    class _Server:
        sockets = (_Socket(),)

        def close(self) -> None:
            calls.append(("close", None))

        async def wait_closed(self) -> None:
            calls.append(("wait_closed", None))

    async def serve(*args: object, **kwargs: object) -> _Server:
        calls.append(("serve", {"args": args, "kwargs": kwargs}))
        return _Server()

    async def scenario() -> None:
        monkeypatch.setattr(xinyu_desktop_ws.websockets, "serve", serve)
        bus = DesktopEventBus(loop=asyncio.get_running_loop())
        server = DesktopWSServer(bus=bus, host="127.0.0.1", port=0, path="/desktop/events")

        await server.start()
        await server.start()
        assert server.bound_port == 9876

        await server.stop()
        await server.stop()
        assert server.server is None

    asyncio.run(scenario())

    assert [call[0] for call in calls] == ["serve", "close", "wait_closed"]


def test_desktop_event_stream_service_attaches_runtime_handle() -> None:
    async def scenario() -> None:
        bus = DesktopEventBus(loop=asyncio.get_running_loop())
        server = DesktopWSServer(bus=bus, host="127.0.0.1", port=0, path="/desktop/events")
        service = DesktopService(event_bus=bus, ws_server=server)
        runtime = type("Runtime", (), {})()

        service.attach_runtime(runtime)

        assert getattr(runtime, DESKTOP_EVENT_STREAM_RUNTIME_ATTR) is service
        assert runtime.desktop_event_bus is bus
        assert runtime.desktop_ws_server is server
        readiness = desktop_event_stream_service_readiness(runtime)
        assert readiness.service_id == "desktop_event_stream"
        assert readiness.status == "configured"
        assert readiness.ready is False

    asyncio.run(scenario())


def test_desktop_event_stream_service_readiness_falls_back_to_runtime_attrs() -> None:
    contract = service_contract_by_id("desktop_event_stream")
    runtime = type("Runtime", (), {"desktop_event_bus": None, "desktop_ws_server": None})()

    readiness = desktop_event_stream_service_readiness(runtime)

    assert readiness.service_id == "desktop_event_stream"
    assert readiness.status == "disabled"
    assert readiness.available is False
    assert readiness.api_routes == contract.api_routes
    assert readiness.runtime_facade_methods == contract.runtime_facade_methods
    assert readiness.process_split_candidate is contract.process_split_candidate
    assert readiness.process_split_ready is contract.process_split_ready
    assert readiness.runtime_attr == DESKTOP_EVENT_STREAM_RUNTIME_ATTR
    assert readiness.lifecycle_boundary == DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY
    assert readiness.externalization_scope == DESKTOP_EVENT_STREAM_EXTERNALIZATION_SCOPE
    assert readiness.app_owned_lifecycle is True


def test_desktop_event_stream_boundary_metadata_keeps_ws_lifecycle_app_owned() -> None:
    readiness = desktop_event_stream_readiness(event_bus=None, ws_server=None)

    assert DESKTOP_EVENT_STREAM_RUNTIME_ATTR == "_desktop_event_stream_service"
    assert DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY == "app_owned_websocket_lifecycle_not_runtime_service_starter"
    assert readiness.runtime_attr == DESKTOP_EVENT_STREAM_RUNTIME_ATTR
    assert readiness.lifecycle_boundary == DESKTOP_EVENT_STREAM_LIFECYCLE_BOUNDARY
    assert readiness.externalization_scope == "event_bus_replay_only_ws_lifecycle_app_owned"
    assert readiness.app_owned_lifecycle is True
