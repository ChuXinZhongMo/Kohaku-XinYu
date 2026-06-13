from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

from xinyu_bridge_http_dispatch import dispatch_get_route, dispatch_post_route
from xinyu_bridge_http_routes import LIFE_TICKET_PREFIX


class _Runtime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def health_snapshot(self) -> dict[str, Any]:
        return {"route": "health_snapshot"}

    async def probe(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("probe", payload)

    async def proactive(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("proactive", payload)

    async def desktop_events_recent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("desktop_events_recent", payload)

    async def desktop_private_desktop_snapshot(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("desktop_private_desktop_snapshot", payload)

    async def external_plugin_manifest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("external_plugin_manifest", payload)

    async def turn_current(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("turn_current", payload)

    async def life_metabolism_ticket_list(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("life_metabolism_ticket_list", payload)

    async def life_metabolism_ticket_get(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("life_metabolism_ticket_get", payload)

    async def life_metabolism_ticket_approve(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("life_metabolism_ticket_approve", payload)

    async def desktop_private_desktop_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("desktop_private_desktop_start", payload)

    def qq_outbox_claim_fast(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("qq_outbox_claim_fast", payload)

    async def learning_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("learning_ingest", payload)

    async def goldmark_mark_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._record("goldmark_mark_request", payload)
        result["http_status"] = payload.get("http_status", HTTPStatus.OK.value)
        return result

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._record("chat", payload)

    def _record(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, dict(payload)))
        return {"route": name, "payload": dict(payload)}


def _run_on_loop(coro: Any, *, timeout: int) -> Any:
    _run_on_loop.timeouts.append(timeout)
    return asyncio.run(coro)


_run_on_loop.timeouts = []  # type: ignore[attr-defined]


def test_get_dispatch_uses_sync_health_snapshot_without_loop() -> None:
    _run_on_loop.timeouts.clear()
    result = dispatch_get_route(runtime=_Runtime(), route="/health", payload={}, run_on_loop=_run_on_loop)
    assert result == {"route": "health_snapshot"}
    assert _run_on_loop.timeouts == []


def test_probe_dispatch_routes_get_and_post_to_runtime_probe() -> None:
    _run_on_loop.timeouts.clear()
    runtime = _Runtime()

    get_result = dispatch_get_route(
        runtime=runtime,
        route="/probe",
        payload={"text": "get"},
        run_on_loop=_run_on_loop,
    )
    post_result = dispatch_post_route(
        runtime=runtime,
        route="/probe",
        payload={"text": "post"},
        run_on_loop=_run_on_loop,
        request_timeout_seconds=30,
    )

    assert get_result == {"route": "probe", "payload": {"text": "get"}}
    assert post_result is not None
    assert post_result.data == {"route": "probe", "payload": {"text": "post"}}
    assert _run_on_loop.timeouts == [10, 10]


def test_get_dispatch_routes_runtime_calls_with_expected_timeouts() -> None:
    _run_on_loop.timeouts.clear()
    runtime = _Runtime()

    assert dispatch_get_route(
        runtime=runtime,
        route="/desktop/private-desktop/snapshot",
        payload={"frame": "latest"},
        run_on_loop=_run_on_loop,
    ) == {"route": "desktop_private_desktop_snapshot", "payload": {"frame": "latest"}}
    assert dispatch_get_route(
        runtime=runtime,
        route="/external/plugins",
        payload={},
        run_on_loop=_run_on_loop,
    ) == {"route": "external_plugin_manifest", "payload": {}}
    assert dispatch_get_route(
        runtime=runtime,
        route="/turn/current",
        payload={},
        run_on_loop=_run_on_loop,
    ) == {"route": "turn_current", "payload": {}}

    assert _run_on_loop.timeouts == [15, 5, 5]


def test_get_dispatch_routes_desktop_events_recent_with_surface_timeout() -> None:
    _run_on_loop.timeouts.clear()
    runtime = _Runtime()

    result = dispatch_get_route(
        runtime=runtime,
        route="/desktop/events/recent",
        payload={"limit": 10},
        run_on_loop=_run_on_loop,
    )

    assert result == {"route": "desktop_events_recent", "payload": {"limit": 10}}
    assert runtime.calls == [("desktop_events_recent", {"limit": 10})]
    assert _run_on_loop.timeouts == [5]


def test_get_dispatch_preserves_proactive_claim_default_and_life_ticket_payload() -> None:
    _run_on_loop.timeouts.clear()
    runtime = _Runtime()

    proactive_payload: dict[str, Any] = {}
    proactive = dispatch_get_route(
        runtime=runtime,
        route="/proactive",
        payload=proactive_payload,
        run_on_loop=_run_on_loop,
    )
    assert proactive == {"route": "proactive", "payload": {"claim": "false"}}
    assert proactive_payload == {"claim": "false"}

    ticket = dispatch_get_route(
        runtime=runtime,
        route=f"{LIFE_TICKET_PREFIX}/ticket-1",
        payload={"include": "details"},
        run_on_loop=_run_on_loop,
    )
    assert ticket == {
        "route": "life_metabolism_ticket_get",
        "payload": {"include": "details", "ticket_id": "ticket-1"},
    }


def test_get_dispatch_returns_none_for_unknown_route() -> None:
    result = dispatch_get_route(runtime=_Runtime(), route="/unknown", payload={}, run_on_loop=_run_on_loop)
    assert result is None


def test_post_dispatch_routes_life_ticket_action_and_mutates_payload() -> None:
    _run_on_loop.timeouts.clear()
    payload: dict[str, Any] = {}
    result = dispatch_post_route(
        runtime=_Runtime(),
        route=f"{LIFE_TICKET_PREFIX}/ticket-1/approve",
        payload=payload,
        run_on_loop=_run_on_loop,
        request_timeout_seconds=30,
    )
    assert result is not None
    assert result.status == HTTPStatus.OK
    assert result.data == {
        "route": "life_metabolism_ticket_approve",
        "payload": {"ticket_id": "ticket-1"},
    }
    assert payload == {"ticket_id": "ticket-1"}
    assert _run_on_loop.timeouts == [10]


def test_post_dispatch_uses_fast_outbox_claim_without_loop() -> None:
    _run_on_loop.timeouts.clear()
    result = dispatch_post_route(
        runtime=_Runtime(),
        route="/qq/outbox/claim",
        payload={"limit": 1},
        run_on_loop=_run_on_loop,
        request_timeout_seconds=30,
    )
    assert result is not None
    assert result.data == {"route": "qq_outbox_claim_fast", "payload": {"limit": 1}}
    assert _run_on_loop.timeouts == []


def test_post_dispatch_preserves_request_timeouts_and_goldmark_status() -> None:
    _run_on_loop.timeouts.clear()
    runtime = _Runtime()

    desktop_start = dispatch_post_route(
        runtime=runtime,
        route="/desktop/private-desktop/start",
        payload={},
        run_on_loop=_run_on_loop,
        request_timeout_seconds=12,
    )
    learning = dispatch_post_route(
        runtime=runtime,
        route="/learning/ingest",
        payload={},
        run_on_loop=_run_on_loop,
        request_timeout_seconds=12,
    )
    goldmark = dispatch_post_route(
        runtime=runtime,
        route="/review/goldmark/mark_request",
        payload={"http_status": HTTPStatus.FORBIDDEN.value},
        run_on_loop=_run_on_loop,
        request_timeout_seconds=12,
    )

    assert desktop_start is not None
    assert desktop_start.data["route"] == "desktop_private_desktop_start"
    assert learning is not None
    assert learning.data["route"] == "learning_ingest"
    assert goldmark is not None
    assert goldmark.status == HTTPStatus.FORBIDDEN
    assert goldmark.data["route"] == "goldmark_mark_request"
    assert _run_on_loop.timeouts == [45, 12, 10]


def test_post_dispatch_routes_chat_and_returns_none_for_unknown_route() -> None:
    _run_on_loop.timeouts.clear()
    chat = dispatch_post_route(
        runtime=_Runtime(),
        route="/chat",
        payload={"text": "hello"},
        run_on_loop=_run_on_loop,
        request_timeout_seconds=30,
    )
    unknown = dispatch_post_route(
        runtime=_Runtime(),
        route="/unknown",
        payload={},
        run_on_loop=_run_on_loop,
        request_timeout_seconds=30,
    )

    assert chat is not None
    assert chat.data == {"route": "chat", "payload": {"text": "hello"}}
    assert unknown is None
    assert _run_on_loop.timeouts == [30]
