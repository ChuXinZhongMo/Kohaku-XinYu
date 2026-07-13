from __future__ import annotations

"""Prediction Engine for Cognitive Kernel (K-003).

Core idea (from architecture):
- Self generates expectations based on its Self Model.
- When outcome differs from prediction, a PredictionError is produced.
- High-magnitude errors can drive updates to Self Model (reorganization).

This is the primary learning signal instead of raw event rewards.
Keeps kernel independent, traceable via source_event_ids.
"""

from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .self.model import CoreStatementType
else:
    CoreStatementType = str  # runtime fallback


class Prediction(BaseModel):
    """A prediction generated from Self Model."""
    prediction_id: str
    statement: str  # what Self expected (derived from core statements)
    confidence: float = Field(ge=0.0, le=1.0)
    related_self_statements: list[str] = Field(default_factory=list)  # statement_ids
    source_event_id: str | None = None


class PredictionError(BaseModel):
    """Mismatch between prediction and reality."""
    prediction_id: str
    reality: str
    error_magnitude: float = Field(ge=0.0, le=1.0)  # 0-1, primary learning signal
    impact_on_self: list[CoreStatementType] = Field(default_factory=list)
    source_event_id: str | None = None


class PredictionEngine:
    """Prediction component owned by a Self.

    Generates expectations from Self Model.
    Records outcomes to compute Prediction Errors.
    High errors can suggest Self Model updates (fed back via propose_self_update).
    """

    def __init__(self, self_id: str):
        self.self_id = self_id
        self.active_predictions: dict[str, Prediction] = {}
        self._next_id = 0

    def generate_prediction(
        self, self_model: dict, source_event_id: str | None = None,
        goals_context: str = "", attention_context: str = "", beliefs_context: str = "", world_context: str = ""
    ) -> Prediction:
        """Generate a prediction based on Self Model + Goals + Attention + Beliefs + World Model (K-007).

        World Model adds generative / longer-term expectations.
        """
        summary = self_model.get("core_summary", "I am a stable subject with evolving commitments.")
        core_stmts = self_model.get("core_statements", [])[:2]

        related = []
        parts = [f"My core model says: {summary}"]
        if goals_context:
            parts.append(goals_context)
        if attention_context:
            parts.append(attention_context)
        if beliefs_context:
            parts.append(beliefs_context)
        if world_context:
            parts.append(world_context)
        for stmt in core_stmts:
            related.append(stmt.get("statement_id", ""))
            parts.append(f"{stmt.get('statement_type')}: {stmt.get('content', '')[:80]}")

        statement = ". ".join(parts) + "."

        pred = Prediction(
            prediction_id=f"pred-{self.self_id[:8]}-{self._next_id}",
            statement=statement[:400],
            confidence=0.65,
            related_self_statements=related,
            source_event_id=source_event_id,
        )
        self._next_id += 1
        self.active_predictions[pred.prediction_id] = pred
        return pred

    def record_outcome(
        self, prediction_id: str, reality: str, source_event_id: str | None = None
    ) -> PredictionError:
        """Record what actually happened and compute error.

        Error magnitude is the main signal for updating Self / World Model.
        """
        if prediction_id not in self.active_predictions:
            raise ValueError(f"Unknown prediction: {prediction_id}")

        pred = self.active_predictions.pop(prediction_id)

        # Simple but meaningful magnitude: normalized text difference + confidence factor
        len_diff = abs(len(reality) - len(pred.statement))
        base_error = min(1.0, len_diff / 300.0)
        error_mag = round(base_error * (1.0 + (1.0 - pred.confidence)) / 2, 3)

        impact: list[CoreStatementType] = []
        if error_mag > 0.65:
            impact.append("identity")
        if error_mag > 0.5:
            impact.append("core_value")

        return PredictionError(
            prediction_id=prediction_id,
            reality=reality[:300],
            error_magnitude=error_mag,
            impact_on_self=impact,
            source_event_id=source_event_id,
        )

    def should_propose_self_update(self, error: PredictionError) -> bool:
        """Decide if this error is strong enough to propose Self Model change."""
        return error.error_magnitude > 0.6 and len(error.impact_on_self) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "self_id": self.self_id,
            "active_predictions": {k: v.model_dump() for k, v in self.active_predictions.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PredictionEngine":
        eng = cls(self_id=data.get("self_id", "unknown"))
        for k, v in data.get("active_predictions", {}).items():
            eng.active_predictions[k] = Prediction.model_validate(v)
        return eng
