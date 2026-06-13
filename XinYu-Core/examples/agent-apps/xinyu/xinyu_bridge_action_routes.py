from __future__ import annotations

import asyncio
from typing import Any

from xinyu_action_experience_digest import compose_action_digest_followup, digest_action_experience_residue
from xinyu_action_layer import codex_response_to_outcome, external_response_to_outcome
from xinyu_action_reply_composer import compose_action_reply
from xinyu_bridge_action_dispatch import execute_action_request as _runtime_execute_action_request
from xinyu_bridge_action_experience import settle_action_experience as _runtime_settle_action_experience
from xinyu_bridge_action_followups import (
    handle_action_digest_followup_turn as _runtime_handle_action_digest_followup_turn,
    handle_recent_action_followup_turn as _runtime_handle_recent_action_followup_turn,
)
from xinyu_bridge_action_layer_turn import handle_action_layer_turn as _runtime_handle_action_layer_turn
from xinyu_bridge_action_route_runtime import (
    handle_action_digest_followup_turn_runtime,
    handle_action_layer_turn_runtime,
    handle_recent_action_followup_turn_runtime,
    settle_action_experience_runtime,
)
from xinyu_bridge_action_support import (
    command_id as _command_id,
    safe_str as _safe_str,
    timestamp_or_now_iso as _timestamp_or_now_iso,
)
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_codex_delegate import looks_like_owner_local_write_request
from xinyu_experience_frame import (
    build_experience_frame,
    compose_recent_action_followup,
    write_action_experience_residue,
    write_recent_action_experience,
)
from xinyu_memory_event_sourcing import record_action_experience_event
from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash
from xinyu_tool_protocol import ActionOutcome, DELEGATED_LOCAL_RISK
from xinyu_visible_state_hygiene import sanitize_visible_state_files


def _deps() -> dict[str, Any]:
    return globals()


async def settle_action_experience(
    runtime: Any,
    payload: dict[str, Any],
    *,
    request: dict[str, Any],
    outcome: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    return await settle_action_experience_runtime(
        runtime,
        payload,
        request=request,
        outcome=outcome,
        deps=_deps(),
    )


async def handle_action_layer_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    bridge_request_error_type: type[BaseException] | None = None,
) -> dict[str, Any] | None:
    return await handle_action_layer_turn_runtime(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        bridge_request_error_type=bridge_request_error_type,
        deps=_deps(),
    )


async def handle_recent_action_followup_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
) -> dict[str, Any] | None:
    return await handle_recent_action_followup_turn_runtime(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        deps=_deps(),
    )


async def handle_action_digest_followup_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
) -> dict[str, Any] | None:
    return await handle_action_digest_followup_turn_runtime(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
        deps=_deps(),
    )
