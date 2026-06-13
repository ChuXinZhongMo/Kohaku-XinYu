from __future__ import annotations

from typing import Callable

from xinyu_bridge_desktop_snapshot_state_payload import DesktopXinyuStatePayload
from xinyu_bridge_desktop_snapshot_state_projection_action import DesktopActionResidueProjection


def project_recent_concern(
    payload: DesktopXinyuStatePayload,
    action: DesktopActionResidueProjection,
    *,
    safe_str_func: Callable[..., str],
    compact_text_func: Callable[..., str],
) -> str:
    active_desire = payload.active_desire
    resource_request = payload.resource_request
    return compact_text_func(
        safe_str_func(active_desire.get("possible_action"))
        or safe_str_func(resource_request.get("reason") if resource_request else "")
        or safe_str_func(payload.latest_intent.get("candidatePreview"))
        or safe_str_func(payload.latest_intent.get("whyNowPreview"))
        or action.concern
        or safe_str_func(payload.latest_turn.get("replyPreview"))
        or safe_str_func(payload.latest_turn.get("textPreview"))
        or "还没有新的牵挂浮上来",
        140,
    )


def project_recent_concerns(
    payload: DesktopXinyuStatePayload,
    action: DesktopActionResidueProjection,
    *,
    safe_str_func: Callable[..., str],
    compact_text_func: Callable[..., str],
) -> list[str]:
    return [
        project_recent_concern(
            payload,
            action,
            safe_str_func=safe_str_func,
            compact_text_func=compact_text_func,
        )
    ]
