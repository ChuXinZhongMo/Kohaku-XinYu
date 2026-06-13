from __future__ import annotations

from typing import Any


def sessions(runtime: Any) -> int:
    return len(getattr(runtime, "_sessions", {}))


def ensure_open(runtime: Any, deps: Any) -> None:
    if getattr(runtime, "_closed", False):
        raise deps.bridge_request_error_type(
            deps.service_unavailable_status,
            "bridge is shutting down",
        )


def ensure_payload(payload: dict[str, Any] | None, deps: Any) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise deps.bridge_request_error_type(
            deps.bad_request_status,
            "request body must be a JSON object",
        )
    return dict(payload or {})


def payload_or_empty(payload: dict[str, Any] | None, deps: Any) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise deps.bridge_request_error_type(
            deps.bad_request_status,
            "request body must be a JSON object",
        )
    return payload or {}
