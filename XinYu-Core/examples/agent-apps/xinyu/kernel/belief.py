"""Belief Engine owned by Self (K-006).

Beliefs are the result of Experience + Prediction Error + Goal evaluation.
They are stable (but updatable) owned objects of the Self.

Core flow:
Experience / PredictionError → BeliefProposal → Gate (stability, evidence) → Commit as owned Belief

Beliefs then influence:
- Prediction generation
- Attention weighting
- Future Goal adjustments
- (Later) World Model

Design constraints:
- No preset personality
- All beliefs traceable to source events
- Owned via Self.claim_ownership
- Minimal for now: simple confidence + evidence list
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field



BeliefStatus = Literal["candidate", "stable", "rejected", "contradicted"]


class Belief(BaseModel):
    """A belief owned by Self.

    Formed from high-signal experiences and prediction errors.
    """
    belief_id: str
    content: str = Field(min_length=5, max_length=400)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    status: BeliefStatus = "candidate"
    evidence_event_ids: list[str] = Field(default_factory=list)
    source_self_id: str
    created_at: str
    last_updated: str | None = None
    related_goals: list[str] = Field(default_factory=list)  # goal_ids


class BeliefEngine:
    """Manages beliefs for a Self.

    Beliefs are the 'what I think is true' layer.
    """

    def __init__(self, self_id: str):
        self.self_id = self_id
        self.beliefs: list[Belief] = []

    def propose_belief(
        self,
        content: str,
        confidence: float = 0.5,
        evidence_event_ids: list[str] | None = None,
        source_event_id: str | None = None,
        related_goals: list[str] | None = None,
    ) -> Belief | None:
        """Propose a new belief (from Experience or PredictionError).

        Returns the belief if accepted for further gate, else None.
        """
        if confidence < 0.4:
            return None  # too weak

        belief = Belief(
            belief_id=f"belief-{self.self_id[:8]}-{len(self.beliefs)}",
            content=content[:400],
            confidence=confidence,
            status="candidate",
            evidence_event_ids=evidence_event_ids or ([source_event_id] if source_event_id else []),
            source_self_id=self.self_id,
            created_at=source_event_id or "",
            related_goals=related_goals or [],
        )
        return belief

    def commit_belief(self, belief: Belief, force: bool = False) -> bool:
        """Commit after gate.

        For now: simple gate - high confidence or force.
        """
        if not force and belief.confidence < 0.6:
            return False

        # Check for contradictions (very basic)
        for existing in self.beliefs:
            if existing.content[:50] == belief.content[:50] and existing.status == "stable":
                if belief.confidence > existing.confidence + 0.2:
                    existing.status = "contradicted"
                else:
                    return False  # don't override stable with weaker

        # Claim ownership will be handled by caller (Self)
        self.beliefs.append(belief)
        return True

    def get_stable_beliefs(self, min_confidence: float = 0.6) -> list[Belief]:
        return [
            b for b in self.beliefs
            if b.status in ("stable", "candidate") and b.confidence >= min_confidence
        ]

    def reinforce(self, belief_id: str, delta: float, event_id: str | None = None) -> bool:
        """K-008: strengthen a belief after reorg cycle confirmation."""
        for b in self.beliefs:
            if b.belief_id == belief_id:
                b.confidence = max(0.0, min(1.0, b.confidence + delta))
                b.last_updated = event_id
                if b.confidence >= 0.7 and b.status == "candidate":
                    b.status = "stable"
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "self_id": self.self_id,
            "beliefs": [b.model_dump() for b in self.beliefs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BeliefEngine":
        eng = cls(self_id=data.get("self_id"))
        for b in data.get("beliefs", []):
            eng.beliefs.append(Belief.model_validate(b))
        return eng

    def beliefs_to_context(self, max_items: int = 3) -> str:
        """Compact context for Prediction / Narrative."""
        stable = self.get_stable_beliefs()[:max_items]
        if not stable:
            return ""
        return "I believe: " + " | ".join(b.content[:70] for b in stable)
