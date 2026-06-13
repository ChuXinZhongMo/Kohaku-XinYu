from __future__ import annotations

from typing import Any, Mapping

from xinyu_bridge_desktop_active_desires import desktop_active_desires as _runtime_desktop_active_desires


FacadeDeps = Mapping[str, Any]


def _dep(facade_deps: FacadeDeps, name: str) -> Any:
    return facade_deps[name]


async def desktop_active_desires(
    runtime: Any,
    *,
    environment: dict[str, Any],
    entropy_state: Any,
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    self_choice_state: dict[str, Any] | None,
    facade_deps: FacadeDeps,
) -> list[dict[str, Any]]:
    return await _runtime_desktop_active_desires(
        runtime,
        environment=environment,
        entropy_state=entropy_state,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        self_choice_state=self_choice_state,
        evaluate_life_kernel_func=_dep(facade_deps, "evaluate_life_kernel"),
        create_metabolism_ticket_func=_dep(facade_deps, "create_metabolism_ticket"),
        to_thread_func=_dep(facade_deps, "asyncio").to_thread,
        safe_str_func=_dep(facade_deps, "safe_str"),
    )
