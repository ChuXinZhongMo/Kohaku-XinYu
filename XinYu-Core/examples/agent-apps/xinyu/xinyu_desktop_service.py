from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_EVENT_STREAM_RUNTIME_ATTR,
    DesktopEventStreamReadiness,
    desktop_event_stream_readiness,
)
from xinyu_desktop_events import DesktopEventBus
from xinyu_desktop_ws import DesktopWSServer


@dataclass(slots=True)
class DesktopService:
    event_bus: DesktopEventBus | None = None
    ws_server: DesktopWSServer | None = None

    @property
    def enabled(self) -> bool:
        return self.event_bus is not None and self.ws_server is not None

    def attach_runtime(self, runtime: Any) -> None:
        setattr(runtime, DESKTOP_EVENT_STREAM_RUNTIME_ATTR, self)
        runtime.desktop_event_bus = self.event_bus
        runtime.desktop_ws_server = self.ws_server

    async def start(self) -> None:
        if self.ws_server is not None:
            await self.ws_server.start()

    async def stop(self) -> None:
        if self.ws_server is not None:
            await self.ws_server.stop()

    def listener_url(self) -> str:
        if self.ws_server is None:
            return ""
        return f"ws://{self.ws_server.host}:{self.ws_server.bound_port}{self.ws_server.path}"

    def readiness(self) -> DesktopEventStreamReadiness:
        return desktop_event_stream_readiness(event_bus=self.event_bus, ws_server=self.ws_server)


def desktop_event_stream_service_readiness(runtime: Any) -> DesktopEventStreamReadiness:
    service = getattr(runtime, DESKTOP_EVENT_STREAM_RUNTIME_ATTR, None)
    readiness = getattr(service, "readiness", None)
    if callable(readiness):
        return readiness()
    return desktop_event_stream_readiness(
        event_bus=getattr(runtime, "desktop_event_bus", None),
        ws_server=getattr(runtime, "desktop_ws_server", None),
    )


def desktop_limit(value: Any, *, default: int, maximum: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(maximum, parsed))


async def desktop_event_state(event_bus: Any | None) -> dict[str, Any]:
    if event_bus is None:
        return {
            "version": 1,
            "available": False,
            "max_events": 0,
            "buffer_size": 0,
            "latest_event_id": "",
            "subscriber_count": 0,
        }
    snapshot = await event_bus.snapshot()
    snapshot["available"] = True
    return snapshot


async def desktop_events_recent(event_bus: Any | None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    limit = desktop_limit((payload or {}).get("limit"), default=100, maximum=500)
    if event_bus is None:
        return {"version": 1, "items": [], "latestEventId": "", "notes": ["desktop_event_bus_unavailable"]}
    items = await event_bus.recent(limit=limit)
    latest = await event_bus.latest_event_id()
    return {
        "version": 1,
        "items": items,
        "latestEventId": latest,
        "notes": ["desktop_events_recent_v0"],
    }


def desktop_recent_items(
    items: list[dict[str, Any]],
    payload: dict[str, Any] | None = None,
    *,
    default: int,
    maximum: int,
    notes: list[str],
) -> dict[str, Any]:
    limit = desktop_limit((payload or {}).get("limit"), default=default, maximum=maximum)
    return {
        "version": 1,
        "items": list(items[-limit:]),
        "notes": notes,
    }


def desktop_services(*, ws_server: Any | None, closed: bool, memory_root_exists: bool) -> list[dict[str, Any]]:
    desktop_ws_status = "offline"
    desktop_ws_port = 0
    if ws_server is not None:
        desktop_ws_status = "ready" if ws_server.server is not None else "configured"
        desktop_ws_port = ws_server.bound_port
    return [
        {
            "service": "core",
            "status": "stopping" if closed else "ready",
            "pid": os.getpid(),
            "message": "xinyu_core_bridge runtime",
        },
        {
            "service": "desktop_events",
            "status": desktop_ws_status,
            "port": desktop_ws_port,
            "message": "desktop event stream dark launch",
        },
        {
            "service": "memory",
            "status": "ready" if memory_root_exists else "degraded",
            "message": "local memory root",
        },
    ]


def build_desktop_service(
    *,
    enabled: bool,
    loop: asyncio.AbstractEventLoop,
    host: str,
    port: int,
    token: str,
) -> DesktopService:
    if not enabled:
        return DesktopService()
    event_bus = DesktopEventBus(loop=loop)
    ws_server = DesktopWSServer(
        bus=event_bus,
        host=host,
        port=port,
        token=token,
    )
    return DesktopService(event_bus=event_bus, ws_server=ws_server)
