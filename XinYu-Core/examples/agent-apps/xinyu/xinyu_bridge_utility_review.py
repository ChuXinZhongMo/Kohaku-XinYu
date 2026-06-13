from __future__ import annotations

from typing import Any

from xinyu_bridge_utility_common import ensure_open
from xinyu_bridge_utility_common import ensure_payload


async def review_inbox_command(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = ensure_payload(payload, deps)
    async with runtime._review_admin_lock:
        return await deps.to_thread(deps.handle_review_inbox_command, runtime.xinyu_dir, payload)
