from __future__ import annotations

from typing import Any

from xinyu_bridge_autonomous_note_results import (
    append_dict_note_result,
    append_note_without_result,
    append_optional_dict_note_result,
)


def append_watched_source_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("watched_source", deps, runtime, notes, checked_at=checked_at)


def append_github_learning_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("github_learning", deps, runtime, notes, checked_at=checked_at)


def append_agent_tech_scout_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("agent_tech_scout", deps, runtime, notes, checked_at=checked_at)


def append_daily_digest_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("daily_digest", deps, runtime, notes, checked_at=checked_at)


def append_creative_writing_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("creative_writing", deps, runtime, notes, checked_at=checked_at)


def append_review_inbox_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("review_inbox", deps, runtime, notes, checked_at=checked_at)


def append_goldmark_dehydrate_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("goldmark_dehydrate", deps, runtime, notes, checked_at=checked_at)


def append_goal_ecology_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("goal_ecology", deps, runtime, notes, checked_at=checked_at)


def append_action_followup_audit_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("action_followup_audit", deps, runtime, notes, checked_at=checked_at)


def append_self_action_gateway_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("self_action_gateway", deps, runtime, notes, checked_at=checked_at)


def append_self_action_patch_executor_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("self_action_patch_executor", deps, runtime, notes, checked_at=checked_at)


def append_self_thought_loop_note(
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
) -> dict[str, Any] | None:
    return append_optional_dict_note_result("self_thought_loop", deps, runtime, notes, checked_at=checked_at)


def append_proactive_request_note(
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
) -> dict[str, Any]:
    return append_dict_note_result("proactive_request", deps, runtime, notes, checked_at=checked_at)


def append_self_exploration_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("self_exploration", deps, runtime, notes, checked_at=checked_at)


def append_learning_closed_loop_self_thought_note(
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    thought: dict[str, Any],
    checked_at: str,
    request: dict[str, Any] | None = None,
) -> None:
    append_note_without_result(
        "learning_closed_loop_self_thought",
        deps,
        runtime,
        notes,
        thought=thought,
        checked_at=checked_at,
        request=request,
    )


def append_autonomous_outward_note(
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    prepare_request: bool,
) -> dict[str, Any]:
    return append_dict_note_result(
        "autonomous_outward",
        deps,
        runtime,
        notes,
        checked_at=checked_at,
        prepare_request=prepare_request,
    )


def append_goal_outcome_observer_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("goal_outcome_observer", deps, runtime, notes, checked_at=checked_at)


def append_proactivity_shadow_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("proactivity_shadow", deps, runtime, notes, checked_at=checked_at)


def append_emotion_council_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("emotion_council", deps, runtime, notes, checked_at=checked_at)


def append_impulse_soup_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("impulse_soup", deps, runtime, notes, checked_at=checked_at)


def append_initiative_spine_note(deps: Any, runtime: Any, notes: list[str], *, checked_at: str) -> None:
    append_note_without_result("initiative_spine", deps, runtime, notes, checked_at=checked_at)
