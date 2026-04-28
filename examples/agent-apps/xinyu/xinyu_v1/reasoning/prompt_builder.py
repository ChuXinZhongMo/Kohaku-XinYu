"""Prompt assembly for slow reasoning."""

from __future__ import annotations

from dataclasses import dataclass

from ..types import TokenBudget
from .models import ReasoningRequest


@dataclass(frozen=True, slots=True)
class PromptBundle:
    system: str
    user: str
    notes: tuple[str, ...]


class PromptBuilder:
    def __init__(self, token_budget: TokenBudget | None = None) -> None:
        self._budget = token_budget or TokenBudget().validate()

    def build(self, request: ReasoningRequest) -> PromptBundle:
        memory_lines: list[str] = []
        for result in request.memories[:8]:
            chunk = result.chunk
            memory_lines.append(f"- [{chunk.layer.value} score={result.score:.2f}] {chunk.text[:360]}")
        emotion_line = ""
        if request.emotion_state:
            vector = request.emotion_state.vector
            active = [f"{key}={value:.2f}" for key, value in vector.to_json().items() if abs(float(value)) >= 0.08]
            emotion_line = ", ".join(active[:8])
        system_parts = [
            "You are XinYu's slow reasoning runtime.",
            "Preserve hidden reasoning boundaries. Do not expose chain-of-thought.",
            "Return only the outward reply text unless the caller asks for structured maintenance output.",
        ]
        if request.system_context:
            system_parts.append(request.system_context[: self._budget.prompt_context])
        if emotion_line:
            system_parts.append(f"Current emotional vector: {emotion_line}")
        if memory_lines:
            system_parts.append("Relevant memories:\n" + "\n".join(memory_lines))
        user = request.turn.text[: self._budget.total]
        return PromptBundle(system="\n\n".join(system_parts), user=user, notes=("prompt_built",))

