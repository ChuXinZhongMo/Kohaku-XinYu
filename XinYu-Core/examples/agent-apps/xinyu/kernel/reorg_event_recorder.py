"""Record K-008 reorganization events into the event sourcing layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from state_service import append_jsonl
except Exception:
    append_jsonl = None  # type: ignore


def record_reorg_event(
    self_id: str,
    cycle_result: dict[str, Any],
    source_event_id: str,
    root: Path | None = None,
) -> dict[str, Any]:
    """Append a reorg cycle summary to memory/events/reorg_events.jsonl."""
    event = {
        "event_kind": "self_reorganization",
        "self_id": self_id,
        "source_event_id": source_event_id,
        "proposals_count": cycle_result.get("proposals_count", 0),
        "applied_count": len(cycle_result.get("applied", [])),
        "pending_review_count": cycle_result.get("pending_count", 0),
        "structural_impact": cycle_result.get("structural_impact", False),
        "working_memory_delta": (
            cycle_result.get("working_memory_after", 0) - cycle_result.get("working_memory_before", 0)
        ),
        "applied_actions": [
            a.get("action_type") for a in cycle_result.get("applied", []) if a.get("applied")
        ],
        "pending_actions": [
            p.get("action_type") for p in cycle_result.get("pending_review", [])
        ],
    }

    if append_jsonl and root:
        try:
            event_dir = root / "memory" / "events"
            event_dir.mkdir(parents=True, exist_ok=True)
            append_jsonl(event_dir / "reorg_events.jsonl", event)
            event["recorded"] = True
        except Exception:
            event["recorded"] = False
    else:
        event["recorded"] = False

    return event