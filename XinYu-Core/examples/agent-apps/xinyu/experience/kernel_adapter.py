"""Adapter between ExperienceProcessor and Cognitive Kernel Self Model.

This allows high-importance experiences to propose updates to the stable Self.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kernel.self import Self
from kernel.self_change_recorder import record_self_model_change
from .models import ExperienceResult


def apply_experience_to_self_model(
    kernel_self: Self,
    exp_result: ExperienceResult,
    source_event_id: str,
) -> dict[str, Any]:
    """Main entry: feed Experience result into Self Model.

    Returns summary of what was accepted.
    """
    if exp_result.importance_score < 60:
        return {"status": "skipped_low_importance", "score": exp_result.importance_score}

    # Filter self-relevant proposals
    self_relevant = [
        p for p in exp_result.belief_update_proposals
        if p.proposal_type in {"boundary", "self_observation", "preference"}
    ]

    if not self_relevant:
        return {"status": "no_self_relevant_proposals"}

    proposal_result = kernel_self.propose_self_update(
        proposals=self_relevant,  # type: ignore
        importance_score=exp_result.importance_score,
        source_event_id=source_event_id,
    )

    candidates = proposal_result.get("candidates", [])
    if candidates:
        commit_result = kernel_self.commit_self_updates(candidates, source_event_id)
        # Record for traceability (the caller should actually append to event log)
        change_event = record_self_model_change(
            kernel_self,
            "experience_proposal_commit",
            {"commit": commit_result, "importance": exp_result.importance_score},
            Path("."),  # placeholder; real caller passes project root
        )
        return {
            "status": "processed",
            "proposal": proposal_result,
            "commit": commit_result,
            "change_event": change_event,
        }

    return {"status": "no_candidates_after_filter", "proposal": proposal_result}
