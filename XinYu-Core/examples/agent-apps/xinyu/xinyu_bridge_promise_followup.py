from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_payload_policy import owner_private_payload_matches
from xinyu_bridge_promise_candidate import candidate as _candidate
from xinyu_bridge_promise_candidate import owner_private_user_id as _owner_private_user_id
from xinyu_bridge_stores import write_promise_followup_state_text
from xinyu_bridge_promise_markers import (
    PROMISE_FOLLOWUP_DONE_MARKERS,
    PROMISE_FOLLOWUP_REPLY_MARKERS,
    PROMISE_FOLLOWUP_STATE_REL,
    PROMISE_FOLLOWUP_USER_MARKERS,
)
from xinyu_bridge_promise_review import run_review as _run_review
from xinyu_bridge_promise_review import schedule_if_needed as _schedule_if_needed
from xinyu_bridge_promise_state import write_state as _write_state
from xinyu_bridge_promises import compact_promise_text
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_values import as_str_set, dedupe, safe_str
from xinyu_qq_outbox import enqueue_qq_outbox_message


def owner_private_user_id(runtime: Any) -> str:
    return _owner_private_user_id(runtime, as_str_set_func=as_str_set)


def candidate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    user_markers: tuple[str, ...] = PROMISE_FOLLOWUP_USER_MARKERS,
    reply_markers: tuple[str, ...] = PROMISE_FOLLOWUP_REPLY_MARKERS,
    done_markers: tuple[str, ...] = PROMISE_FOLLOWUP_DONE_MARKERS,
    model_codex_task: str = "",
) -> dict[str, str]:
    return _candidate(
        runtime,
        payload,
        user_text=user_text,
        reply=reply,
        session_key=session_key,
        owner_private_user_id_func=owner_private_user_id,
        owner_private_payload_matches_func=owner_private_payload_matches,
        compact_promise_text_func=compact_promise_text,
        safe_str_func=safe_str,
        user_markers=user_markers,
        reply_markers=reply_markers,
        done_markers=done_markers,
        model_codex_task=model_codex_task,
    )


def schedule_if_needed(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    message_func: Callable[[dict[str, str]], str],
    user_markers: tuple[str, ...] = PROMISE_FOLLOWUP_USER_MARKERS,
    reply_markers: tuple[str, ...] = PROMISE_FOLLOWUP_REPLY_MARKERS,
    done_markers: tuple[str, ...] = PROMISE_FOLLOWUP_DONE_MARKERS,
    model_codex_task: str = "",
) -> dict[str, Any]:
    return _schedule_if_needed(
        runtime,
        payload,
        user_text=user_text,
        reply=reply,
        session_key=session_key,
        message_func=message_func,
        candidate_func=candidate,
        write_state_func=write_state,
        run_review_func=run_review,
        create_task_func=asyncio.create_task,
        to_thread_func=asyncio.to_thread,
        user_markers=user_markers,
        reply_markers=reply_markers,
        done_markers=done_markers,
        model_codex_task=model_codex_task,
    )


def run_review(
    runtime: Any,
    followup: dict[str, str],
    *,
    message_func: Callable[[dict[str, str]], str],
) -> dict[str, Any]:
    return _run_review(
        runtime,
        followup,
        message_func=message_func,
        enqueue_message_func=enqueue_qq_outbox_message,
        write_state_func=write_state,
        safe_str_func=safe_str,
    )


def write_state(
    runtime: Any,
    followup: dict[str, str],
    *,
    status: str,
    message_id: str,
    notes: list[str],
    state_rel: Path = PROMISE_FOLLOWUP_STATE_REL,
) -> None:
    _write_state(
        runtime,
        followup,
        status=status,
        message_id=message_id,
        notes=notes,
        atomic_write_text_func=write_promise_followup_state_text,
        normalize_bridge_reply_func=normalize_bridge_reply,
        dedupe_func=dedupe,
        safe_str_func=safe_str,
        state_rel=state_rel,
    )
