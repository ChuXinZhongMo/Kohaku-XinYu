"""Time helpers with injectable clocks for tests."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def load_timezone(name: str | None, *, default: str = "Asia/Hong_Kong") -> timezone | ZoneInfo:
    text = (name or default).strip() or default
    if text.upper() == "UTC":
        return UTC
    try:
        return ZoneInfo(text)
    except ZoneInfoNotFoundError:
        if text in {"Asia/Hong_Kong", "Asia/Shanghai", default}:
            return timezone(timedelta(hours=8), name="UTC+08:00")
        return UTC


@dataclass(frozen=True, slots=True)
class SystemClock:
    timezone_name: str = "Asia/Hong_Kong"

    @property
    def timezone(self) -> timezone | ZoneInfo:
        return load_timezone(self.timezone_name)

    def now(self) -> datetime:
        return datetime.now(self.timezone)

    def now_iso(self) -> str:
        return self.now().isoformat(timespec="seconds")

    def monotonic(self) -> float:
        return time.monotonic()

    def elapsed_ms(self, started_at: float) -> int:
        return max(0, int((self.monotonic() - started_at) * 1000))


@dataclass(frozen=True, slots=True)
class FixedClock:
    timestamp: datetime
    monotonic_value: float = 0.0

    def now(self) -> datetime:
        if self.timestamp.tzinfo is None:
            return self.timestamp.replace(tzinfo=UTC)
        return self.timestamp

    def now_iso(self) -> str:
        return self.now().isoformat(timespec="seconds")

    def monotonic(self) -> float:
        return self.monotonic_value
