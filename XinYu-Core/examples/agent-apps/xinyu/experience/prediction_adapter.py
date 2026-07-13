"""Adapter to close the Prediction Error loop with Self and Experience (K-003).

Usage:
    After an outcome is known (e.g. post-reply or action result),
    generate prediction from Self, record outcome, and if high error,
    feed back as proposal to Self Model.
"""

from __future__ import annotations

from typing import Any

from kernel.self import Self


def run_prediction_cycle(
    kernel_self: Self,
    current_self_model: dict | None = None,
    outcome_reality: str | None = None,
    source_event_id: str = "unknown",
    include_reorg: bool = True,
) -> dict[str, Any]:
    """One prediction-error cycle (K-003 + K-004).

    1. Generate prediction from Self Model + active Goals.
    2. If outcome known, record it and get error.
    3. High error -> self model proposals AND/or goal adjustments.
    """
    if current_self_model is None:
        current_self_model = kernel_self.get_self_model()

    pred = kernel_self.generate_prediction(source_event_id=source_event_id)

    result: dict[str, Any] = {
        "prediction": pred.model_dump(),
        "active_goals": [g.model_dump() for g in kernel_self.get_active_goals(3)],
    }

    if outcome_reality:
        error = kernel_self.record_prediction_outcome(
            pred.prediction_id, outcome_reality, source_event_id
        )
        result["error"] = error.model_dump()

        feedback = kernel_self.error_to_self_proposal(error)
        result["self_proposal_feedback"] = feedback

        if feedback.get("should_propose"):
            result["recommend_propose"] = True

        # K-004: if error high, can propose goal change too
        if error.error_magnitude > 0.7:
            result["suggest_goal_review"] = True

        # K-006: also feed to beliefs
        from .belief_adapter import apply_to_beliefs
        belief_res = apply_to_beliefs(
            kernel_self,
            feedback.get("proposals", []),
            source_event_id,
        )
        result["belief_result"] = belief_res

        # K-007: update World Model from error
        if "error" in result:
            from .world_model_adapter import apply_to_world_model
            wm_res = apply_to_world_model(
                kernel_self,
                from_error=result["error"],
                source_event_id=source_event_id,
            )
            result["world_model_result"] = wm_res

        # K-008: cross-layer reorganization (skipped when K-009 cycle owns reorg)
        if include_reorg:
            from .reorganization_adapter import run_reorganization_cycle

            reorg_res = run_reorganization_cycle(
                kernel_self,
                prediction_error=result.get("error"),
                belief_result=result.get("belief_result"),
                world_model_result=result.get("world_model_result"),
                source_event_id=source_event_id,
            )
            result["reorganization_result"] = reorg_res

    return result
