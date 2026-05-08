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
