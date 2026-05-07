"""Idle-window detection for maintenance jobs."""

from __future__ import annotations

from dataclasses import dataclass

from ..clock import SystemClock


@dataclass(slots=True)
class IdleDetector:
    idle_after_seconds: int
    clock: SystemClock
    active_requests: int = 0
    last_human_monotonic: float = 0.0

    def mark_human_turn(self) -> None:
        self.last_human_monotonic = self.clock.monotonic()

    def request_started(self) -> None:
        self.active_requests += 1

    def request_finished(self) -> None:
        self.active_requests = max(0, self.active_requests - 1)

    def is_idle(self) -> bool:
        if self.active_requests > 0:
            return False
        if self.last_human_monotonic <= 0:
            return True
        return self.clock.monotonic() - self.last_human_monotonic >= self.idle_after_seconds

