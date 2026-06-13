from __future__ import annotations

from typing import Any, Mapping

from xinyu_bridge_desktop_service_status_store import desktop_service_path_exists
from xinyu_bridge_desktop_snapshot_service import desktop_snapshot as _runtime_desktop_snapshot


FacadeDeps = Mapping[str, Any]


def _dep(facade_deps: FacadeDeps, name: str) -> Any:
    return facade_deps[name]


async def desktop_event_state(runtime: Any, *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return await _dep(facade_deps, "desktop_service_event_state")(runtime.desktop_event_bus)


def desktop_services(runtime: Any, *, facade_deps: FacadeDeps) -> list[dict[str, Any]]:
    return _dep(facade_deps, "desktop_service_services")(
        ws_server=runtime.desktop_ws_server,
        closed=runtime._closed,
        memory_root_exists=desktop_service_path_exists(runtime.memory_root),
    )


async def desktop_snapshot(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    facade_deps: FacadeDeps,
) -> dict[str, Any]:
    return await _runtime_desktop_snapshot(
        runtime,
        payload,
        sample_environment_func=_dep(facade_deps, "sample_environment"),
        build_entropy_state_func=_dep(facade_deps, "build_entropy_state"),
        read_action_digest_func=_dep(facade_deps, "read_recent_action_digest_snapshot"),
        self_action_snapshot_func=_dep(facade_deps, "desktop_self_action_snapshot"),
        private_ecosystem_snapshot_func=_dep(facade_deps, "desktop_private_ecosystem_snapshot"),
    )
