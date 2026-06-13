from __future__ import annotations

from typing import Any

from xinyu_bridge_values import safe_str


def goal_outcome_summary(result: dict[str, Any]) -> str:
    return (
        "goal_outcome:"
        f"{safe_str(result.get('status'), 'unknown')}/"
        f"{safe_str(result.get('goal_id') or result.get('reason'), 'none')}/"
        f"{safe_str(result.get('outcome') or result.get('reason_code') or result.get('reason'), 'none')}"
    )


def proactivity_shadow_summary(shadow: dict[str, Any]) -> str:
    return (
        "proactivity_shadow:"
        f"{safe_str(shadow.get('status'), 'unknown')}/"
        f"{safe_str(shadow.get('source_type'), 'none')}/"
        f"{safe_str(shadow.get('total_score'), '0')}/"
        f"{safe_str(shadow.get('preferred_channel'), 'silent')}"
    )


def initiative_orchestrator_summary(initiative: dict[str, Any]) -> str:
    return (
        "initiative_orchestrator:"
        f"{safe_str(initiative.get('status'), 'unknown')}/"
        f"{safe_str(initiative.get('source_type'), 'none')}/"
        f"{safe_str(initiative.get('total_score'), '0')}/"
        f"{safe_str(initiative.get('delivery_level'), 'none')}"
    )


def initiative_desktop_notes(initiative: dict[str, Any], *, limit: int = 4) -> list[str]:
    return [safe_str(note) for note in initiative.get("notes", [])[:limit]]


def emotion_council_summary(council: dict[str, Any]) -> str:
    return (
        "emotion_council:"
        f"{safe_str(council.get('status'), 'unknown')}/"
        f"{safe_str(council.get('strongest_lens'), 'none')}/"
        f"{safe_str(council.get('active_lens_count'), '0')}"
    )


def impulse_soup_summary(soup: dict[str, Any]) -> str:
    return (
        "impulse_soup:"
        f"{safe_str(soup.get('status'), 'unknown')}/"
        f"{safe_str(soup.get('active_count'), '0')}/"
        f"{safe_str(soup.get('lineage_count'), '0')}/"
        f"{safe_str(soup.get('top_desire_shape'), 'none')}"
    )


def initiative_spine_summary(spine: dict[str, Any]) -> str:
    return (
        "initiative_spine:"
        f"{safe_str(spine.get('emergence_level'), 'unknown')}/"
        f"{safe_str(spine.get('action_permission'), 'unknown')}"
    )


def desire_drive_summary(drive: dict[str, Any]) -> str:
    return (
        "desire_drive:"
        f"{safe_str(drive.get('status'), 'unknown')}/"
        f"{safe_str(drive.get('dominant_drive'), 'none')}/"
        f"{safe_str(drive.get('drive_intensity'), '0')}/"
        f"{safe_str(drive.get('autonomy_tension'), 'unknown')}"
    )


def contextual_self_observatory_summary(observatory: dict[str, Any]) -> str:
    return (
        "contextual_self_observatory:"
        f"{safe_str(observatory.get('posture'), 'unknown')}/"
        f"{safe_str(observatory.get('latest_scene'), 'unknown')}/"
        f"{safe_str(observatory.get('recall_admitted_count_24h'), '0')}/"
        f"{safe_str(observatory.get('initiative_held_by_context_count_24h'), '0')}"
    )
