from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


async def attach_desktop_self_action_response(
    result: dict[str, Any],
    *,
    decision: str,
    snapshot_func: Callable[..., Awaitable[dict[str, Any]]],
    approval_reply_func: Callable[..., str],
) -> dict[str, Any]:
    snapshot = await snapshot_func({})
    result["selfAction"] = snapshot.get("selfAction")
    result["reply"] = approval_reply_func(result, decision=decision)
    return result
