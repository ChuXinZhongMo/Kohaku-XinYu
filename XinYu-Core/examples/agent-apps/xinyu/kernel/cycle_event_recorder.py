"""Record K-009 full cognitive cycle events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from state_service import append_jsonl
except Exception:
    append_jsonl = None  # type: ignore


def record_cognitive_cycle_event(
    self_id: str,
    summary: dict[str, Any],
    stages: dict[str, Any],
    root: Path | None = None,
) -> dict[str, Any]:
    """Append a closed cognitive cycle to memory/events/cognitive_cycle_events.jsonl."""
    event = {
        "event_kind": "cognitive_cycle",
        "self_id": self_id,
        "source_event_id": summary.get("source_event_id"),
        "importance": summary.get("importance"),
        "error_magnitude": summary.get("error_magnitude"),
        "reorg_mode": summary.get("reorg_mode"),
        "cycle_closed": summary.get("cycle_closed", True),
        "structural_impact": summary.get("structural_impact", False),
        "stages_completed": list(stages.keys()),
        "prediction_ran": "prediction" in stages and not stages["prediction"].get("skipped"),
        "reorg_ran": "reorganization" in stages,
    }

    if append_jsonl and root:
        try:
            event_dir = root / "memory" / "events"
            event_dir.mkdir(parents=True, exist_ok=True)
            append_jsonl(event_dir / "cognitive_cycle_events.jsonl", event)
            event["recorded"] = True
        except Exception:
            event["recorded"] = False
    else:
        event["recorded"] = False

    return event