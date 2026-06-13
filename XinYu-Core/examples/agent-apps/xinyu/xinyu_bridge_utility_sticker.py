from __future__ import annotations

from typing import Any

from xinyu_bridge_utility_common import ensure_open
from xinyu_bridge_utility_common import payload_or_empty


async def sticker_import(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = payload_or_empty(payload, deps)
    async with runtime._global_turn_lock:
        return await deps.to_thread(deps.import_sticker_from_payload, runtime.xinyu_dir, payload)
