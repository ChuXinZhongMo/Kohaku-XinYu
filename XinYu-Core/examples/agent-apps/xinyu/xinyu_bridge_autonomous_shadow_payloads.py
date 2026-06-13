from __future__ import annotations

from typing import Any, Callable


def goal_outcome_observer_kwargs(notes: list[str], *, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "trigger": "autonomous_maintenance",
        "maintenance_notes": notes,
    }


def proactivity_shadow_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {"checked_at": checked_at}


def initiative_orchestrator_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "trigger": "autonomous_maintenance",
        "delivery_level": "desktop_inbox",
        "dry_run": False,
    }


def emotion_council_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "trigger": "autonomous_maintenance",
    }


def impulse_soup_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {"checked_at": checked_at}


def initiative_spine_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "trigger": "autonomous_maintenance",
    }


def desire_drive_kwargs(*, checked_at: str) -> dict[str, Any]:
    return {
        "checked_at": checked_at,
        "trigger": "autonomous_maintenance",
    }


def contextual_self_observatory_kwargs(
    *,
    checked_at: str,
    timestamp_or_now_iso_func: Callable[..., str],
) -> dict[str, Any]:
    return {"observed_at": timestamp_or_now_iso_func(checked_at)}
