"""Slow path adapter boundary."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from ..gateway.models import InboundTurn
from .hybrid_router import RouteDecision


@dataclass(frozen=True, slots=True)
class SlowPathResult:
    reply: str
    memory_changed: bool | None = None
    notes: tuple[str, ...] = ("slow_path",)


SlowPathHandler = Callable[[InboundTurn, RouteDecision], Awaitable[SlowPathResult]]


class SlowPathRuntime:
    def __init__(self, handler: SlowPathHandler | None = None) -> None:
        self._handler = handler

    async def run(self, turn: InboundTurn, decision: RouteDecision) -> SlowPathResult:
        if self._handler is None:
            return SlowPathResult(reply="", memory_changed=None, notes=("slow_path_unconfigured",))
        return await self._handler(turn, decision)

