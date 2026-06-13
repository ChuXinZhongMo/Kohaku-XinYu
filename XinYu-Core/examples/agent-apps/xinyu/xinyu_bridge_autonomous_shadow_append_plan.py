from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_autonomous_shadow_appenders_helpers import ShadowAppendCall
from xinyu_bridge_autonomous_shadow_payloads import (
    contextual_self_observatory_kwargs,
    desire_drive_kwargs,
    initiative_orchestrator_kwargs,
    initiative_spine_kwargs,
    proactivity_shadow_kwargs,
)
from xinyu_bridge_autonomous_shadow_rendering import (
    contextual_self_observatory_summary,
    desire_drive_summary,
    initiative_orchestrator_summary,
    initiative_spine_summary,
    proactivity_shadow_summary,
)


def proactivity_shadow_append_calls(
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    run_proactivity_scorer_shadow_func: Callable[..., dict[str, Any]],
    run_initiative_orchestrator_func: Callable[..., dict[str, Any]],
    publish_initiative_func: Callable[[Any, list[str], dict[str, Any]], None],
) -> tuple[ShadowAppendCall, ...]:
    return (
        ShadowAppendCall(
            note_kind="proactivity_shadow",
            run_func=run_proactivity_scorer_shadow_func,
            kwargs=proactivity_shadow_kwargs(checked_at=checked_at),
            render_summary=proactivity_shadow_summary,
        ),
        ShadowAppendCall(
            note_kind="initiative_orchestrator",
            run_func=run_initiative_orchestrator_func,
            kwargs=initiative_orchestrator_kwargs(checked_at=checked_at),
            render_summary=initiative_orchestrator_summary,
            after_result=lambda initiative: publish_initiative_func(runtime, notes, initiative),
        ),
    )


def initiative_spine_append_calls(
    *,
    checked_at: str,
    run_initiative_spine_func: Callable[..., dict[str, Any]],
    run_desire_drive_state_func: Callable[..., dict[str, Any]],
    run_contextual_self_observatory_func: Callable[..., dict[str, Any]],
    timestamp_or_now_iso_func: Callable[..., str],
) -> tuple[ShadowAppendCall, ...]:
    return (
        ShadowAppendCall(
            note_kind="initiative_spine",
            run_func=run_initiative_spine_func,
            kwargs=initiative_spine_kwargs(checked_at=checked_at),
            render_summary=initiative_spine_summary,
        ),
        ShadowAppendCall(
            note_kind="desire_drive",
            run_func=run_desire_drive_state_func,
            kwargs=desire_drive_kwargs(checked_at=checked_at),
            render_summary=desire_drive_summary,
        ),
        ShadowAppendCall(
            note_kind="contextual_self_observatory",
            run_func=run_contextual_self_observatory_func,
            kwargs=contextual_self_observatory_kwargs(
                checked_at=checked_at,
                timestamp_or_now_iso_func=timestamp_or_now_iso_func,
            ),
            render_summary=contextual_self_observatory_summary,
        ),
    )
