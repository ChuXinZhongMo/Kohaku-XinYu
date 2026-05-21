from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Mapping

from xinyu_qq_config import as_int


def event_timestamp_seconds(event: Mapping[str, Any]) -> int:
    timestamp = as_int(event.get("time"), int(time.time()))
    if timestamp > 10_000_000_000:
        timestamp = int(timestamp / 1000)
    if timestamp <= 0:
        return int(time.time())
    return timestamp


def event_time_iso(timestamp_seconds: int) -> str:
    try:
        return datetime.fromtimestamp(int(timestamp_seconds)).astimezone().isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        return datetime.now().astimezone().isoformat(timespec="seconds")
