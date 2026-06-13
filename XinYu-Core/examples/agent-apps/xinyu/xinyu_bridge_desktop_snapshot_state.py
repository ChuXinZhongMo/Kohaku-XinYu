from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_desktop_snapshot_state_payload import (
    DesktopXinyuStatePayload,
    build_desktop_xinyu_state_payload,
)
from xinyu_bridge_desktop_snapshot_state_projection import (
    DesktopActionResidueProjection,
    project_action_residue,
    project_desktop_xinyu_state,
)


@dataclass(frozen=True)
class DesktopXinyuStateDeps:
    safe_str_func: Callable[..., str]
    compact_text_func: Callable[..., str]
    desktop_action_theme_label_func: Callable[[str], str]
    desktop_action_result_label_func: Callable[[str], str]
    desktop_action_pressure_label_func: Callable[[str], str]
    desktop_latest_memory_route_func: Callable[[list[Any]], dict[str, Any]]
    desktop_creative_writing_state_func: Callable[[Any], dict[str, Any]]
    desktop_initiative_metrics_summary_func: Callable[[dict[str, Any]], dict[str, Any]]


def desktop_xinyu_state(
    root: Path,
    *,
    environment: dict[str, Any],
    entropy_state: dict[str, Any],
    active_desires: list[dict[str, Any]],
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    deps: DesktopXinyuStateDeps,
    action_digest: dict[str, Any] | None = None,
    initiative_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_desktop_xinyu_state_payload(
        environment=environment,
        entropy_state=entropy_state,
        active_desires=active_desires,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        action_digest=action_digest,
        initiative_metrics=initiative_metrics,
    )
    return project_desktop_xinyu_state(
        payload,
        latest_memory_route=deps.desktop_latest_memory_route_func(recent_memory_events),
        creative_writing_state=deps.desktop_creative_writing_state_func(root),
        safe_str_func=deps.safe_str_func,
        compact_text_func=deps.compact_text_func,
        desktop_action_theme_label_func=deps.desktop_action_theme_label_func,
        desktop_action_result_label_func=deps.desktop_action_result_label_func,
        desktop_action_pressure_label_func=deps.desktop_action_pressure_label_func,
        desktop_initiative_metrics_summary_func=deps.desktop_initiative_metrics_summary_func,
    )


__all__ = [
    "DesktopActionResidueProjection",
    "DesktopXinyuStateDeps",
    "DesktopXinyuStatePayload",
    "build_desktop_xinyu_state_payload",
    "desktop_xinyu_state",
    "project_action_residue",
    "project_desktop_xinyu_state",
]
