"""Reorganization adapter for K-008.

Closes the loop: Prediction Error + Belief + WM → structural updates
(Attention, Goals, memory candidates) with owner review gates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kernel.self import Self


def run_reorganization_cycle(
    kernel_self: Self | None,
    *,
    prediction_error: dict[str, Any] | None = None,
    belief_result: dict[str, Any] | None = None,
    world_model_result: dict[str, Any] | None = None,
    experience_result: dict[str, Any] | None = None,
    source_event_id: str = "unknown",
    event_root: Path | None = None,
    reorg_mode: str = "fast",
) -> dict[str, Any]:
    """Run one K-008 reorganization cycle and optionally record to event log."""
    if kernel_self is None:
        return {"status": "skipped", "reason": "no_kernel_self"}

    if prediction_error and "self_proposal_feedback" not in prediction_error:
        err_obj = prediction_error
        if err_obj.get("error_magnitude", 0) >= 0.5:
            from kernel.prediction import PredictionError

            try:
                pe = PredictionError.model_validate(err_obj)
                feedback = kernel_self.error_to_self_proposal(pe)
                prediction_error = {**err_obj, "self_proposal_feedback": feedback}
            except Exception:
                pass

    cycle = kernel_self.run_reorganization_cycle(
        prediction_error=prediction_error,
        belief_result=belief_result,
        world_model_result=world_model_result,
        experience_result=experience_result,
        source_event_id=source_event_id,
        reorg_mode=reorg_mode,
    )

    recorded = None
    if event_root is not None:
        try:
            from kernel.reorg_event_recorder import record_reorg_event

            recorded = record_reorg_event(
                kernel_self.self_id,
                cycle,
                source_event_id,
                event_root,
            )
        except Exception:
            recorded = {"recorded": False}

    return {
        "status": "processed",
        "cycle": cycle,
        "reorg_event": recorded,
        "pending_reorg": kernel_self.get_pending_reorg_proposals(),
    }