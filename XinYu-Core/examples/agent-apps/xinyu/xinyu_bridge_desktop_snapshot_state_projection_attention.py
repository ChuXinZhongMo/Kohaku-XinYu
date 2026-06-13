from __future__ import annotations

from typing import Callable

from xinyu_bridge_desktop_snapshot_state_payload import DesktopXinyuStatePayload
from xinyu_bridge_desktop_snapshot_state_projection_action import DesktopActionResidueProjection


def project_current_attention(
    payload: DesktopXinyuStatePayload,
    action: DesktopActionResidueProjection,
    *,
    safe_str_func: Callable[..., str],
    compact_text_func: Callable[..., str],
) -> str:
    active_desire = payload.active_desire
    return compact_text_func(
        safe_str_func(active_desire.get("visible_trace"))
        or safe_str_func(payload.latest_intent.get("focusLabel"))
        or safe_str_func(payload.latest_intent.get("kind"))
        or action.attention
        or safe_str_func(payload.entropy_state.get("visible_artifact"))
        or safe_str_func(payload.latest_turn.get("textPreview"))
        or safe_str_func(payload.latest_turn.get("replyPreview"))
        or "等待新的生活信号",
        96,
    )
