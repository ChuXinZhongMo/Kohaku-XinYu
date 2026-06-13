from __future__ import annotations

from typing import Any

from xinyu_bridge_values import as_bool, safe_str


def self_thought_summary(thought: dict[str, Any]) -> str:
    return (
        "self_thought:"
        f"{safe_str(thought.get('status'), 'unknown')}/"
        f"{safe_str(thought.get('outcome'), 'unknown')}/"
        f"{safe_str(thought.get('focus_kind'), 'unknown')}/"
        f"{safe_str(thought.get('intention'), 'unknown')}"
    )


def proactive_request_summary(request: dict[str, Any]) -> str:
    return (
        "proactive_request:"
        f"{safe_str(request.get('status'), 'unknown')}/"
        f"{safe_str(request.get('kind'), 'unknown')}/"
        f"{safe_str(request.get('delivery_level'), 'unknown')}"
    )


def self_exploration_summary(exploration: dict[str, Any]) -> str:
    return (
        "self_exploration:"
        f"{safe_str(exploration.get('status'), 'unknown')}/"
        f"{safe_str(exploration.get('research_route'), 'none')}/"
        f"{safe_str(exploration.get('research_execution_level'), 'none')}/"
        f"{safe_str(exploration.get('provider_results'), '0')}"
    )


def bounded_closed_loop_notes(closed_loop: dict[str, Any], *, limit: int = 2) -> list[str]:
    return [safe_str(note) for note in closed_loop.get("notes", [])[:limit]]


def self_thought_research_summary(thought: dict[str, Any]) -> str:
    return f"self_thought_research:{safe_str(thought.get('research_route'), 'unknown')}"


def request_allows_desktop_candidate(request: dict[str, Any]) -> bool:
    return safe_str(request.get("status")) in {"ready", "candidate_only"}


def autonomous_outward_is_queued(auto_outward: dict[str, Any]) -> bool:
    return as_bool(auto_outward.get("queued"), default=False)


def desktop_candidate_request_notes(request: dict[str, Any]) -> list[str]:
    return [safe_str(note) for note in request.get("notes", [])[:4]]


def autonomous_outward_summary(auto_outward: dict[str, Any]) -> str:
    prepared = auto_outward.get("prepared_request")
    prepared_source = safe_str(prepared.get("source"), "none") if isinstance(prepared, dict) else "none"
    return (
        "autonomous_outward:"
        f"{safe_str(auto_outward.get('status'), 'unknown')}/"
        f"{str(as_bool(auto_outward.get('queued'), default=False)).lower()}/"
        f"{safe_str(auto_outward.get('send_status'), 'none')}/"
        f"{prepared_source}"
    )
