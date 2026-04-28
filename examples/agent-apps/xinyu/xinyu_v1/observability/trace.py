"""Per-turn trace recording."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..clock import SystemClock
from ..storage.atomic import atomic_write_text
from ..types import JSONValue, TraceContext


@dataclass(slots=True)
class TraceRecorder:
    path: Path
    clock: SystemClock = field(default_factory=SystemClock)

    def record(self, trace: TraceContext, event: str, payload: dict[str, JSONValue] | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": self.clock.now_iso(),
            "trace": trace.to_json(),
            "event": event,
            "payload": payload or {},
        }
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def write_snapshot(self, trace: TraceContext, payload: dict[str, JSONValue]) -> None:
        atomic_write_text(self.path.with_suffix(".latest.json"), json.dumps({"trace": trace.to_json(), **payload}, ensure_ascii=False, indent=2))

