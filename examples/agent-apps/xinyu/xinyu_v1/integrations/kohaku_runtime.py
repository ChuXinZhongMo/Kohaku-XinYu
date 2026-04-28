"""Adapter boundary for the existing KohakuTerrarium runtime."""

from __future__ import annotations

from dataclasses import dataclass

from ..gateway.models import InboundTurn


@dataclass(frozen=True, slots=True)
class KohakuRuntimeResult:
    reply: str
    memory_changed: bool | None = None
    notes: tuple[str, ...] = ("kohaku_runtime",)


class KohakuRuntimeAdapter:
    async def run_turn(self, turn: InboundTurn) -> KohakuRuntimeResult:
        return KohakuRuntimeResult(reply="", memory_changed=None, notes=("kohaku_runtime_unconfigured", turn.kind.value))

