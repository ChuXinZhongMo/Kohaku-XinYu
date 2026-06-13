from __future__ import annotations

from typing import Any, Mapping

from xinyu_bridge_external_action_backend import (
    ApprovedExternalActionRequest,
    external_action_backend_for_runtime,
)


async def maybe_execute_external_action_backend(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    route: str,
    http_method: str,
    runtime_method: str,
    owner_private_context: bool = False,
) -> dict[str, Any] | None:
    if getattr(runtime, "_closed", False):
        return None
    if payload is not None and not isinstance(payload, dict):
        return None

    backend = external_action_backend_for_runtime(runtime)
    if not bool(getattr(backend, "enabled", False)):
        return None

    request = ApprovedExternalActionRequest(
        route=route,
        http_method=http_method,
        runtime_method=runtime_method,
        payload=dict(payload or {}),
        query=_query_from_payload(payload),
        owner_private_context=owner_private_context,
    )
    return await backend.execute(runtime, request)


def _query_from_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    query = payload.get("query")
    return dict(query) if isinstance(query, Mapping) else {}
