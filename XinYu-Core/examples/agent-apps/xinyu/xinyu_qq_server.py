from __future__ import annotations

from typing import Any


def websocket_path(websocket: Any) -> str:
    request = getattr(websocket, "request", None)
    path = getattr(request, "path", "") if request is not None else ""
    if path:
        return str(path)
    return _safe_text(getattr(websocket, "path", ""))


def websocket_path_allowed(path: str, configured_path: str) -> bool:
    if not configured_path:
        return True
    return path in {"", configured_path}


def connection_id(prefix: str, timestamp_seconds: int, sequence: int) -> str:
    return f"{prefix}-{timestamp_seconds}-{sequence}"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
