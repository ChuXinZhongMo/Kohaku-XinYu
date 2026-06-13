from __future__ import annotations

from typing import Any, Callable


def record_runtime_startup_traces(
    runtime: Any,
    *,
    started_at_seconds: float,
    build_startup_bridge_snapshot_func: Callable[..., dict[str, Any]],
    build_startup_route_payload_func: Callable[[float], dict[str, Any]],
    record_bridge_heartbeat_func: Callable[..., Any],
    record_turn_route_stage_func: Callable[..., Any],
) -> None:
    record_bridge_heartbeat_func(
        runtime.xinyu_dir,
        reason="bridge_init",
        bridge_snapshot=build_startup_bridge_snapshot_func(
            active_sessions=len(runtime._sessions),
            autonomous_maintenance_enabled=runtime.autonomous_maintenance_enabled,
        ),
    )
    record_turn_route_stage_func(
        runtime.xinyu_dir,
        **build_startup_route_payload_func(started_at_seconds),
    )
