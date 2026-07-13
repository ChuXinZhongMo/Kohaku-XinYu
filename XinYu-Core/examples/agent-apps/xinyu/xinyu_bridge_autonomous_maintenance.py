from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from typing import Any

import xinyu_bridge_autonomous_note_facade as _autonomous_note_facade
from xinyu_autonomous_self_exploration import run_autonomous_self_exploration_tick
from xinyu_autonomous_outward_action import run_autonomous_outward_action_tick
from xinyu_bridge_autonomous_maintenance_payload import (
    AUTONOMOUS_MAINTENANCE_PROMPT,
    create_autonomous_maintenance_event as _payload_create_autonomous_maintenance_event,
)
from xinyu_bridge_autonomous_maintenance_response import (
    run_autonomous_maintenance_once as _response_run_autonomous_maintenance_once,
)
from xinyu_bridge_autonomous_maintenance_note_bindings import bind_note_wrappers
from xinyu_bridge_autonomous_maintenance_scheduling import (
    autonomous_maintenance_loop as _scheduling_autonomous_maintenance_loop,
    ensure_autonomous_session as _scheduling_ensure_autonomous_session,
    record_autonomous_failure as _scheduling_record_autonomous_failure,
)
from xinyu_bridge_autonomous_state import (
    trace_autonomous as _runtime_trace_autonomous,
    write_autonomous_state as _runtime_write_autonomous_state,
)
from xinyu_bridge_stores import write_autonomous_state_text
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_contextual_self_observatory import run_contextual_self_observatory
from xinyu_creative_writing import run_creative_writing_maintenance
from xinyu_daily_digest import run_daily_digest_maintenance
from xinyu_desire_drive_state import run_desire_drive_state
from xinyu_emotion_council import run_emotion_council_shadow
from xinyu_goal_outcome_observer import run_goal_outcome_observer
from xinyu_goldmark_dehydrate import run_goldmark_dehydration_maintenance
from xinyu_impulse_soup import run_impulse_soup
from xinyu_initiative_orchestrator import run_initiative_orchestrator
from xinyu_initiative_spine import run_initiative_spine
from xinyu_learning_closed_loop import record_learning_closed_loop_self_thought
from xinyu_proactivity_scorer import run_proactivity_scorer_shadow
from xinyu_proactive_request_loop import run_proactive_request_loop
from xinyu_review_inbox import run_review_inbox_maintenance
from xinyu_self_action_gateway import run_self_action_gateway
from xinyu_self_action_patch_executor import run_self_action_patch_executor
from xinyu_action_followup_proposals import run_audit_and_queue_followups
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology
from xinyu_self_thought_loop import run_self_thought_loop
from xinyu_watched_sources import run_watched_source_check


def _run_self_chosen_goal_ecology(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return run_self_chosen_goal_ecology(*args, **kwargs)


def _run_audit_and_queue_followups(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return run_audit_and_queue_followups(*args, **kwargs)


def _run_self_action_gateway(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return run_self_action_gateway(*args, **kwargs)


def _run_self_action_patch_executor(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return run_self_action_patch_executor(*args, **kwargs)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def create_autonomous_maintenance_event(runtime: Any, *, prompt: str = AUTONOMOUS_MAINTENANCE_PROMPT) -> Any:
    return _payload_create_autonomous_maintenance_event(runtime, prompt=prompt, now_iso_func=_now_iso)


def record_autonomous_failure(runtime: Any, message: str) -> None:
    _scheduling_record_autonomous_failure(runtime, message)


async def ensure_autonomous_session(runtime: Any) -> Any:
    return await _scheduling_ensure_autonomous_session(runtime, time_func=time.time)


async def autonomous_maintenance_loop(runtime: Any) -> None:
    await _scheduling_autonomous_maintenance_loop(runtime, time_func=time.time, sleep_func=asyncio.sleep)


async def run_autonomous_maintenance_once(runtime: Any) -> dict[str, Any]:
    return await _response_run_autonomous_maintenance_once(
        runtime,
        normalize_reply_func=normalize_bridge_reply,
        wait_for_func=asyncio.wait_for,
        time_func=time.time,
        now_iso_func=_now_iso,
    )


def trace_autonomous(runtime: Any, line: str) -> None:
    _runtime_trace_autonomous(runtime, line, now_iso_func=_now_iso)


def write_autonomous_state(
    runtime: Any,
    status: str,
    *,
    memory_changed: bool | None = None,
    notes: list[str] | None = None,
) -> None:
    _runtime_write_autonomous_state(
        runtime,
        status,
        memory_changed=memory_changed,
        notes=notes,
        now_iso_func=_now_iso,
        atomic_write_text_func=write_autonomous_state_text,
    )


def _load_run_github_autonomous_learning() -> Any:
    from github_autonomous_learning_engine import run_github_autonomous_learning



    return run_github_autonomous_learning


def _note_deps() -> Any:
    return sys.modules[__name__]


bind_note_wrappers(
    globals(),
    module_name=__name__,
    note_deps_func=_note_deps,
    facade=_autonomous_note_facade,
)

__all__ = (
    "AUTONOMOUS_MAINTENANCE_PROMPT",
    "Any",
    "_autonomous_note_facade",
    "_load_run_github_autonomous_learning",
    "_note_deps",
    "_now_iso",
    "_payload_create_autonomous_maintenance_event",
    "_response_run_autonomous_maintenance_once",
    "_run_audit_and_queue_followups",
    "_run_self_action_gateway",
    "_run_self_action_patch_executor",
    "_run_self_chosen_goal_ecology",
    "_runtime_trace_autonomous",
    "_runtime_write_autonomous_state",
    "_scheduling_autonomous_maintenance_loop",
    "_scheduling_ensure_autonomous_session",
    "_scheduling_record_autonomous_failure",
    "annotations",
    "asyncio",
    "autonomous_maintenance_loop",
    "bind_note_wrappers",
    "create_autonomous_maintenance_event",
    "datetime",
    "ensure_autonomous_session",
    "normalize_bridge_reply",
    "record_autonomous_failure",
    "record_learning_closed_loop_self_thought",
    "run_audit_and_queue_followups",
    "run_autonomous_maintenance_once",
    "run_autonomous_outward_action_tick",
    "run_autonomous_self_exploration_tick",
    "run_contextual_self_observatory",
    "run_creative_writing_maintenance",
    "run_daily_digest_maintenance",
    "run_desire_drive_state",
    "run_emotion_council_shadow",
    "run_goal_outcome_observer",
    "run_goldmark_dehydration_maintenance",
    "run_impulse_soup",
    "run_initiative_orchestrator",
    "run_initiative_spine",
    "run_proactive_request_loop",
    "run_proactivity_scorer_shadow",
    "run_review_inbox_maintenance",
    "run_self_action_gateway",
    "run_self_action_patch_executor",
    "run_self_chosen_goal_ecology",
    "run_self_thought_loop",
    "run_watched_source_check",
    "sys",
    "time",
    "timestamp_or_now_iso",
    "trace_autonomous",
    "write_autonomous_state",
    "write_autonomous_state_text",
)
