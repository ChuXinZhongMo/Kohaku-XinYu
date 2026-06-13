from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from xinyu_bridge_desktop_snapshot_labels import (
    desktop_account_label as _project_desktop_account_label,
    desktop_session_label as _project_desktop_session_label,
)
from xinyu_bridge_desktop_snapshot_projection import (
    desktop_creative_writing_state as _project_desktop_creative_writing_state,
    desktop_initiative_metrics_summary as _project_desktop_initiative_metrics_summary,
    desktop_latest_memory_route as _project_desktop_latest_memory_route,
    desktop_memory_route_payload as _project_desktop_memory_route_payload,
    desktop_metric_int as _project_desktop_metric_int,
    desktop_recall_item as _project_desktop_recall_item,
    desktop_turn_base as _project_desktop_turn_base,
)
from xinyu_bridge_desktop_snapshot_state import (
    DesktopXinyuStateDeps,
    desktop_xinyu_state as _project_desktop_xinyu_state,
)


FacadeDeps = Mapping[str, Any]


def _dep(facade_deps: FacadeDeps, name: str) -> Any:
    return facade_deps[name]


def desktop_metric_int(value: Any, *, facade_deps: FacadeDeps) -> int:
    return _project_desktop_metric_int(value, safe_str_func=_dep(facade_deps, "safe_str"))


def desktop_initiative_metrics_summary(metrics: dict[str, Any], *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return _project_desktop_initiative_metrics_summary(
        metrics,
        safe_str_func=_dep(facade_deps, "safe_str"),
        metric_int_func=_dep(facade_deps, "desktop_metric_int"),
    )


def desktop_latest_memory_route(recent_memory_events: list[Any], *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return _project_desktop_latest_memory_route(
        recent_memory_events,
        safe_str_func=_dep(facade_deps, "safe_str"),
    )


def desktop_creative_writing_state(root: Path, *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return _project_desktop_creative_writing_state(
        root,
        creative_writing_state_rel=_dep(facade_deps, "CREATIVE_WRITING_STATE_REL"),
        read_text_safe_func=_dep(facade_deps, "read_text_safe"),
        state_field_func=_dep(facade_deps, "state_field"),
        metric_int_func=_dep(facade_deps, "desktop_metric_int"),
    )


def desktop_xinyu_state(
    runtime: Any,
    *,
    environment: dict[str, Any],
    entropy_state: dict[str, Any],
    active_desires: list[dict[str, Any]],
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    action_digest: dict[str, Any] | None,
    initiative_metrics: dict[str, Any] | None,
    facade_deps: FacadeDeps,
) -> dict[str, Any]:
    return _project_desktop_xinyu_state(
        runtime.xinyu_dir,
        environment=environment,
        entropy_state=entropy_state,
        active_desires=active_desires,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        action_digest=action_digest,
        initiative_metrics=initiative_metrics,
        deps=DesktopXinyuStateDeps(
            safe_str_func=_dep(facade_deps, "safe_str"),
            compact_text_func=_dep(facade_deps, "compact_text"),
            desktop_action_theme_label_func=_dep(facade_deps, "desktop_action_theme_label"),
            desktop_action_result_label_func=_dep(facade_deps, "desktop_action_result_label"),
            desktop_action_pressure_label_func=_dep(facade_deps, "desktop_action_pressure_label"),
            desktop_latest_memory_route_func=_dep(facade_deps, "desktop_latest_memory_route"),
            desktop_creative_writing_state_func=_dep(facade_deps, "desktop_creative_writing_state"),
            desktop_initiative_metrics_summary_func=_dep(facade_deps, "desktop_initiative_metrics_summary"),
        ),
    )


def desktop_memory_route_payload(route_plan: Any | None, *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return _project_desktop_memory_route_payload(route_plan, safe_str_func=_dep(facade_deps, "safe_str"))


def desktop_recall_item(item: Any, *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return _project_desktop_recall_item(
        item,
        safe_str_func=_dep(facade_deps, "safe_str"),
        desktop_text_preview_func=_dep(facade_deps, "desktop_text_preview"),
        desktop_hash_func=_dep(facade_deps, "desktop_hash"),
    )


def desktop_session_label(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_kind: str,
    metadata: dict[str, Any],
    facade_deps: FacadeDeps,
) -> str:
    return _project_desktop_session_label(
        runtime,
        payload,
        session_kind=session_kind,
        metadata=metadata,
        safe_str_func=_dep(facade_deps, "safe_str"),
        as_bool_func=_dep(facade_deps, "as_bool"),
    )


def desktop_account_label(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_kind: str,
    metadata: dict[str, Any],
    user_display_id: str,
    group_display_id: str,
    facade_deps: FacadeDeps,
) -> str:
    return _project_desktop_account_label(
        runtime,
        payload,
        session_kind=session_kind,
        metadata=metadata,
        user_display_id=user_display_id,
        group_display_id=group_display_id,
        safe_str_func=_dep(facade_deps, "safe_str"),
        as_bool_func=_dep(facade_deps, "as_bool"),
    )


def desktop_turn_base(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_key: str,
    turn_id: str,
    facade_deps: FacadeDeps,
) -> dict[str, Any]:
    return _project_desktop_turn_base(
        runtime,
        payload,
        session_key=session_key,
        turn_id=turn_id,
        safe_str_func=_dep(facade_deps, "safe_str"),
        as_bool_func=_dep(facade_deps, "as_bool"),
    )
