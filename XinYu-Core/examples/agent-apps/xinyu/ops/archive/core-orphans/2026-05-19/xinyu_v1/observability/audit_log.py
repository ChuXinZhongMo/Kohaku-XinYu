"""Append-only audit log."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..clock import SystemClock
from ..types import JSONMapping, TraceContext


@dataclass(slots=True)
class JsonlAuditLog:
    path: Path
    clock: SystemClock = field(default_factory=SystemClock)

    def record(self, event_type: str, payload: JSONMapping, trace: TraceContext | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "created_at": self.clock.now_iso(),
            "event_type": event_type,
            "payload": dict(payload),
            "trace": trace.to_json() if trace else None,
        }
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

