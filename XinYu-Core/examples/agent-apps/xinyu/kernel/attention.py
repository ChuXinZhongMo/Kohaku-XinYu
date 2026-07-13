"""Attention Buffer + Working Memory selection for Cognitive Kernel (K-005).

Core idea (from architecture):
- Not all memory/context floods into narrative/prediction.
- Attention Buffer selects the most relevant items based on:
  - Current Self Model (core statements)
  - Active Goals
  - Recent Prediction Errors (high error items get priority)
- Produces a compact "working memory" context for downstream layers (Prediction, Narrative, Decision).

This prevents context explosion and focuses the system on what matters for Self.

Keeps kernel independent, traceable.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AttentionItem(BaseModel):
    """An item that can enter the attention buffer."""
    item_id: str
    content: str = Field(max_length=500)
    item_type: str = "memory"  # memory, goal, prediction_error, experience, etc.
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.5)
    source_event_id: str | None = None


class AttentionBuffer:
    """Selects and maintains the current focus of attention for a Self.

    In full system: fed from Memory System (with Episodic/Semantic), Goals, Prediction.
    Outputs compact working context.
    """

    def __init__(self, self_id: str, max_items: int = 5):
        self.self_id = self_id
        self.max_items = max_items
        self.buffer: list[AttentionItem] = []

    def update_from_self_model(self, self_model: dict, weight: float = 0.4) -> None:
        """Boost attention for items matching Self Model core statements."""
        core = self_model.get("core_summary", "")
        if not core:
            return
        core_lower = core.lower()
        for item in self.buffer:
            if any(kw in item.content.lower() for kw in core_lower.split()[:5]):
                item.relevance_score = min(1.0, item.relevance_score + weight * 0.3)

    def update_from_goals(self, active_goals: list[dict], weight: float = 0.3) -> None:
        """Boost items related to current active goals."""
        for goal in active_goals:
            desc_lower = goal.get("description", "").lower()
            for item in self.buffer:
                if any(kw in item.content.lower() for kw in desc_lower.split()[:4]):
                    item.relevance_score = min(1.0, item.relevance_score + weight * 0.4)

    def update_from_prediction_error(self, error: dict | None, weight: float = 0.5) -> None:
        """High error items get strong attention boost (core of K-005)."""
        if not error or error.get("error_magnitude", 0) < 0.4:
            return
        impact = error.get("impact_on_self", [])
        reality = error.get("reality", "").lower()
        pred_id = error.get("prediction_id")
        for item in self.buffer:
            if any(imp in reality for imp in impact) or (pred_id and pred_id in item.content):
                item.relevance_score = min(1.0, item.relevance_score + weight * error["error_magnitude"])

    def add_item(self, item: AttentionItem) -> None:
        """Add or update an item in the buffer."""
        existing = next((i for i in self.buffer if i.item_id == item.item_id), None)
        if existing:
            existing.relevance_score = max(existing.relevance_score, item.relevance_score)
            existing.content = item.content  # refresh
        else:
            self.buffer.append(item)

        # Keep only top items
        self.buffer.sort(key=lambda x: x.relevance_score, reverse=True)
        self.buffer = self.buffer[: self.max_items]

    def get_working_memory(self) -> list[dict[str, Any]]:
        """Return the current focused working memory (sorted by relevance)."""
        self.buffer.sort(key=lambda x: x.relevance_score, reverse=True)
        return [item.model_dump() for item in self.buffer[: self.max_items]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "self_id": self.self_id,
            "max_items": self.max_items,
            "buffer": [item.model_dump() for item in self.buffer],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AttentionBuffer":
        buf = cls(self_id=data.get("self_id"), max_items=data.get("max_items", 5))
        for item in data.get("buffer", []):
            buf.buffer.append(AttentionItem.model_validate(item))
        return buf
