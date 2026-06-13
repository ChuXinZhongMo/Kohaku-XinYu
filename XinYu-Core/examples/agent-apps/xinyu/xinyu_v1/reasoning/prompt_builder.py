"""Prompt assembly for slow reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field

from xinyu_persona_voice import persona_voice_header, unified_voice_enabled

from ..types import TokenBudget
from .models import ReasoningRequest


@dataclass(frozen=True, slots=True)
class PromptBundle:
    system: str
    user: str
    history: tuple[dict[str, str], ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)


class PromptBuilder:
    def __init__(self, token_budget: TokenBudget | None = None) -> None:
        self._budget = token_budget or TokenBudget().validate()

    def build(self, request: ReasoningRequest) -> PromptBundle:
        memory_lines: list[str] = []
        for result in request.memories[:8]:
            chunk = result.chunk
            memory_lines.append(f"- [{chunk.layer.value} score={result.score:.2f}] {chunk.text[:360]}")
        history_messages: list[dict[str, str]] = []
        for message in request.recent_messages[-8:]:
            role = "assistant" if message.role == "assistant" else "user"
            text = " ".join(message.text.split())[:720]
            if text:
                history_messages.append({"role": role, "content": text})
        emotion_line = ""
        if request.emotion_state:
            vector = request.emotion_state.vector
            active = [f"{key}={value:.2f}" for key, value in vector.to_json().items() if abs(float(value)) >= 0.08]
            emotion_line = ", ".join(active[:8])
        if unified_voice_enabled():
            # This path otherwise carries zero persona; give it the one shared
            # voice (persona contract + thin-expression + output boundaries) so
            # the slow path sounds like the same person as the live path.
            system_parts = [persona_voice_header()]
        else:
            system_parts = [
                "You are XinYu's slow reasoning runtime.",
                "Preserve hidden reasoning boundaries. Do not expose chain-of-thought.",
                "Return only the outward reply text unless the caller asks for structured maintenance output.",
                "Treat prior chat messages as authoritative short-term context for callbacks and corrections.",
            ]
        if request.system_context:
            system_parts.append(request.system_context[: self._budget.prompt_context])
        if emotion_line:
            system_parts.append(f"Current emotional vector: {emotion_line}")
        if memory_lines:
            system_parts.append("Relevant memories:\n" + "\n".join(memory_lines))
        user = request.turn.text[: self._budget.total]
        return PromptBundle(
            system="\n\n".join(system_parts),
            user=user,
            history=tuple(history_messages),
            notes=("prompt_built", f"history_messages:{len(history_messages)}"),
        )
