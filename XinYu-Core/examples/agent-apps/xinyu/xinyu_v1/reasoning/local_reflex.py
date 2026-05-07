"""Local deterministic reflex replies."""

from __future__ import annotations

from ..routing.fast_path import FastPathResponder, FastPathResult
from .models import ReasoningRequest, ReasoningResult


class LocalReflexReasoner:
    def __init__(self) -> None:
        self._responder = FastPathResponder()

    async def run(self, request: ReasoningRequest) -> ReasoningResult:
        result: FastPathResult = self._responder.respond(request.turn, request.route.classification)
        return ReasoningResult(draft=result.reply, memory_changed=result.memory_changed, notes=result.notes)

