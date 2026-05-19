"""Detect conflict signals before final response."""

from __future__ import annotations

from .models import ConflictReport, ReasoningRequest


CONFLICT_TERMS = ("不对", "不是这样", "你刚才", "矛盾", "冲突", "前后不一致")


def inspect_conflict(request: ReasoningRequest) -> ConflictReport:
    reasons: list[str] = []
    text = request.turn.text
    if any(term in text for term in CONFLICT_TERMS):
        reasons.append("explicit_user_conflict_marker")
    if "conflict" in request.route.classification.intents:
        reasons.append("classifier_conflict")
    severity = min(1.0, 0.35 * len(reasons))
    return ConflictReport(has_conflict=bool(reasons), reasons=tuple(reasons), severity=severity)

