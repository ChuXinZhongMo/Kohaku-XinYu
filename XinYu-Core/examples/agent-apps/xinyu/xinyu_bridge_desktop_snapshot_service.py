from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from xinyu_bridge_desktop_snapshot_context import collect_desktop_snapshot_context
from xinyu_bridge_desktop_surface_snapshot_state_backend import (
    desktop_surface_snapshot_state_backend_for_runtime,
)


async def desktop_snapshot(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    sample_environment_func: Callable[..., dict[str, Any]],
    build_entropy_state_func: Callable[..., Any],
    read_action_digest_func: Callable[..., dict[str, Any]],
    self_action_snapshot_func: Callable[..., dict[str, Any]],
    private_ecosystem_snapshot_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    payload = payload or {}
    state_backend = desktop_surface_snapshot_state_backend_for_runtime(runtime)
    context = await collect_desktop_snapshot_context(
        runtime,
        payload,
        sample_environment_func=sample_environment_func,
        build_entropy_state_func=build_entropy_state_func,
        read_action_digest_func=read_action_digest_func,
    )
    return {
        "version": 1,
        "snapshotAt": datetime.now().astimezone().isoformat(),
        "lastEventId": context.event_state.get("latest_event_id", ""),
        "services": state_backend.services(runtime),
        "health": context.health,
        "environment": context.environment,
        "entropyState": context.entropy_state,
        "selfChoiceState": context.self_choice_public,
        "activeDesires": context.active_desires,
        "xinyuState": state_backend.xinyu_state(
            runtime,
            environment=context.environment,
            entropy_state=context.entropy_state,
            active_desires=context.active_desires,
            proactive_items=context.proactive_items,
            recent_turns=context.recent_turns,
            recent_memory_events=context.recent_memory_events,
            action_digest=context.action_digest,
            initiative_metrics=context.initiative_metrics,
        ),
        "eventBus": context.event_state,
        "proactiveInbox": context.proactive_items,
        "proactiveHistory": context.proactive_history,
        "recentTurns": context.recent_turns,
        "recentMemoryEvents": context.recent_memory_events,
        "actionDigestState": context.action_digest,
        "selfAction": state_backend.self_action_snapshot(runtime, self_action_snapshot_func),
        "privateEcosystem": state_backend.private_ecosystem_snapshot(runtime, private_ecosystem_snapshot_func),
        "notes": ["desktop_snapshot_v1_life_state"],
    }
