from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from xinyu_turn_route_trace import record_turn_route_stage


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


class TurnRouteObserver:
    def __init__(
        self,
        root: Path,
        *,
        turn_id: str,
        payload: dict[str, Any],
        started_at: float,
    ) -> None:
        self.root = Path(root)
        self.turn_id = _safe_str(turn_id)
        self.payload = payload
        self.started_at = started_at

    def record(
        self,
        stage: str,
        *,
        route: str = "undecided",
        status: str = "running",
        elapsed_ms: int | None = None,
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        return record_turn_route_stage(
            self.root,
            turn_id=self.turn_id,
            stage=stage,
            route=route,
            status=status,
            elapsed_ms=elapsed_ms if elapsed_ms is not None else self.elapsed_ms(),
            payload=self.payload,
            notes=[_safe_str(note) for note in list(notes or [])[:8]],
        )

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started_at) * 1000)
