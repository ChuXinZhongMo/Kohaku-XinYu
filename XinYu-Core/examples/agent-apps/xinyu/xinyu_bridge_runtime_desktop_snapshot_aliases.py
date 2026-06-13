from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_snapshot


def install_desktop_snapshot_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.desktop_snapshot = xinyu_bridge_desktop_snapshot.desktop_snapshot
    runtime_cls._desktop_active_desires = xinyu_bridge_desktop_snapshot.desktop_active_desires
    runtime_cls._desktop_xinyu_state = xinyu_bridge_desktop_snapshot.desktop_xinyu_state
    runtime_cls._desktop_latest_memory_route = staticmethod(xinyu_bridge_desktop_snapshot.desktop_latest_memory_route)
    runtime_cls._desktop_initiative_metrics_summary = staticmethod(
        xinyu_bridge_desktop_snapshot.desktop_initiative_metrics_summary
    )
    runtime_cls._desktop_metric_int = staticmethod(xinyu_bridge_desktop_snapshot.desktop_metric_int)
    runtime_cls._desktop_event_state = xinyu_bridge_desktop_snapshot.desktop_event_state
    runtime_cls._desktop_services = xinyu_bridge_desktop_snapshot.desktop_services
    runtime_cls._desktop_recall_item = staticmethod(xinyu_bridge_desktop_snapshot.desktop_recall_item)
    runtime_cls._desktop_memory_route_payload = staticmethod(xinyu_bridge_desktop_snapshot.desktop_memory_route_payload)
    runtime_cls._desktop_turn_base = xinyu_bridge_desktop_snapshot.desktop_turn_base
    runtime_cls._desktop_session_label = xinyu_bridge_desktop_snapshot.desktop_session_label
    runtime_cls._desktop_account_label = xinyu_bridge_desktop_snapshot.desktop_account_label
