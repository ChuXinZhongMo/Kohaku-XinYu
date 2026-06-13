from __future__ import annotations

from typing import Any

from xinyu_bridge_utility_common import ensure_open
from xinyu_bridge_utility_common import payload_or_empty


async def learning_ingest(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = payload_or_empty(payload, deps)
    try:
        return await runtime.learning_service.ingest(payload)
    except deps.learning_bridge_error_type as exc:
        raise deps.bridge_request_error_type(getattr(exc, "status"), getattr(exc, "message")) from exc


async def learning_study(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = payload_or_empty(payload, deps)
    return await runtime.learning_service.study(payload)


async def learning_observe(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = payload_or_empty(payload, deps)
    return await runtime.learning_service.observe(payload)
