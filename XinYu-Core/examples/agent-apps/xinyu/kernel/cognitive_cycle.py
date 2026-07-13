"""Full cognitive cycle orchestrator (K-009).

Closes: Experience → Prediction Error → Belief → World Model → Reorganization
with slow vs fast reorganization modes and persistent cycle state.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ReorgMode = Literal["fast", "slow", "skip"]

_SLOW_ESCALATION_THRESHOLD = 3
_DEFERRED_SLOW_ACTIONS = frozenset({"goal_priority_adjust", "memory_candidate", "self_model_proposal"})


class CognitiveCycleState(BaseModel):
    """Tracks slow-signal accumulation across cycles."""

    self_id: str
    slow_signal_count: int = 0
    last_fast_reorg_event_id: str | None = None
    cycle_count: int = 0
    recent_summaries: list[dict[str, Any]] = Field(default_factory=list)

    def should_escalate_to_fast(self, threshold: int = _SLOW_ESCALATION_THRESHOLD) -> bool:
        return self.slow_signal_count >= threshold

    def record(self, summary: dict[str, Any], mode: ReorgMode) -> None:
        self.cycle_count += 1
        if mode == "slow":
            self.slow_signal_count += 1
        elif mode == "fast":
            self.slow_signal_count = 0
            self.last_fast_reorg_event_id = summary.get("source_event_id")
        self.recent_summaries = ([summary] + self.recent_summaries)[:10]


def classify_reorg_mode(
    importance: int,
    error_magnitude: float,
    cycle_state: CognitiveCycleState | None = None,
    *,
    escalation_threshold: int = _SLOW_ESCALATION_THRESHOLD,
) -> ReorgMode:
    """Classify reorganization urgency from experience + prediction error."""
    if cycle_state and cycle_state.should_escalate_to_fast(escalation_threshold):
        return "fast"
    if importance < 40 and error_magnitude < 0.35:
        return "skip"
    if importance >= 70 or error_magnitude >= 0.65:
        return "fast"
    return "slow"


def run_full_cognitive_cycle(
    kernel_self: Any,
    event_input: dict[str, Any],
    *,
    outcome_reality: str | None = None,
    source_event_id: str = "unknown",
    event_root: Any = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run the complete K-009 cognitive cycle on one experience event."""
    from experience.processor import ExperienceProcessor
    from experience.kernel_adapter import apply_experience_to_self_model
    from experience.prediction_adapter import run_prediction_cycle
    from experience.reorganization_adapter import run_reorganization_cycle

    stages: dict[str, Any] = {}

    exp = ExperienceProcessor().process(event_input)
    stages["experience"] = exp.model_dump()
    importance = exp.importance_score
    reality = (outcome_reality or str(event_input.get("raw_text", ""))).strip()[:300]

    if importance >= 60:
        stages["self_model"] = apply_experience_to_self_model(kernel_self, exp, source_event_id)

    if exp.belief_update_proposals:
        items = [
            {
                "item_id": f"exp-{source_event_id[:12]}-{i}",
                "content": p.content,
                "item_type": "experience",
                "relevance_score": min(0.9, importance / 100.0),
                "source_event_id": source_event_id,
            }
            for i, p in enumerate(exp.belief_update_proposals[:3])
        ]
        kernel_self.update_attention(items=items, from_self_model=True, from_goals=True)
        stages["attention_seed"] = len(items)

    error_mag = importance / 100.0
    belief_result: dict[str, Any] | None = None
    wm_result: dict[str, Any] | None = None
    prediction_error: dict[str, Any] | None = None

    if reality and importance >= 35:
        pred_cycle = run_prediction_cycle(
            kernel_self,
            outcome_reality=reality,
            source_event_id=source_event_id,
            include_reorg=False,
        )
        stages["prediction"] = pred_cycle
        if pred_cycle.get("error"):
            prediction_error = pred_cycle["error"]
            error_mag = float(prediction_error.get("error_magnitude", error_mag))
        belief_result = pred_cycle.get("belief_result")
        wm_result = pred_cycle.get("world_model_result")
    else:
        stages["prediction"] = {"skipped": True, "reason": "low_importance_or_no_reality"}

    cycle_state: CognitiveCycleState = getattr(
        kernel_self, "cognitive_cycle_state", CognitiveCycleState(self_id=kernel_self.self_id)
    )
    escalation_threshold = _SLOW_ESCALATION_THRESHOLD
    if event_root is not None:
        try:
            from .meta_learning import get_slow_escalation_threshold

            escalation_threshold = get_slow_escalation_threshold(event_root)
        except Exception:
            pass
    reorg_mode = classify_reorg_mode(
        importance,
        error_mag,
        cycle_state,
        escalation_threshold=escalation_threshold,
    )
    stages["slow_escalation_threshold"] = escalation_threshold
    stages["reorg_mode"] = reorg_mode

    reorg_result: dict[str, Any] = {"status": "skipped", "reason": "reorg_mode_skip"}
    if reorg_mode != "skip":
        if not prediction_error and reality:
            prediction_error = {
                "error_magnitude": error_mag,
                "reality": reality,
                "source_event_id": source_event_id,
                "impact_on_self": ["identity"] if importance > 75 else [],
            }
        reorg_result = run_reorganization_cycle(
            kernel_self,
            prediction_error=prediction_error,
            belief_result=belief_result,
            world_model_result=wm_result,
            experience_result=exp.model_dump(),
            source_event_id=source_event_id,
            event_root=event_root,
            reorg_mode=reorg_mode,
        )
        stages["reorganization"] = reorg_result

    cycle_summary = {
        "source_event_id": source_event_id,
        "importance": importance,
        "error_magnitude": error_mag,
        "reorg_mode": reorg_mode,
        "cycle_closed": True,
        "structural_impact": (reorg_result.get("cycle") or {}).get("structural_impact", False),
    }
    cycle_state.record(cycle_summary, reorg_mode)
    kernel_self.cognitive_cycle_state = cycle_state

    cycle_event = None
    if event_root is not None:
        try:
            from .cycle_event_recorder import record_cognitive_cycle_event
            from .runtime_self import persist_runtime_self

            cycle_event = record_cognitive_cycle_event(kernel_self.self_id, cycle_summary, stages, event_root)
            if persist:
                persist_runtime_self(kernel_self, event_root)
        except Exception:
            cycle_event = {"recorded": False}

    reorg_cycle = reorg_result.get("cycle") or {}
    story_result = None
    meta_result = None
    if event_root is not None:
        try:
            from .narrative_builder import maybe_update_self_story
            from .meta_learning import record_cycle_meta

            story_result = maybe_update_self_story(
                kernel_self,
                event_root,
                structural_impact=bool(reorg_cycle.get("structural_impact")),
            )
            meta_result = record_cycle_meta(
                event_root,
                reorg_mode=reorg_mode,
                structural_impact=bool(reorg_cycle.get("structural_impact")),
            )
        except Exception:
            story_result = {"updated": False}
            meta_result = None

    return {
        "cycle_closed": True,
        "reorg_mode": reorg_mode,
        "importance": importance,
        "error_magnitude": error_mag,
        "stages": stages,
        "structural_impact": reorg_cycle.get("structural_impact", False),
        "reorg_applied_count": len(reorg_cycle.get("applied", [])),
        "reorg_pending_count": reorg_cycle.get("pending_count", 0),
        "slow_signal_count": cycle_state.slow_signal_count,
        "cycle_count": cycle_state.cycle_count,
        "cycle_event": cycle_event,
        "self_story": story_result,
        "reorg_meta": meta_result,
        "self_snapshot": {
            "working_memory_size": len(kernel_self.get_working_memory()),
            "active_goals": len(kernel_self.get_active_goals()),
            "stable_beliefs": len(kernel_self.get_stable_beliefs(0.6)),
            "world_facts": len(kernel_self.world_model.facts),
            "core_statements": len(kernel_self.get_self_model().get("core_statements", [])),
        },
    }