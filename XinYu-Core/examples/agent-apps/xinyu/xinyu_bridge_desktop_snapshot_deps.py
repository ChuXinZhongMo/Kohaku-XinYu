from __future__ import annotations

from typing import Any, Mapping

from xinyu_bridge_desktop_snapshot_active_deps import desktop_active_desires
from xinyu_bridge_desktop_snapshot_projection_deps import (
    desktop_account_label,
    desktop_creative_writing_state,
    desktop_initiative_metrics_summary,
    desktop_latest_memory_route,
    desktop_memory_route_payload,
    desktop_metric_int,
    desktop_recall_item,
    desktop_session_label,
    desktop_turn_base,
    desktop_xinyu_state,
)
from xinyu_bridge_desktop_snapshot_service_deps import (
    desktop_event_state,
    desktop_services,
    desktop_snapshot,
)
from xinyu_bridge_desktop_snapshot_state import DesktopXinyuStateDeps
from xinyu_bridge_desktop_snapshot_wrapper_deps import (
    desktop_private_ecosystem_snapshot,
    desktop_safe_dict,
    desktop_self_action_snapshot,
)


FacadeDeps = Mapping[str, Any]


def _dep(facade_deps: FacadeDeps, name: str) -> Any:
    return facade_deps[name]


__all__ = [
    "DesktopXinyuStateDeps",
    "FacadeDeps",
    "desktop_account_label",
    "desktop_active_desires",
    "desktop_creative_writing_state",
    "desktop_event_state",
    "desktop_initiative_metrics_summary",
    "desktop_latest_memory_route",
    "desktop_memory_route_payload",
    "desktop_metric_int",
    "desktop_private_ecosystem_snapshot",
    "desktop_recall_item",
    "desktop_safe_dict",
    "desktop_self_action_snapshot",
    "desktop_services",
    "desktop_session_label",
    "desktop_snapshot",
    "desktop_turn_base",
    "desktop_xinyu_state",
]
