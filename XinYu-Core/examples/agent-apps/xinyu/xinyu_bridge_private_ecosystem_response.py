"""Response payload helpers for private ecosystem bridge routes."""
from __future__ import annotations

from typing import Any

from xinyu_bridge_values import safe_str as _safe_str


def private_ecosystem_tick_note(result: dict[str, Any]) -> str:
    counters = result.get("counters") if isinstance(result.get("counters"), dict) else {}
    return (
        "private_ecosystem:"
        f"{_safe_str(result.get('selected_goal_id'), 'none')}/"
        f"{_safe_str(result.get('selected_action_kind'), 'none')}/"
        f"{_safe_str(result.get('action_status'), 'none')}/"
        f"{_safe_str(counters.get('ticks'), '0')}"
    )


def private_ecosystem_snapshot_response(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "accepted": True, "privateEcosystem": snapshot, "notes": ["private_ecosystem_snapshot"]}


def private_ecosystem_pause_response(
    merged: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    paused: bool,
) -> dict[str, Any]:
    share = merged.get("owner_private_autonomous_share", {})
    if not isinstance(share, dict):
        share = {}
    return {
        "ok": True,
        "accepted": True,
        "paused": bool(share.get("paused")),
        "enabled": bool(share.get("enabled")),
        "privateEcosystem": snapshot,
        "notes": ["share_paused" if paused else "share_resumed"],
    }


def private_ecosystem_grant_response(
    *,
    patch: dict[str, Any],
    rejected: list[str],
    merged: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    share = merged.get("owner_private_autonomous_share", {})
    ecosystem = merged.get("private_ecosystem", {})
    browser = merged.get("private_browser", {})
    computer = merged.get("computer_control", {})
    return {
        "ok": True,
        "accepted": True,
        "sections": sorted(patch.keys()),
        "rejected_keys": rejected,
        "share_enabled": bool(share.get("enabled")) if isinstance(share, dict) else False,
        "private_ecosystem_enabled": bool(ecosystem.get("enabled")) if isinstance(ecosystem, dict) else False,
        "browser_enabled": bool(browser.get("enabled")) if isinstance(browser, dict) else False,
        "computer_enabled": bool(computer.get("enabled")) if isinstance(computer, dict) else False,
        "privateEcosystem": snapshot,
        "notes": ["private_ecosystem_grant_updated"],
    }


def private_ecosystem_tick_disabled_response(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "accepted": False,
        "error": "private_ecosystem_disabled",
        "privateEcosystem": snapshot,
        "notes": ["enable_private_ecosystem_before_tick"],
    }


def private_ecosystem_tick_response(result: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": True,
        "accepted": bool(result.get("ok", True)),
        "goalId": _safe_str(result.get("selected_goal_id")),
        "actionKind": _safe_str(result.get("selected_action_kind")),
        "actionStatus": _safe_str(result.get("action_status")),
        "privateEcosystem": snapshot,
        "notes": ["private_ecosystem_tick"],
    }


def private_browser_snapshot_response(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "accepted": True, "browser": snapshot, "notes": ["private_browser_snapshot"]}
