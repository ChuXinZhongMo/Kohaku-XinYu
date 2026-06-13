from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import safe_str as _safe_str


SafeStr = Callable[..., str]
OPEN_TICKET_STATUSES = {"requested", "approved", "running"}
STATUS_RANK = {"running": 3, "approved": 2, "requested": 1}


def select_desktop_metabolism_ticket(
    tickets: list[dict[str, Any]],
    *,
    safe_str: SafeStr = _safe_str,
) -> dict[str, Any]:
    if not tickets:
        return {}
    ticket = max(
        tickets,
        key=lambda item: (
            STATUS_RANK.get(safe_str(item.get("status")), 0),
            safe_str(item.get("created_at")),
            safe_str(item.get("ticket_id")),
        ),
    )
    return dict(ticket)
