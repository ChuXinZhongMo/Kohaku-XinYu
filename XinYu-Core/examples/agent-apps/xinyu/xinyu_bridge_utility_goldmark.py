from __future__ import annotations

from typing import Any

from xinyu_bridge_utility_common import ensure_open
from xinyu_bridge_utility_common import ensure_payload


async def goldmark_mark_request(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = ensure_payload(payload, deps)
    return await deps.to_thread(deps.mark_goldmark_request, runtime.xinyu_dir, payload)
