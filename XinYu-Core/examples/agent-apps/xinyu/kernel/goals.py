"""Goals / Motivation layer for Cognitive Kernel (K-004).

Goals are owned by Self and drive behavior and predictions.
They evolve slowly via high-importance Experience or Prediction Errors.
All goals are claimed by the owning Self.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .exceptions import KernelError

# Avoid circular import with Self; SelfModel passed when needed
SelfModel = "SelfModel"  # for type hints only


GoalStatus = Literal["active", "achieved", "abandoned", "paused"]


class Goal(BaseModel):
    """A goal/motivation owned by Self."""
    goal_id: str
    description: str = Field(min_length=5, max_length=300)
    priority: float = Field(ge=0.0, le=1.0, default=0.5)
    status: GoalStatus = "active"
    source_self_id: str
    created_from_event: str | None = None
    last_updated: str | None = None


class GoalManager:
    """Manages goals for a Self. Goals are the 'why' behind actions and predictions."""

    def __init__(self, self_id: str, self_model: Any = None):
        self.self_id = self_id
        self.self_model = self_model  # optional for now to avoid cycles
        self.goals: list[Goal] = []

    def propose_goal(
        self,
        description: str,
        priority: float = 0.5,
        source_event_id: str | None = None,
        force: bool = False,
    ) -> Goal | None:
        """Propose and add a new goal (after validation/gate).

        In full flow, called from Experience or high-error PredictionError.
        """
        if not force and self.self_model is not None:
            # Simple gate
            if hasattr(self.self_model, "core_statements") and not self.self_model.core_statements and priority < 0.7:
                return None

        goal = Goal(
            goal_id=f"goal-{self.self_id[:8]}-{len(self.goals)}",
            description=description[:300],
            priority=priority,
            source_self_id=self.self_id,
            created_from_event=source_event_id,
        )
        self.add_goal(goal)
        return goal

    def add_goal(self, goal: Goal) -> None:
        if goal.source_self_id != self.self_id:
            raise KernelError("Goal must belong to this Self")
        # Claim ownership if model available
        if self.self_model is not None and hasattr(self.self_model, "add_owned"):
            if not self.self_model.has_owned(goal.goal_id):
                self.self_model.add_owned(goal.goal_id, "goal")
        self.goals.append(goal)

    def get_active_goals(self, top_k: int = 5) -> list[Goal]:
        active = [g for g in self.goals if g.status == "active"]
        return sorted(active, key=lambda g: g.priority, reverse=True)[:top_k]

    def update_goal_status(self, goal_id: str, new_status: GoalStatus, event_id: str | None = None) -> bool:
        for g in self.goals:
            if g.goal_id == goal_id:
                g.status = new_status
                g.last_updated = event_id
                return True
        return False

    def adjust_priority(self, goal_id: str, delta: float, event_id: str | None = None) -> bool:
        """K-008: shift goal priority after reorganization signals."""
        for g in self.goals:
            if g.goal_id == goal_id and g.status == "active":
                g.priority = max(0.0, min(1.0, g.priority + delta))
                g.last_updated = event_id
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "self_id": self.self_id,
            "goals": [g.model_dump() for g in self.goals],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], self_model: Any = None) -> "GoalManager":
        gm = cls(self_id=data.get("self_id"), self_model=self_model)
        for g in data.get("goals", []):
            gm.goals.append(Goal.model_validate(g))
        return gm

