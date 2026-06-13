"""Response payload helpers for private isolated-desktop routes."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_private_desktop_status_store import (
    private_desktop_status_path_exists,
    private_desktop_status_path_mtime,
)
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_private_desktop_control import LATEST_FRAME_REL, boundaries_dict

BoundariesFunc = Callable[[], dict[str, Any]]


def _latest_frame_age_seconds(path: Path) -> int | None:
    if not private_desktop_status_path_exists(path):
        return None
    try:
        import time

        return int(max(0, time.time() - private_desktop_status_path_mtime(path)))
    except OSError:
        return None


def _live_state_payload(
    root: Path,
    status: dict[str, Any],
    *,
    boundaries_func: BoundariesFunc = boundaries_dict,
) -> dict[str, Any]:
    latest = root / LATEST_FRAME_REL
    return {
        "ok": True,
        "accepted": True,
        "backend": _safe_str(status.get("backend")) or "unavailable",
        "session_state": _safe_str(status.get("session_state")) or "stopped",
        "live": bool(status.get("live")),
        "display_size": _safe_str(status.get("display_size")),
        "live_view_url": _safe_str(status.get("live_view_url")),
        "has_latest_frame": private_desktop_status_path_exists(latest),
        "frame_age_seconds": _latest_frame_age_seconds(latest),
        "boundaries": boundaries_func(),
        "notes": ["private_desktop_live_state"],
    }


def _observe_payload(action: str, outcome: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    accepted = bool(outcome.get("ok"))
    return {
        "ok": accepted,
        "accepted": accepted,
        "action": action,
        "result": _safe_str(outcome.get("result")),
        "error_code": _safe_str(outcome.get("error_code")),
        "frame_ref": _safe_str(outcome.get("frame_ref")),
        "privateDesktop": snapshot,
        "notes": ["private_desktop_observe", "read_only_action"],
    }


def _lifecycle_payload(
    outcome: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    note: str,
    include_error_code: bool = False,
) -> dict[str, Any]:
    payload = {
        "ok": bool(outcome.get("ok")),
        "accepted": bool(outcome.get("ok")),
        "session_state": _safe_str(outcome.get("session_state")) or "stopped",
        "live": bool(outcome.get("live")),
        "privateDesktop": snapshot,
        "notes": [note],
    }
    if include_error_code:
        payload["error_code"] = _safe_str(outcome.get("error_code"))
    return payload
