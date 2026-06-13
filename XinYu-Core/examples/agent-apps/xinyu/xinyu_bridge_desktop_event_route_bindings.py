from __future__ import annotations

from typing import Any

from xinyu_bridge_desktop_event_helpers import chat_finished_payload
from xinyu_bridge_desktop_event_helpers import chat_finished_severity
from xinyu_bridge_desktop_event_helpers import chat_started_payload
from xinyu_bridge_desktop_event_helpers import maybe_enqueue_tts as _maybe_enqueue_tts
from xinyu_bridge_desktop_event_helpers import memory_recall_notes
from xinyu_bridge_desktop_event_helpers import memory_recall_payload
from xinyu_bridge_desktop_event_helpers import memory_recall_remember_item
from xinyu_bridge_desktop_event_helpers import memory_recall_should_skip
from xinyu_bridge_desktop_event_helpers import memory_recall_top_sources
from xinyu_bridge_desktop_event_routes import publish_chat_finished as _publish_chat_finished
from xinyu_bridge_desktop_event_routes import publish_chat_started as _publish_chat_started
from xinyu_bridge_desktop_event_routes import publish_memory_recall as _publish_memory_recall
from xinyu_bridge_payload_policy import owner_private_payload_matches
from xinyu_bridge_values import dedupe
from xinyu_bridge_values import safe_str
from xinyu_sent_reply_index import visible_text_hash


def _dependency(scope: dict[str, Any] | None, name: str, fallback: Any) -> Any:
    if scope is None:
        return fallback
    return scope.get(name, fallback)


def maybe_enqueue_tts(
    runtime: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    status: str,
    reply_hash: str,
    session_key: str,
    turn_id: str,
    dependency_scope: dict[str, Any] | None = None,
) -> None:
    _maybe_enqueue_tts(
        getattr(runtime, "tts_output", None),
        payload,
        reply=reply,
        status=status,
        reply_hash=reply_hash,
        session_key=session_key,
        turn_id=turn_id,
        safe_str_func=_dependency(dependency_scope, "_safe_str", safe_str),
        owner_private_payload_matches_func=_dependency(
            dependency_scope,
            "owner_private_payload_matches",
            owner_private_payload_matches,
        ),
        visible_text_hash_func=_dependency(dependency_scope, "visible_text_hash", visible_text_hash),
    )


async def publish_chat_started(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    started_at: str,
    active_sessions: int,
    dependency_scope: dict[str, Any] | None = None,
) -> None:
    await _publish_chat_started(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        started_at=started_at,
        active_sessions=active_sessions,
        chat_started_payload_func=_dependency(dependency_scope, "_chat_started_payload", chat_started_payload),
    )


async def publish_chat_finished(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    started_at: str,
    finished_at: str,
    elapsed_ms: int,
    status: str,
    notes: list[str] | tuple[str, ...] | None,
    memory_changed: bool,
    archive_message_ids: list[Any] | tuple[Any, ...] | None,
    reply_hash: str,
    recall_event_id: str,
    recall_count: int,
    top_recall_sources: list[str] | tuple[str, ...] | None,
    dependency_scope: dict[str, Any] | None = None,
) -> None:
    await _publish_chat_finished(
        runtime,
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=started_at,
        finished_at=finished_at,
        elapsed_ms=elapsed_ms,
        status=status,
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=archive_message_ids,
        reply_hash=reply_hash,
        recall_event_id=recall_event_id,
        recall_count=recall_count,
        top_recall_sources=top_recall_sources,
        chat_finished_payload_func=_dependency(dependency_scope, "_chat_finished_payload", chat_finished_payload),
        chat_finished_severity_func=_dependency(dependency_scope, "_chat_finished_severity", chat_finished_severity),
        safe_str_func=_dependency(dependency_scope, "_safe_str", safe_str),
        visible_text_hash_func=_dependency(dependency_scope, "visible_text_hash", visible_text_hash),
    )


async def publish_memory_recall(
    runtime: Any,
    payload: dict[str, Any],
    result: Any,
    *,
    session_key: str,
    turn_id: str,
    dependency_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await _publish_memory_recall(
        runtime,
        payload,
        result,
        session_key=session_key,
        turn_id=turn_id,
        memory_recall_notes_func=_dependency(dependency_scope, "_memory_recall_notes", memory_recall_notes),
        memory_recall_should_skip_func=_dependency(
            dependency_scope,
            "_memory_recall_should_skip",
            memory_recall_should_skip,
        ),
        memory_recall_top_sources_func=_dependency(
            dependency_scope,
            "_memory_recall_top_sources",
            memory_recall_top_sources,
        ),
        memory_recall_payload_func=_dependency(dependency_scope, "_memory_recall_payload", memory_recall_payload),
        memory_recall_remember_item_func=_dependency(
            dependency_scope,
            "_memory_recall_remember_item",
            memory_recall_remember_item,
        ),
        dedupe_func=_dependency(dependency_scope, "_dedupe", dedupe),
        safe_str_func=_dependency(dependency_scope, "_safe_str", safe_str),
    )


__all__ = [
    "maybe_enqueue_tts",
    "publish_chat_finished",
    "publish_chat_started",
    "publish_memory_recall",
]
