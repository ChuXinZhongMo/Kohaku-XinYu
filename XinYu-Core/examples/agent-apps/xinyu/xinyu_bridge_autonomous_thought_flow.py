from __future__ import annotations

from typing import Any

from xinyu_bridge_autonomous_note_responses import self_thought_research_summary
from xinyu_bridge_values import as_bool


_BASE_THOUGHT_SIDECAR_METHODS = (
    "_append_watched_source_note",
    "_append_github_learning_note",
    "_append_daily_digest_note",
    "_append_creative_writing_note",
    "_append_review_inbox_note",
    "_append_goldmark_dehydrate_note",
    "_append_goal_ecology_note",
    "_append_private_ecosystem_note",
    "_append_self_action_gateway_note",
    "_append_self_action_patch_executor_note",
)


def _append_base_thought_sidecar_notes(runtime: Any, notes: list[str], *, checked_at: str) -> None:
    for method_name in _BASE_THOUGHT_SIDECAR_METHODS:
        getattr(runtime, method_name)(notes, checked_at=checked_at)


def append_self_thought_research_notes(
    runtime: Any,
    notes: list[str],
    *,
    thought: dict[str, Any],
    checked_at: str,
) -> None:
    notes.append(self_thought_research_summary(thought))
    notes.extend(
        runtime._maybe_run_self_thought_external_plugin(
            thought=thought,
            checked_at=checked_at,
        )
    )
    runtime._append_self_exploration_note(notes, checked_at=checked_at)


def append_autonomous_outcome_shadow_notes(runtime: Any, notes: list[str], *, checked_at: str) -> None:
    runtime._append_goal_outcome_observer_note(notes, checked_at=checked_at)
    runtime._append_proactivity_shadow_note(notes, checked_at=checked_at)


def run_autonomous_self_thought_sidecars(runtime: Any, *, checked_at: str) -> list[str]:
    notes: list[str] = []
    _append_base_thought_sidecar_notes(runtime, notes, checked_at=checked_at)
    thought = runtime._append_self_thought_loop_note(notes, checked_at=checked_at)
    if thought is None:
        runtime._append_autonomous_outcome_shadow_notes(notes, checked_at=checked_at)
        return notes

    if not as_bool(thought.get("candidate_enabled"), default=False):
        if as_bool(thought.get("research_needed"), default=False):
            runtime._append_self_thought_research_notes(notes, thought=thought, checked_at=checked_at)
        runtime._append_learning_closed_loop_self_thought_note(notes, thought=thought, checked_at=checked_at)
        runtime._append_autonomous_outward_note(notes, checked_at=checked_at, prepare_request=True)
        runtime._append_autonomous_outcome_shadow_notes(notes, checked_at=checked_at)
        return notes

    request = runtime._append_proactive_request_note(notes, checked_at=checked_at)
    auto_outward = runtime._append_autonomous_outward_note(notes, checked_at=checked_at, prepare_request=False)
    runtime._append_desktop_proactive_candidate_ready_note(
        notes,
        request=request,
        auto_outward=auto_outward,
    )
    runtime._append_learning_closed_loop_self_thought_note(
        notes,
        thought=thought,
        checked_at=checked_at,
        request=request,
    )
    runtime._append_autonomous_outcome_shadow_notes(notes, checked_at=checked_at)
    return notes

