from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from xinyu_runtime_presence import DEFAULT_RUNNING_STALE_SECONDS


@dataclass(frozen=True, slots=True)
class HealthDiagnosticsRuntimeContext:
    xinyu_dir: Path
    memory_root: Path
    sessions: int
    turn_timeout_seconds: int
    pre_model_routes_timeout_seconds: int
    outward_renderer: bool
    renderer_mode: str
    render_timeout_seconds: int
    session_idle_ttl_seconds: int
    max_sessions: int
    dialogue_prompt_tail_entries: int
    dialogue_session_tail_entries: int
    dialogue_persisted_tail_entries: int
    proactive_min_interval_seconds: int
    v1: dict[str, Any]
    self_choice: dict[str, Any]
    closed: bool


def health_diagnostics_runtime_context(runtime: Any) -> HealthDiagnosticsRuntimeContext:
    return HealthDiagnosticsRuntimeContext(
        xinyu_dir=Path(runtime.xinyu_dir),
        memory_root=Path(runtime.memory_root),
        sessions=len(runtime._sessions),
        turn_timeout_seconds=runtime.turn_timeout_seconds,
        pre_model_routes_timeout_seconds=runtime.pre_model_routes_timeout_seconds,
        outward_renderer=runtime.outward_renderer,
        renderer_mode=runtime.renderer_mode,
        render_timeout_seconds=runtime.render_timeout_seconds,
        session_idle_ttl_seconds=runtime.session_idle_ttl_seconds,
        max_sessions=runtime.max_sessions,
        dialogue_prompt_tail_entries=runtime.dialogue_prompt_tail_entries,
        dialogue_session_tail_entries=runtime.dialogue_session_tail_entries,
        dialogue_persisted_tail_entries=runtime.dialogue_persisted_tail_entries,
        proactive_min_interval_seconds=runtime.proactive_min_interval_seconds,
        v1=runtime._v1_health(),
        self_choice=runtime.self_choice_store.health_snapshot(),
        closed=runtime._closed,
    )


def build_health_snapshot(
    runtime: Any,
    *,
    bridge_version: str,
    source_digest: str,
    runtime_source_digest: str,
    read_code_awareness_summary_func: Callable[..., dict[str, Any]],
    read_runtime_presence_summary_func: Callable[..., dict[str, Any]],
    read_turn_route_summary_func: Callable[..., dict[str, Any]],
    read_recent_action_digest_snapshot_func: Callable[..., dict[str, Any]],
    autonomous_maintenance_health_func: Callable[[Any], dict[str, Any]],
    metabolism_health_func: Callable[[Any], dict[str, Any]],
    operator_health_func: Callable[..., dict[str, Any]],
    service_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = health_diagnostics_runtime_context(runtime)
    code_awareness = read_code_awareness_summary_func(context.xinyu_dir)
    if code_awareness.get("available"):
        code_awareness = {
            **code_awareness,
            "running_bridge_digest": source_digest,
            "running_runtime_digest": runtime_source_digest,
        }
    runtime_presence = read_runtime_presence_summary_func(context.xinyu_dir)
    turn_route = read_turn_route_summary_func(context.xinyu_dir)
    return build_health_snapshot_from_context(
        context,
        bridge_version=bridge_version,
        source_digest=source_digest,
        runtime_source_digest=runtime_source_digest,
        code_awareness=code_awareness,
        runtime_presence=runtime_presence,
        turn_route=turn_route,
        autonomous_maintenance=autonomous_maintenance_health_func(runtime),
        operator=operator_health_func(runtime_presence=runtime_presence, turn_route=turn_route),
        metabolism=metabolism_health_func(runtime),
        action_experience_digest=read_recent_action_digest_snapshot_func(context.xinyu_dir, limit=3),
        service_health=service_health,
    )


def build_health_snapshot_from_context(
    context: HealthDiagnosticsRuntimeContext,
    *,
    bridge_version: str,
    source_digest: str,
    runtime_source_digest: str,
    code_awareness: dict[str, Any],
    runtime_presence: dict[str, Any],
    turn_route: dict[str, Any],
    autonomous_maintenance: dict[str, Any],
    operator: dict[str, Any],
    metabolism: dict[str, Any],
    action_experience_digest: dict[str, Any],
    service_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = {
        "ok": True,
        "bridge": "xinyu_core_bridge",
        "version": bridge_version,
        "source_digest": source_digest,
        "runtime_source_digest": runtime_source_digest,
        "xinyu_dir": str(context.xinyu_dir),
        "memory_root": str(context.memory_root),
        "sessions": context.sessions,
        "turn_timeout_seconds": context.turn_timeout_seconds,
        "pre_model_routes_timeout_seconds": context.pre_model_routes_timeout_seconds,
        "outward_renderer": context.outward_renderer,
        "renderer_mode": context.renderer_mode,
        "render_timeout_seconds": context.render_timeout_seconds,
        "session_idle_ttl_seconds": context.session_idle_ttl_seconds,
        "max_sessions": context.max_sessions,
        "dialogue_memory": {
            "prompt_tail_entries": context.dialogue_prompt_tail_entries,
            "session_tail_entries": context.dialogue_session_tail_entries,
            "persisted_tail_entries": context.dialogue_persisted_tail_entries,
        },
        "proactive_min_interval_seconds": context.proactive_min_interval_seconds,
        "autonomous_maintenance": autonomous_maintenance,
        "runtime_presence": runtime_presence,
        "turn_route": turn_route,
        "operator": operator,
        "program_awareness": runtime_presence.get("program_awareness", {}),
        "code_awareness": code_awareness,
        "v1": context.v1,
        "metabolism": metabolism,
        "self_choice": context.self_choice,
        "action_experience_digest": action_experience_digest,
        "closed": context.closed,
    }
    if service_health is not None:
        snapshot["service_health"] = service_health
    return snapshot


def build_operator_health(*, runtime_presence: dict[str, Any], turn_route: dict[str, Any]) -> dict[str, Any]:
    current_turn_age_seconds = _safe_int(runtime_presence.get("current_turn_age_seconds"), 0)
    stale_running = bool(runtime_presence.get("stale_running"))
    stale_age_seconds = 0
    if stale_running and current_turn_age_seconds > DEFAULT_RUNNING_STALE_SECONDS:
        stale_age_seconds = current_turn_age_seconds - DEFAULT_RUNNING_STALE_SECONDS
    return {
        "current_turn_state": _safe_str(runtime_presence.get("current_turn_state"), "unknown"),
        "current_turn_age_seconds": current_turn_age_seconds,
        "route_stage": _safe_str(turn_route.get("last_stage"), "unknown"),
        "route": _safe_str(turn_route.get("last_route"), "unknown"),
        "route_status": _safe_str(turn_route.get("last_status"), "unknown"),
        "stale_running": stale_running,
        "stale_age_seconds": stale_age_seconds,
        "last_timeout_stage": _safe_str(turn_route.get("last_timeout_stage")),
        "last_timeout_reason": _safe_str(turn_route.get("last_timeout_reason")),
    }


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
