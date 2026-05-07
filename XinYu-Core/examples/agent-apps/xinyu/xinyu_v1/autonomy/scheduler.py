"""Idle auto-healing scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..clock import SystemClock
from ..config import MaintenanceConfig
from ..memory.jsonl_store import JsonlMemoryStore
from ..paths import XinYuPaths
from ..storage.file_lock import FileLock
from ..types import JSONValue
from .deadlock_inspector import inspect_deadlocks
from .dream_consolidator import run_dream_consolidation
from .idle_detector import IdleDetector
from .reports import write_report


@dataclass(frozen=True, slots=True)
class SchedulerRunReport:
    ran: bool
    notes: tuple[str, ...] = field(default_factory=tuple)
    payload: dict[str, JSONValue] = field(default_factory=dict)


class AutoHealingScheduler:
    def __init__(self, paths: XinYuPaths, config: MaintenanceConfig, *, clock: SystemClock | None = None) -> None:
        self._paths = paths
        self._config = config
        self._clock = clock or SystemClock()
        self.idle = IdleDetector(config.idle_after_seconds, self._clock)

    async def run_once_if_idle(self) -> SchedulerRunReport:
        if not self.idle.is_idle():
            return SchedulerRunReport(ran=False, notes=("not_idle",))
        lock_path = self._paths.runtime_path("maintenance.lock")
        with FileLock(lock_path, timeout_seconds=0):
            store = JsonlMemoryStore(self._paths.runtime_path("memory"))
            deadlock = inspect_deadlocks(self._paths.root)
            dream = run_dream_consolidation(store)
            payload: dict[str, JSONValue] = {
                "timestamp": self._clock.now_iso(),
                "deadlock": {"ok": deadlock.ok, "findings": list(deadlock.findings)},
                "dream_consolidation": dream.to_json(),
            }
            write_report(self._paths.logs_root / "xinyu_v1_maintenance_latest.md", "XinYu v1 Maintenance", payload)
            return SchedulerRunReport(ran=True, notes=("maintenance_complete",), payload=payload)

