from __future__ import annotations

from typing import Any

from xinyu_bridge_desktop_surface_route_backend import maybe_execute_desktop_surface_backend
from xinyu_bridge_desktop_surface_snapshot_state_backend import desktop_surface_snapshot_state_backend_for_runtime
from xinyu_bridge_desktop_surface_state_store import desktop_surface_state_store_for_runtime
from xinyu_bridge_values import as_int as _as_int
from xinyu_desktop_service import desktop_events_recent as desktop_service_events_recent
from xinyu_desktop_service import desktop_recent_items as desktop_service_recent_items
from xinyu_memory_promotion import list_growth_candidate_promotions


DESKTOP_RECENT_TURNS_MAX = 200
DESKTOP_RECENT_MEMORY_EVENTS_MAX = 200


async def desktop_events_recent(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_desktop_surface_backend(
        runtime,
        payload,
        route="/desktop/events/recent",
        http_method="GET",
        runtime_method="desktop_events_recent",
    )
    if backend_result is not None:
        return backend_result
    return await desktop_service_events_recent(runtime.desktop_event_bus, payload)


async def desktop_chat_recent(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_desktop_surface_backend(
        runtime,
        payload,
        route="/desktop/chat/recent",
        http_method="GET",
        runtime_method="desktop_chat_recent",
    )
    if backend_result is not None:
        return backend_result
    state_store = desktop_surface_state_store_for_runtime(runtime)
    return desktop_service_recent_items(
        state_store.recent_turns(),
        payload,
        default=50,
        maximum=200,
        notes=["desktop_chat_recent_v0_runtime_buffer"],
    )


async def desktop_memory_recent(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_desktop_surface_backend(
        runtime,
        payload,
        route="/desktop/memory/recent",
        http_method="GET",
        runtime_method="desktop_memory_recent",
    )
    if backend_result is not None:
        return backend_result
    state_store = desktop_surface_state_store_for_runtime(runtime)
    return desktop_service_recent_items(
        state_store.recent_memory_events(),
        payload,
        default=100,
        maximum=500,
        notes=["desktop_memory_recent_v0_runtime_buffer"],
    )


async def desktop_memory_growth_candidates(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_desktop_surface_backend(
        runtime,
        payload,
        route="/desktop/memory/growth-candidates",
        http_method="GET",
        runtime_method="desktop_memory_growth_candidates",
    )
    if backend_result is not None:
        return backend_result
    data = payload or {}
    limit = max(1, min(_as_int(data.get("limit"), 50), 200))
    root = desktop_surface_snapshot_state_backend_for_runtime(runtime).root(runtime)
    return list_growth_candidate_promotions(root, limit=limit)


def desktop_remember_turn(runtime: Any, item: dict[str, Any]) -> None:
    desktop_surface_state_store_for_runtime(runtime).remember_turn(item, max_items=DESKTOP_RECENT_TURNS_MAX)


def desktop_remember_memory_event(runtime: Any, item: dict[str, Any]) -> None:
    desktop_surface_state_store_for_runtime(runtime).remember_memory_event(
        item,
        max_items=DESKTOP_RECENT_MEMORY_EVENTS_MAX,
    )
