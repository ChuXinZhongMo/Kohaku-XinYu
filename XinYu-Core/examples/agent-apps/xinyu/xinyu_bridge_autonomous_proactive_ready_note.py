from __future__ import annotations

from typing import Any

from xinyu_bridge_autonomous_note_responses import (
    autonomous_outward_is_queued,
    desktop_candidate_request_notes,
    request_allows_desktop_candidate,
)


def should_schedule_desktop_proactive_candidate(
    request: dict[str, Any],
    auto_outward: dict[str, Any],
) -> bool:
    return request_allows_desktop_candidate(request) and not autonomous_outward_is_queued(auto_outward)


def append_desktop_proactive_candidate_ready_note(
    runtime: Any,
    notes: list[str],
    *,
    request: dict[str, Any],
    auto_outward: dict[str, Any],
) -> None:
    if not should_schedule_desktop_proactive_candidate(request, auto_outward):
        return
    scheduled = runtime._desktop_schedule_proactive_candidate_ready_from_state(
        notes=desktop_candidate_request_notes(request),
    )
    if scheduled:
        notes.append("desktop_proactive_candidate_ready_scheduled")
