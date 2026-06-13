from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any, Callable

from xinyu_bridge_errors import BridgeRequestError


def ensure_open(runtime: Any) -> None:
    if runtime._closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")


def ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


def timestamp_or_now_iso(value: Any = None, *, safe_str_func: Callable[..., str]) -> str:
    text = safe_str_func(value).strip()
    if not text:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def result_notes(result: dict[str, Any], *, safe_str_func: Callable[..., str], limit: int = 4) -> list[str]:
    return [safe_str_func(note) for note in result.get("notes", [])[:limit]]


def ack_delivery_severity(result: dict[str, Any], *, safe_str_func: Callable[..., str]) -> str | None:
    return "error" if safe_str_func(result.get("ack_status")) == "failed" else None
