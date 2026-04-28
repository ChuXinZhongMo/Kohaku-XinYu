"""Route risk scoring."""

from __future__ import annotations

from dataclasses import dataclass

from ..gateway.models import InboundTurn
from ..types import normalize_risk_score
from .classifier import TurnClassification


@dataclass(frozen=True, slots=True)
class RiskScore:
    score: float
    reasons: tuple[str, ...]


def score_turn_risk(turn: InboundTurn, classification: TurnClassification) -> RiskScore:
    score = classification.salience
    reasons: list[str] = []
    if turn.actor.is_owner and "relationship_pressure" in classification.intents:
        score += 0.25
        reasons.append("owner_relationship_pressure")
    if turn.has_attachments:
        score += 0.25
        reasons.append("attachment")
    if "learning" in classification.intents:
        score += 0.2
        reasons.append("learning_request")
    if "conflict" in classification.intents:
        score += 0.2
        reasons.append("conflict")
    if turn.actor.group_id:
        score += 0.1
        reasons.append("group_context")
    return RiskScore(score=normalize_risk_score(score), reasons=tuple(reasons))

