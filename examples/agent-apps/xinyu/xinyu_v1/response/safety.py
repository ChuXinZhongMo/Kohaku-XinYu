"""Final response safety checks."""

from __future__ import annotations

from ..gateway.models import InboundTurn
from ..types import GateDecision, SafetyDecision, Severity


PRIVATE_LEAK_MARKERS = ("XINYU_API_KEY", "Authorization:", "Bearer ", "runtime_bridge_state.md")


def check_response_safety(text: str, turn: InboundTurn) -> GateDecision:
    if not text.strip() and turn.kind.value not in {"probe", "maintenance"}:
        return GateDecision(SafetyDecision.REVIEW, "blank_reply", Severity.WARNING)
    if any(marker in text for marker in PRIVATE_LEAK_MARKERS):
        return GateDecision(SafetyDecision.BLOCK, "private_marker_in_reply", Severity.ERROR)
    return GateDecision(SafetyDecision.ALLOW, "ok")

