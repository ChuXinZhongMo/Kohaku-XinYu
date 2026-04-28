"""Low-latency local route implementation."""

from __future__ import annotations

from dataclasses import dataclass

from ..gateway.models import InboundTurn
from .classifier import TurnClassification


@dataclass(frozen=True, slots=True)
class FastPathResult:
    reply: str
    memory_changed: bool = False
    notes: tuple[str, ...] = ("fast_path",)


class FastPathResponder:
    def respond(self, turn: InboundTurn, classification: TurnClassification) -> FastPathResult:
        intents = set(classification.intents)
        if "probe" in intents:
            return FastPathResult(reply="[OK]", notes=("fast_path", "probe"))
        if "empty" in intents:
            return FastPathResult(reply="", notes=("fast_path", "empty"))
        if "greeting" in intents:
            return FastPathResult(reply="在。", notes=("fast_path", "greeting"))
        if "ack" in intents:
            return FastPathResult(reply="嗯。", notes=("fast_path", "ack"))
        return FastPathResult(reply="", notes=("fast_path", "no_reply"))
