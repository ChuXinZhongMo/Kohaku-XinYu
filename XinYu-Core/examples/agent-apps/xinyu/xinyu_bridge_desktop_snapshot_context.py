from __future__ import annotations

from typing import Any, Callable, NamedTuple

from xinyu_bridge_desktop_surface_snapshot_state_backend import (
    desktop_surface_snapshot_state_backend_for_runtime,
)
from xinyu_bridge_desktop_surface_projection_backend import collect_desktop_surface_projection


class DesktopSnapshotContext(NamedTuple):
    event_state: dict[str, Any]
    proactive_items: list[Any]
    proactive_history: list[Any]
    recent_turns: list[Any]
    recent_memory_events: list[Any]
    environment: dict[str, Any]
    entropy_state: dict[str, Any]
    active_desires: list[dict[str, Any]]
    self_choice_public: dict[str, Any]
    action_digest: dict[str, Any]
    health: dict[str, Any]
    initiative_metrics: dict[str, Any]


async def collect_desktop_snapshot_context(
    runtime: Any,
    payload: dict[str, Any],
    *,
    sample_environment_func: Callable[..., dict[str, Any]],
    build_entropy_state_func: Callable[..., Any],
    read_action_digest_func: Callable[..., dict[str, Any]],
) -> DesktopSnapshotContext:
    state_backend = desktop_surface_snapshot_state_backend_for_runtime(runtime)
    root = state_backend.root(runtime)
    await state_backend.prepare_self_choice(runtime)
    self_choice_private = await state_backend.self_choice_private(runtime)
    event_state = await state_backend.event_state(runtime)
    projection = await collect_desktop_surface_projection(runtime, payload)
    proactive_items = projection.proactive_items
    proactive_history = projection.proactive_history
    recent_turns = projection.recent_turns
    recent_memory_events = projection.recent_memory_events
    environment = sample_environment_func(root)
    entropy = build_entropy_state_func(
        environment=environment,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
    )
    entropy_state = entropy.model_dump(mode="json")
    active_desires = await state_backend.active_desires(
        runtime,
        environment=environment,
        entropy_state=entropy,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        self_choice_state=self_choice_private,
    )
    self_choice_public = await state_backend.self_choice_public(runtime)
    action_digest = read_action_digest_func(root, limit=5)
    health = state_backend.health_snapshot(runtime)
    initiative_metrics = (
        health.get("runtime_presence", {}).get("initiative_metrics", {})
        if isinstance(health.get("runtime_presence"), dict)
        else {}
    )
    return DesktopSnapshotContext(
        event_state=event_state,
        proactive_items=proactive_items,
        proactive_history=proactive_history,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        environment=environment,
        entropy_state=entropy_state,
        active_desires=active_desires,
        self_choice_public=self_choice_public,
        action_digest=action_digest,
        health=health,
        initiative_metrics=initiative_metrics,
    )
