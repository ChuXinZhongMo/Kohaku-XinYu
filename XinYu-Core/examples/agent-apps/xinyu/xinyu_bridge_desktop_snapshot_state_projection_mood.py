from __future__ import annotations

from typing import Callable

from xinyu_bridge_desktop_snapshot_state_payload import DesktopXinyuStatePayload
from xinyu_bridge_desktop_snapshot_state_projection_action import DesktopActionResidueProjection


_CHOSEN_ACTION_MOOD_TAGS = {
    "suppress_and_wait": "想靠近但忍住了",
    "leave_note_on_desk": "把话留在桌面边缘",
    "request_metabolism_window": "在索求一次整理窗口",
}


def project_mood_tag(
    payload: DesktopXinyuStatePayload,
    action: DesktopActionResidueProjection,
    *,
    pressure: str,
    safe_str_func: Callable[..., str],
) -> str:
    chosen_action = safe_str_func(payload.active_desire.get("chosen_action"))
    if chosen_action in _CHOSEN_ACTION_MOOD_TAGS:
        return _CHOSEN_ACTION_MOOD_TAGS[chosen_action]
    if payload.waiting:
        return "想靠近"

    mood_tag = "安静在场"
    if safe_str_func(payload.entropy_state.get("entropy_band")) in {"fracture", "terminal"}:
        mood_tag = "熵噪堆积"

    if not chosen_action:
        if pressure == "high":
            mood_tag = "被热压住"
        elif pressure == "low":
            mood_tag = "失重安静"
        if action.seed_id and action.pressure in {"medium", "high"}:
            mood_tag = "行动残留未散"
    return mood_tag
