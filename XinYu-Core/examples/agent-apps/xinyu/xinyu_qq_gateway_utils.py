from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any


def quiet_websockets_handshake_noise() -> None:
    for logger_name in ("websockets.server", "websockets.protocol"):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def hash_id(value: Any, *, length: int = 16) -> str:
    text = safe_str(value).strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def maybe_int(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def message_ids_from_action_response(action_response: dict[str, Any] | None) -> list[str]:
    """Collect OneBot / bubble message ids from a send_action response payload."""
    if not isinstance(action_response, dict):
        return []
    data = action_response.get("data")
    if not isinstance(data, dict):
        return []
    ids: list[str] = []
    bubble_ids = data.get("reply_bubble_message_ids")
    if isinstance(bubble_ids, list):
        ids.extend(safe_str(item).strip() for item in bubble_ids)
    ids.extend(
        part.strip()
        for part in safe_str(data.get("message_id")).replace("，", ",").split(",")
    )
    return list(dict.fromkeys(item for item in ids if item))
