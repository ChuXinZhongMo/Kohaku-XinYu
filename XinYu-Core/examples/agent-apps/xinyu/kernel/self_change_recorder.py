"""Helper to record Self Model changes into the existing event sourcing system.

This keeps kernel independent while allowing traceable updates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kernel.self import Self

# Try to use existing append without making kernel depend on full runtime
try:
    from state_service import append_jsonl
except Exception:
    append_jsonl = None  # type: ignore


def record_self_model_change(
    kernel_self: Self,
    change_type: str,
    details: dict[str, Any],
    root: Path | None = None,
) -> dict[str, Any]:
    """Record a self model change.

    Appends to memory/events/self_model_events.jsonl if possible (using existing append_jsonl).
    Always returns the structured event payload for further processing (e.g. in _record or sidecars).
    """
    model = kernel_self.get_self_model()
    event = {
        "event_kind": "self_model_update",
        "self_id": kernel_self.self_id,
        "change_type": change_type,
        "details": details,
        "current_model_summary": model.get("core_summary"),
        "core_statements": model.get("core_statements", []),
        "timestamp": details.get("timestamp"),  # caller should fill if needed
    }

    if append_jsonl and root:
        try:
            event_dir = root / "memory" / "events"
            event_dir.mkdir(parents=True, exist_ok=True)
            append_jsonl(event_dir / "self_model_events.jsonl", event)
            event["recorded"] = True
        except Exception:
            event["recorded"] = False
    else:
        event["recorded"] = False

    return event
