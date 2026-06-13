from __future__ import annotations

from typing import Any, Callable, Mapping

import xinyu_bridge_desktop_proactive_bindings as _proactive_bindings
from xinyu_bridge_desktop_surface_route_backend import maybe_execute_desktop_surface_backend


DepsProvider = Callable[[], Any]
FacadeProvider = Callable[[], Mapping[str, Any]]


def build_desktop_proactive_inbox_facade(
    *,
    deps_provider: DepsProvider,
    facade_provider: FacadeProvider,
) -> dict[str, Callable[..., Any]]:
    async def desktop_proactive_inbox(
        runtime: Any,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        backend_result = await maybe_execute_desktop_surface_backend(
            runtime,
            payload,
            route="/desktop/proactive/inbox",
            http_method="GET",
            runtime_method="desktop_proactive_inbox",
        )
        if backend_result is not None:
            return backend_result
        return await _proactive_bindings.desktop_proactive_inbox(runtime, payload, deps=deps_provider())

    def desktop_proactive_item_from_state(runtime: Any, *, include_final: bool = False) -> dict[str, Any]:
        return _proactive_bindings.desktop_proactive_item_from_state(
            runtime,
            include_final=include_final,
            deps=deps_provider(),
        )

    def desktop_proactive_existing(runtime: Any, candidate_id: str) -> dict[str, Any]:
        return _proactive_bindings.desktop_proactive_existing(runtime, candidate_id)

    def desktop_upsert_proactive_inbox(runtime: Any, item: dict[str, Any]) -> None:
        _proactive_bindings.desktop_upsert_proactive_inbox(runtime, item, deps=deps_provider())

    def desktop_remove_proactive_inbox(runtime: Any, candidate_id: str) -> None:
        _proactive_bindings.desktop_remove_proactive_inbox(runtime, candidate_id)

    def desktop_remove_proactive_state_items(runtime: Any) -> None:
        _proactive_bindings.desktop_remove_proactive_state_items(runtime, deps=deps_provider())

    def desktop_clear_proactive_inbox(runtime: Any) -> None:
        _proactive_bindings.desktop_clear_proactive_inbox(runtime)

    def desktop_prune_proactive_inbox(runtime: Any) -> None:
        _proactive_bindings.desktop_prune_proactive_inbox(runtime, deps=deps_provider())

    def desktop_remember_proactive_history(runtime: Any, item: dict[str, Any]) -> None:
        _proactive_bindings.desktop_remember_proactive_history(
            runtime,
            item,
            compact_history=facade_provider()["desktop_compact_proactive_history"],
            deps=deps_provider(),
        )

    def desktop_load_proactive_history(runtime: Any) -> None:
        _proactive_bindings.desktop_load_proactive_history(
            runtime,
            compact_history=facade_provider()["desktop_compact_proactive_history"],
            deps=deps_provider(),
        )

    def desktop_compact_proactive_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return _proactive_bindings.desktop_compact_proactive_history(rows, deps=deps_provider())

    def desktop_current_proactive_question(runtime: Any, item: dict[str, Any]) -> str:
        return _proactive_bindings.desktop_current_proactive_question(runtime, item, deps=deps_provider())

    return {
        "desktop_proactive_inbox": desktop_proactive_inbox,
        "desktop_proactive_item_from_state": desktop_proactive_item_from_state,
        "desktop_proactive_existing": desktop_proactive_existing,
        "desktop_upsert_proactive_inbox": desktop_upsert_proactive_inbox,
        "desktop_remove_proactive_inbox": desktop_remove_proactive_inbox,
        "desktop_remove_proactive_state_items": desktop_remove_proactive_state_items,
        "desktop_clear_proactive_inbox": desktop_clear_proactive_inbox,
        "desktop_prune_proactive_inbox": desktop_prune_proactive_inbox,
        "desktop_remember_proactive_history": desktop_remember_proactive_history,
        "desktop_load_proactive_history": desktop_load_proactive_history,
        "desktop_compact_proactive_history": desktop_compact_proactive_history,
        "desktop_current_proactive_question": desktop_current_proactive_question,
    }
