from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import optional_int as _optional_int
from xinyu_bridge_values import safe_str as _safe_str


SafeStr = Callable[..., str]
OptionalInt = Callable[[Any], int | None]
MarkerCount = Callable[[list[Any], tuple[str, ...]], int]

SUPPRESSED_RESIDUE_MARKERS = (
    "suppress",
    "suppressed",
    "\u5fcd\u4f4f",
    "\u538b\u4e0b",
    "\u6ca1\u6709\u53d1\u51fa\u53bb",
)


def ticket_id_from_payload(payload: dict[str, Any], *, safe_str: SafeStr = _safe_str) -> str:
    return safe_str(payload.get("ticket_id") or payload.get("id")).strip()


def owner_decision_id_from_payload(payload: dict[str, Any], *, safe_str: SafeStr = _safe_str) -> str:
    return safe_str(payload.get("owner_decision_id") or payload.get("decision_id")).strip()


def statuses_from_payload(payload: dict[str, Any], *, safe_str: SafeStr = _safe_str) -> set[str] | None:
    raw_status = safe_str(payload.get("status") or payload.get("statuses")).strip()
    return {part.strip() for part in raw_status.split(",") if part.strip()} if raw_status else None


def approved_seconds_from_payload(
    payload: dict[str, Any],
    *,
    optional_int: OptionalInt = _optional_int,
) -> int | None:
    return optional_int(payload.get("approved_seconds"))


def note_from_payload(payload: dict[str, Any], *, safe_str: SafeStr = _safe_str) -> str:
    return safe_str(payload.get("note"))


def cancel_reason_from_payload(payload: dict[str, Any], *, safe_str: SafeStr = _safe_str) -> str:
    return safe_str(payload.get("reason"), "owner_cancelled")


def metabolism_input_window_payload(
    *,
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    marker_count: MarkerCount,
    self_choice_dream_bias: dict[str, Any] | None = None,
) -> dict[str, Any]:
    window: dict[str, Any] = {
        "suppressed_residue_count": marker_count(recent_memory_events, SUPPRESSED_RESIDUE_MARKERS),
        "memory_event_count": sum(isinstance(item, dict) for item in recent_memory_events),
        "proactive_item_count": sum(isinstance(item, dict) for item in proactive_items),
        "recent_turn_count": sum(isinstance(item, dict) for item in recent_turns),
    }
    if isinstance(self_choice_dream_bias, dict):
        window["self_choice"] = self_choice_dream_bias
    return window
