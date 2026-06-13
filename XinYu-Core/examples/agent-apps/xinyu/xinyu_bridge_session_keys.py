from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def session_key_from_payload(payload: Mapping[str, Any]) -> str:
    for key in ("session_id", "user_id"):
        value = _safe_text(payload.get(key)).strip()
        if value:
            return value
    metadata = payload.get("metadata")
    if isinstance(metadata, Mapping):
        for key in ("session_id", "user_id"):
            value = _safe_text(metadata.get(key)).strip()
            if value:
                return value
    return "qq:default"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
