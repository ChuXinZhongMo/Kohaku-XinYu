from __future__ import annotations

from datetime import datetime
from typing import Any

from xinyu_bridge_desktop_event_helpers import chat_finished_payload as _chat_finished_payload
from xinyu_bridge_desktop_event_helpers import chat_finished_severity as _chat_finished_severity
from xinyu_bridge_desktop_event_helpers import chat_started_payload as _chat_started_payload
from xinyu_bridge_desktop_event_helpers import memory_recall_notes as _memory_recall_notes
from xinyu_bridge_desktop_event_helpers import memory_recall_payload as _memory_recall_payload
from xinyu_bridge_desktop_event_helpers import memory_recall_remember_item as _memory_recall_remember_item
from xinyu_bridge_desktop_event_helpers import memory_recall_should_skip as _memory_recall_should_skip
from xinyu_bridge_desktop_event_helpers import memory_recall_top_sources as _memory_recall_top_sources
from xinyu_bridge_desktop_event_helpers import publish_event as _publish_event
from xinyu_bridge_desktop_event_helpers import publish_event_threadsafe as _publish_event_threadsafe
from xinyu_bridge_desktop_event_route_bindings import maybe_enqueue_tts as _bound_maybe_enqueue_tts
from xinyu_bridge_desktop_event_route_bindings import publish_chat_finished as _bound_publish_chat_finished
from xinyu_bridge_desktop_event_route_bindings import publish_chat_started as _bound_publish_chat_started
from xinyu_bridge_desktop_event_route_bindings import publish_memory_recall as _bound_publish_memory_recall
from xinyu_bridge_payload_policy import owner_private_payload_matches
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_sent_reply_index import visible_text_hash


_DESKTOP_EVENT_SOURCE = "xinyu_core_bridge"
_RUNTIME_PATCHABLE_DEPENDENCIES = (
    _chat_finished_payload,
    _chat_finished_severity,
    _chat_started_payload,
    _dedupe,
    _memory_recall_notes,
    _memory_recall_payload,
    _memory_recall_remember_item,
    _memory_recall_should_skip,
    _memory_recall_top_sources,
    _safe_str,
    owner_private_payload_matches,
    visible_text_hash,
)


async def desktop_publish_event(
    runtime: Any,
    event_type: str,
    payload: dict[str, Any],
    *,
    privacy: str = "internal_summary",
    severity: str | None = None,
) -> dict[str, Any]:
    return await _publish_event(
        runtime.desktop_event_bus,
        event_type,
        payload,
        source=_DESKTOP_EVENT_SOURCE,
        privacy=privacy,
        severity=severity,
    )


def desktop_publish_event_threadsafe(
    runtime: Any,
    event_type: str,
    payload: dict[str, Any],
    *,
    privacy: str = "internal_summary",
    severity: str | None = None,
) -> None:
    _publish_event_threadsafe(
        runtime.desktop_event_bus,
        event_type,
        payload,
        source=_DESKTOP_EVENT_SOURCE,
        privacy=privacy,
        severity=severity,
    )


def maybe_enqueue_tts(
    runtime: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    status: str,
    reply_hash: str,
    session_key: str,
    turn_id: str,
) -> None:
    _bound_maybe_enqueue_tts(
        runtime,
        payload,
        reply=reply,
        status=status,
        reply_hash=reply_hash,
        session_key=session_key,
        turn_id=turn_id,
        dependency_scope=globals(),
    )


async def desktop_publish_chat_started(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    started_at: str,
    active_sessions: int,
) -> None:
    await _bound_publish_chat_started(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        started_at=started_at,
        active_sessions=active_sessions,
        dependency_scope=globals(),
    )


async def desktop_publish_chat_finished(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    started_at: str,
    elapsed_ms: int,
    status: str,
    notes: list[str] | tuple[str, ...] | None = None,
    memory_changed: bool = False,
    archive_message_ids: list[Any] | tuple[Any, ...] | None = None,
    reply_hash: str = "",
    recall_event_id: str = "",
    recall_count: int = 0,
    top_recall_sources: list[str] | tuple[str, ...] | None = None,
) -> None:
    await _bound_publish_chat_finished(
        runtime,
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=started_at,
        finished_at=datetime.now().astimezone().isoformat(),
        elapsed_ms=elapsed_ms,
        status=status,
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=archive_message_ids,
        reply_hash=reply_hash,
        recall_event_id=recall_event_id,
        recall_count=recall_count,
        top_recall_sources=top_recall_sources,
        dependency_scope=globals(),
    )


async def desktop_publish_memory_recall(
    runtime: Any,
    payload: dict[str, Any],
    result: Any,
    *,
    session_key: str,
    turn_id: str,
) -> dict[str, Any]:
    return await _bound_publish_memory_recall(
        runtime,
        payload,
        result,
        session_key=session_key,
        turn_id=turn_id,
        dependency_scope=globals(),
    )
