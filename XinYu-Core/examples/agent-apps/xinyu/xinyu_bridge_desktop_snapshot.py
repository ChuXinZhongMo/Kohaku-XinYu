from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from stores.self_action_queue import APPROVAL_QUEUE_REL as SELF_ACTION_APPROVAL_QUEUE_REL
from stores.self_action_queue import read_approval_queue_events
from xinyu_action_experience_digest import read_recent_action_digest_snapshot
from xinyu_bridge_desktop_actions import desktop_action_pressure_label
from xinyu_bridge_desktop_actions import desktop_action_result_label
from xinyu_bridge_desktop_actions import desktop_action_theme_label
from xinyu_bridge_desktop_projection import desktop_hash, desktop_text_preview
import xinyu_bridge_desktop_snapshot_deps as _snapshot_deps
from xinyu_bridge_desktop_snapshot_state import DesktopXinyuStateDeps
from xinyu_bridge_desktop_surface_route_backend import maybe_execute_desktop_surface_backend
from xinyu_bridge_state_text import read_text_safe, state_field
from xinyu_bridge_values import as_bool, compact_text, safe_str
from xinyu_browser_control import build_browser_snapshot
from xinyu_computer_control import build_computer_snapshot
from xinyu_desktop_service import desktop_event_state as desktop_service_event_state
from xinyu_desktop_service import desktop_services as desktop_service_services
from xinyu_environment_sensor import sample_environment
from xinyu_life_kernel import build_entropy_state, evaluate_life_kernel
from xinyu_metabolism_contract import create_ticket as create_metabolism_ticket
from xinyu_private_ecosystem import build_private_ecosystem_snapshot


SELF_ACTION_GATEWAY_STATE_REL = Path("runtime/self_action_gateway/state.json")
SELF_ACTION_APPROVAL_HANDOFF_REL = Path("memory/context/self_action_gateway_execution_handoff.md")
SELF_ACTION_PATCH_STATE_REL = Path("runtime/self_action_patch_executor/state.json")
SELF_ACTION_PATCH_TASK_MD_REL = Path("memory/context/self_action_patch_executor_task.md")
CREATIVE_WRITING_STATE_REL = Path("memory/creative/planning/novel_state.md")


def desktop_metric_int(value: Any) -> int:
    return _snapshot_deps.desktop_metric_int(value, facade_deps=globals())


def desktop_initiative_metrics_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    return _snapshot_deps.desktop_initiative_metrics_summary(metrics, facade_deps=globals())


async def desktop_event_state(runtime: Any) -> dict[str, Any]:
    return await _snapshot_deps.desktop_event_state(runtime, facade_deps=globals())


def desktop_services(runtime: Any) -> list[dict[str, Any]]:
    return _snapshot_deps.desktop_services(runtime, facade_deps=globals())


def desktop_latest_memory_route(recent_memory_events: list[Any]) -> dict[str, Any]:
    return _snapshot_deps.desktop_latest_memory_route(recent_memory_events, facade_deps=globals())


def desktop_creative_writing_state(root: Path) -> dict[str, Any]:
    return _snapshot_deps.desktop_creative_writing_state(root, facade_deps=globals())


def desktop_xinyu_state(
    runtime: Any,
    *,
    environment: dict[str, Any],
    entropy_state: dict[str, Any],
    active_desires: list[dict[str, Any]],
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    action_digest: dict[str, Any] | None = None,
    initiative_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _snapshot_deps.desktop_xinyu_state(
        runtime,
        environment=environment,
        entropy_state=entropy_state,
        active_desires=active_desires,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        action_digest=action_digest,
        initiative_metrics=initiative_metrics,
        facade_deps=globals(),
    )


def desktop_memory_route_payload(route_plan: Any | None) -> dict[str, Any]:
    return _snapshot_deps.desktop_memory_route_payload(route_plan, facade_deps=globals())


def desktop_recall_item(item: Any) -> dict[str, Any]:
    return _snapshot_deps.desktop_recall_item(item, facade_deps=globals())


def desktop_session_label(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_kind: str,
    metadata: dict[str, Any],
) -> str:
    return _snapshot_deps.desktop_session_label(
        runtime,
        payload,
        session_kind=session_kind,
        metadata=metadata,
        facade_deps=globals(),
    )


def desktop_account_label(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session_kind: str,
    metadata: dict[str, Any],
    user_display_id: str,
    group_display_id: str,
) -> str:
    return _snapshot_deps.desktop_account_label(
        runtime,
        payload,
        session_kind=session_kind,
        metadata=metadata,
        user_display_id=user_display_id,
        group_display_id=group_display_id,
        facade_deps=globals(),
    )


async def desktop_active_desires(
    runtime: Any,
    *,
    environment: dict[str, Any],
    entropy_state: Any,
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    self_choice_state: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return await _snapshot_deps.desktop_active_desires(
        runtime,
        environment=environment,
        entropy_state=entropy_state,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        self_choice_state=self_choice_state,
        facade_deps=globals(),
    )


def desktop_turn_base(runtime: Any, payload: dict[str, Any], *, session_key: str, turn_id: str) -> dict[str, Any]:
    return _snapshot_deps.desktop_turn_base(
        runtime,
        payload,
        session_key=session_key,
        turn_id=turn_id,
        facade_deps=globals(),
    )


def desktop_self_action_snapshot(root: Path) -> dict[str, Any]:
    return _snapshot_deps.desktop_self_action_snapshot(root, facade_deps=globals())


def _desktop_safe_dict(value: Any) -> dict[str, Any]:
    return _snapshot_deps.desktop_safe_dict(value)


def desktop_private_ecosystem_snapshot(root: Path) -> dict[str, Any]:
    return _snapshot_deps.desktop_private_ecosystem_snapshot(root, facade_deps=globals())


async def desktop_snapshot(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_desktop_surface_backend(
        runtime,
        payload,
        route="/desktop/snapshot",
        http_method="GET",
        runtime_method="desktop_snapshot",
    )
    if backend_result is not None:
        return backend_result
    return await _snapshot_deps.desktop_snapshot(runtime, payload, facade_deps=globals())
