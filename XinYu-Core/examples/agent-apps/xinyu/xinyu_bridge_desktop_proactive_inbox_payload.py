from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_desktop_proactive_inbox_history import desktop_proactive_history_time


def build_desktop_proactive_inbox_payload(
    inbox: dict[str, dict[str, Any]],
    history: list[dict[str, Any]],
    *,
    safe_str: Callable[..., str],
    inbox_max: int,
    history_max: int,
) -> dict[str, Any]:
    items = sorted(
        (dict(item) for item in inbox.values()),
        key=lambda item: safe_str(item.get("createdAt")),
        reverse=True,
    )[:inbox_max]
    history_items = sorted(
        (dict(item) for item in history),
        key=lambda item: desktop_proactive_history_time(item, safe_str),
        reverse=True,
    )[:history_max]
    return {
        "version": 1,
        "items": items,
        "history": history_items,
        "notes": ["desktop_proactive_inbox_v0_runtime_buffer"],
    }
