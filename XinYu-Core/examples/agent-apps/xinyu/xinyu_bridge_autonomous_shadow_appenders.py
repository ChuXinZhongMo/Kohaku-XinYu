from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_autonomous_shadow_payloads import (
    emotion_council_kwargs,
    goal_outcome_observer_kwargs,
    impulse_soup_kwargs,
)
from xinyu_bridge_autonomous_shadow_rendering import (
    emotion_council_summary,
    goal_outcome_summary,
    impulse_soup_summary,
    initiative_desktop_notes,
)
from xinyu_bridge_autonomous_shadow_appenders_helpers import (
    append_shadow_result_note,
    append_shadow_result_notes,
)
from xinyu_bridge_autonomous_shadow_append_plan import (
    initiative_spine_append_calls,
    proactivity_shadow_append_calls,
)


def append_goal_outcome_observer_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_goal_outcome_observer_func: Callable[..., dict[str, Any]],
) -> None:
    append_shadow_result_note(
        runtime,
        notes,
        note_kind="goal_outcome",
        run_func=run_goal_outcome_observer_func,
        kwargs=goal_outcome_observer_kwargs(notes, checked_at=checked_at),
        render_summary=goal_outcome_summary,
    )


def append_proactivity_shadow_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_proactivity_scorer_shadow_func: Callable[..., dict[str, Any]],
    run_initiative_orchestrator_func: Callable[..., dict[str, Any]],
) -> None:
    runtime._append_emotion_council_note(notes, checked_at=checked_at)
    append_shadow_result_notes(
        runtime,
        notes,
        proactivity_shadow_append_calls(
            runtime,
            notes,
            checked_at=checked_at,
            run_proactivity_scorer_shadow_func=run_proactivity_scorer_shadow_func,
            run_initiative_orchestrator_func=run_initiative_orchestrator_func,
            publish_initiative_func=publish_initiative_desktop_candidate,
        ),
    )
    runtime._append_impulse_soup_note(notes, checked_at=checked_at)
    runtime._append_initiative_spine_note(notes, checked_at=checked_at)


def publish_initiative_desktop_candidate(runtime: Any, notes: list[str], initiative: dict[str, Any]) -> None:
    desktop_item = initiative.get("desktop_item")
    if not isinstance(desktop_item, dict) or not desktop_item:
        return
    published = runtime._desktop_publish_initiative_candidate_threadsafe(
        desktop_item,
        notes=initiative_desktop_notes(initiative),
    )
    if published:
        notes.append("desktop_initiative_candidate_ready_scheduled")


def append_emotion_council_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_emotion_council_shadow_func: Callable[..., dict[str, Any]],
) -> None:
    append_shadow_result_note(
        runtime,
        notes,
        note_kind="emotion_council",
        run_func=run_emotion_council_shadow_func,
        kwargs=emotion_council_kwargs(checked_at=checked_at),
        render_summary=emotion_council_summary,
    )


def append_impulse_soup_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_impulse_soup_func: Callable[..., dict[str, Any]],
) -> None:
    append_shadow_result_note(
        runtime,
        notes,
        note_kind="impulse_soup",
        run_func=run_impulse_soup_func,
        kwargs=impulse_soup_kwargs(checked_at=checked_at),
        render_summary=impulse_soup_summary,
    )


def append_initiative_spine_note(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_initiative_spine_func: Callable[..., dict[str, Any]],
    run_desire_drive_state_func: Callable[..., dict[str, Any]],
    run_contextual_self_observatory_func: Callable[..., dict[str, Any]],
    timestamp_or_now_iso_func: Callable[..., str],
) -> None:
    append_shadow_result_notes(
        runtime,
        notes,
        initiative_spine_append_calls(
            checked_at=checked_at,
            run_initiative_spine_func=run_initiative_spine_func,
            run_desire_drive_state_func=run_desire_drive_state_func,
            run_contextual_self_observatory_func=run_contextual_self_observatory_func,
            timestamp_or_now_iso_func=timestamp_or_now_iso_func,
        ),
    )
