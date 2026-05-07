from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

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
