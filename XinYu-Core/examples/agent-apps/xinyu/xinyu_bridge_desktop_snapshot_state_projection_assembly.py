from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_desktop_snapshot_state_payload import DesktopXinyuStatePayload
from xinyu_bridge_desktop_snapshot_state_projection_action import (
    DesktopActionResidueProjection,
    project_action_residue,
)
from xinyu_bridge_desktop_snapshot_state_projection_attention import project_current_attention
from xinyu_bridge_desktop_snapshot_state_projection_concern import project_recent_concerns
from xinyu_bridge_desktop_snapshot_state_projection_mood import project_mood_tag
from xinyu_bridge_desktop_snapshot_state_projection_physical import project_physical_sensation


def _entropy_fields(payload: DesktopXinyuStatePayload, *, safe_str_func: Callable[..., str]) -> dict[str, Any]:
    entropy_state = payload.entropy_state
    return {
        "entropy_level": entropy_state.get("entropy_level", 0.0),
        "entropy_band": safe_str_func(entropy_state.get("entropy_band"), "clear"),
        "scar_level": entropy_state.get("scar_level", 0.0),
        "memory_decay_risk": entropy_state.get("memory_decay_risk", 0.0),
        "metabolism_needed": bool(entropy_state.get("metabolism_needed")),
        "entropy_visible_artifact": safe_str_func(entropy_state.get("visible_artifact"), ""),
    }


def _memory_route_fields(latest_memory_route: dict[str, Any], *, safe_str_func: Callable[..., str]) -> dict[str, Any]:
    return {
        "latest_memory_route_summary": safe_str_func(latest_memory_route.get("summary")),
        "latest_memory_route_experts": latest_memory_route.get("selectedExperts", []),
        "latest_memory_current_turn_facts": latest_memory_route.get("currentTurnFacts", []),
    }


def _action_fields(action: DesktopActionResidueProjection, digested_count: int) -> dict[str, Any]:
    return {
        "action_experience_count": digested_count,
        "action_residue_label": action.label,
        "action_residue_route": action.route,
        "action_residue_pressure": action.pressure if action.seed_id else "",
        "action_residue_result": action.result if action.seed_id else "",
        "action_residue_seed_id": action.seed_id,
        "action_residue_reflection_item_id": action.reflection_item_id,
    }


def project_desktop_xinyu_state(
    payload: DesktopXinyuStatePayload,
    *,
    latest_memory_route: dict[str, Any],
    creative_writing_state: dict[str, Any],
    safe_str_func: Callable[..., str],
    compact_text_func: Callable[..., str],
    desktop_action_theme_label_func: Callable[[str], str],
    desktop_action_result_label_func: Callable[[str], str],
    desktop_action_pressure_label_func: Callable[[str], str],
    desktop_initiative_metrics_summary_func: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    action = project_action_residue(
        payload,
        safe_str_func=safe_str_func,
        compact_text_func=compact_text_func,
        desktop_action_theme_label_func=desktop_action_theme_label_func,
        desktop_action_result_label_func=desktop_action_result_label_func,
        desktop_action_pressure_label_func=desktop_action_pressure_label_func,
    )
    pressure = safe_str_func(payload.sensation.get("pressure"), "unknown")
    active_desire = payload.active_desire
    return {
        "version": 1,
        "mood_tag": project_mood_tag(payload, action, pressure=pressure, safe_str_func=safe_str_func),
        "current_attention": project_current_attention(
            payload,
            action,
            safe_str_func=safe_str_func,
            compact_text_func=compact_text_func,
        ),
        "recent_concerns": project_recent_concerns(
            payload,
            action,
            safe_str_func=safe_str_func,
            compact_text_func=compact_text_func,
        ),
        "is_waiting_for_reply": payload.waiting,
        "physical_sensation": project_physical_sensation(
            payload,
            action,
            safe_str_func=safe_str_func,
            compact_text_func=compact_text_func,
        ),
        "physical_sensation_tag": safe_str_func(payload.sensation.get("tag"), "unfelt"),
        "physical_pressure": pressure,
        "environment_sensor_quality": safe_str_func(payload.environment.get("sensorQuality"), "unknown"),
        "recent_memory_echoes": payload.recent_memory_echoes,
        **_entropy_fields(payload, safe_str_func=safe_str_func),
        **_memory_route_fields(latest_memory_route, safe_str_func=safe_str_func),
        "resource_request": payload.resource_request,
        "metabolism_ticket_id": safe_str_func(active_desire.get("metabolism_ticket_id")),
        "metabolism_ticket_status": safe_str_func(active_desire.get("metabolism_ticket_status")),
        **_action_fields(action, payload.digested_count),
        **creative_writing_state,
        "initiative_metrics": desktop_initiative_metrics_summary_func(payload.initiative_metrics),
    }
