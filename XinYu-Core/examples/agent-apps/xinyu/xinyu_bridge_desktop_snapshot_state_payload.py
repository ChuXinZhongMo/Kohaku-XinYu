from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DesktopXinyuStatePayload:
    environment: dict[str, Any]
    entropy_state: dict[str, Any]
    active_desire: Any
    latest_intent: dict[str, Any]
    latest_turn: dict[str, Any]
    sensation: dict[str, Any]
    resource_request: dict[str, Any] | None
    action_digest: dict[str, Any]
    initiative_metrics: dict[str, Any]
    latest_action: dict[str, Any]
    seed_detail: dict[str, Any]
    digested_count: int
    recent_memory_echoes: int
    waiting: bool


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_or_none(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _first_dict(items: list[Any]) -> dict[str, Any]:
    first = items[0] if items else {}
    return first if isinstance(first, dict) else {}


def _last_dict(items: list[Any]) -> dict[str, Any]:
    latest = items[-1] if items else {}
    return latest if isinstance(latest, dict) else {}


def _digested_count(action_digest: dict[str, Any]) -> int:
    raw_count = action_digest.get("digested_count") or "0"
    return int(action_digest.get("digested_count") or 0) if str(raw_count).isdigit() else 0


def build_desktop_xinyu_state_payload(
    *,
    environment: dict[str, Any],
    entropy_state: dict[str, Any],
    active_desires: list[dict[str, Any]],
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    action_digest: dict[str, Any] | None,
    initiative_metrics: dict[str, Any] | None,
) -> DesktopXinyuStatePayload:
    normalized_action_digest = _dict_or_empty(action_digest)
    action_recent = normalized_action_digest.get("recent")
    latest_action = _last_dict(action_recent if isinstance(action_recent, list) else [])
    seed_detail = _dict_or_empty(latest_action.get("seed_detail"))
    sensation = _dict_or_empty(environment.get("physicalSensation"))

    return DesktopXinyuStatePayload(
        environment=environment,
        entropy_state=entropy_state,
        active_desire=active_desires[0] if active_desires else {},
        latest_intent=_first_dict(proactive_items),
        latest_turn=_last_dict(recent_turns),
        sensation=sensation,
        resource_request=_dict_or_none(entropy_state.get("resource_request")),
        action_digest=normalized_action_digest,
        initiative_metrics=_dict_or_empty(initiative_metrics),
        latest_action=latest_action,
        seed_detail=seed_detail,
        digested_count=_digested_count(normalized_action_digest),
        recent_memory_echoes=len(recent_memory_events),
        waiting=bool(proactive_items),
    )
