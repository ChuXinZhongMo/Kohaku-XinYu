from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_observation_payload import (
    ObservationPayload,
    _as_bool,
    _detected_urls,
    _learning_candidate,
    _one_line,
    _parse_iso,
    _safe_str,
    _stable_hash,
    _timestamp_or_now_iso,
    normalize_observation_payload,
)
from xinyu_bridge_observation_reports import (
    _append_section,
    _ensure_observation_file,
    _header,
    _update_real_life_events,
    format_observation_block,
    observation_event_entry,
)
from xinyu_memory_event_sourcing import record_learning_observe_event

__all__ = [
    "ObservationPayload",
    "format_observation_block",
    "normalize_observation_payload",
    "observation_event_entry",
    "observe",
    "record_learning_observe_event",
    "_append_section",
    "_as_bool",
    "_detected_urls",
    "_ensure_observation_file",
    "_header",
    "_learning_candidate",
    "_one_line",
    "_parse_iso",
    "_safe_str",
    "_stable_hash",
    "_timestamp_or_now_iso",
    "_update_real_life_events",
]


async def observe(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"accepted": False, "observed": False, "reply": "", "notes": ["invalid_payload"]}

    observation = normalize_observation_payload(payload)
    if observation is None:
        return {"accepted": True, "observed": False, "reply": "", "notes": ["empty_text"]}

    async with lock:
        cleanup = await cleanup_idle_sessions()
        path = memory_root / "knowledge/group_learning_observations.md"
        _ensure_observation_file(path, observation.observed_at)
        _append_section(path, format_observation_block(observation))
        _update_real_life_events(memory_root, observation.observed_at, observation_event_entry(observation))
        sidecar_result: dict[str, Any] = {"notes": ["event_sourcing_not_run"]}
        try:
            sidecar_result = record_learning_observe_event(xinyu_dir, payload, text=observation.text)
        except Exception as exc:
            sidecar_result = {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}

    notes = ["learning_observe", "no_agent_turn", "no_reply", "session_not_created"]
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    notes.extend(_safe_str(note) for note in sidecar_result.get("notes", [])[:4])
    return {
        "accepted": True,
        "observed": True,
        "reply": "",
        "memory_changed": True,
        "session_created": False,
        "sessions": session_count(),
        "observation_id": f"obs-{observation.observation_id}",
        "learning_candidate": observation.candidate,
        "notes": notes,
    }
