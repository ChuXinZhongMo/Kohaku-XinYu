from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_action_feedback_surface import record_action_feedback_from_message_ack
from xinyu_action_feedback_surface import record_action_feedback_from_message_drop
from xinyu_dialogue_archive import retract_archived_assistant_message
from xinyu_dialogue_working_memory import remove_matching_assistant_reply
from xinyu_dialogue_working_memory import remove_matching_assistant_reply_from_tail
from xinyu_dialogue_working_memory import save_dialogue_tail
from xinyu_goldmark import mark_goldmark_request as mark_goldmark_request_bridge
from xinyu_review_inbox import handle_review_inbox_command
from xinyu_sent_reply_index import register_sent_reply_ack


def _sessions(runtime: Any) -> int:
    return len(getattr(runtime, "_sessions", {}))


def _ensure_open(runtime: Any) -> None:
    if getattr(runtime, "_closed", False):
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")


def _ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


async def probe(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    bridge_version: str,
) -> dict[str, Any]:
    """No-memory diagnostic endpoint.

    This intentionally does not start an Agent, create a session, render a
    reply, or inject a turn. It is for startup/status checks that should not
    become lived context.
    """
    payload = _ensure_payload(payload)
    text = runtime._payload_text(payload)
    cleanup = await runtime._cleanup_idle_sessions()
    return {
        "ok": True,
        "bridge": "xinyu_core_bridge",
        "version": bridge_version,
        "probe": "diagnostic_no_memory",
        "accepted": True,
        "reply": "probe_ok",
        "received_text_chars": len(text),
        "memory_changed": False,
        "session_created": False,
        "sessions": _sessions(runtime),
        "cleaned_sessions": cleanup["cleaned_sessions"],
        "notes": ["no_agent_turn", "no_memory_write", "no_session_created"],
    }


async def review_inbox_command(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    async with runtime._review_admin_lock:
        return await asyncio.to_thread(handle_review_inbox_command, runtime.xinyu_dir, payload)


async def message_ack(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    result = await asyncio.to_thread(register_sent_reply_ack, runtime.xinyu_dir, payload)
    await asyncio.to_thread(record_action_feedback_from_message_ack, runtime.xinyu_dir, payload, ack_result=result)
    return result


async def message_drop(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    session_id = str(payload.get("session_id") or "").strip()
    reply = str(payload.get("reply") or payload.get("visible_text") or "").strip()
    reply_hash = str(payload.get("reply_hash") or payload.get("visible_text_hash") or "").strip()
    notes: list[str] = []
    tail_removed = False

    if session_id:
        sessions_lock = getattr(runtime, "_sessions_lock", None)
        if sessions_lock is not None:
            async with sessions_lock:
                session = getattr(runtime, "_sessions", {}).get(session_id)
                tail = getattr(session, "dialogue_tail", None)
                if isinstance(tail, list):
                    result = remove_matching_assistant_reply_from_tail(tail, reply=reply, reply_hash=reply_hash)
                    tail_removed = bool(result.get("removed"))
                    notes.extend(str(note) for note in result.get("notes", []) if note)
                    if tail_removed:
                        await asyncio.to_thread(
                            save_dialogue_tail,
                            runtime.xinyu_dir,
                            session_id,
                            tail,
                            max_entries=getattr(runtime, "dialogue_persisted_tail_entries", None),
                        )
        if not tail_removed:
            tail_result = await asyncio.to_thread(
                remove_matching_assistant_reply,
                runtime.xinyu_dir,
                session_id,
                reply=reply,
                reply_hash=reply_hash,
            )
            tail_removed = bool(tail_result.get("removed"))
            notes.extend(str(note) for note in tail_result.get("notes", []) if note)
    else:
        notes.append("missing_session_id")

    archive_result = await asyncio.to_thread(
        retract_archived_assistant_message,
        runtime.xinyu_dir,
        message_id=payload.get("archive_assistant_message_id"),
        expected_reply=reply,
    )
    notes.extend(str(note) for note in archive_result.get("notes", []) if note)
    result = {
        "accepted": True,
        "dropped": True,
        "tail_removed": tail_removed,
        "archive_deleted": bool(archive_result.get("deleted")),
        "archive_deleted_count": int(archive_result.get("deleted_count") or 0),
        "notes": notes,
    }
    await asyncio.to_thread(record_action_feedback_from_message_drop, runtime.xinyu_dir, payload, drop_result=result)
    return result


async def goldmark_mark_request(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    return await asyncio.to_thread(mark_goldmark_request_bridge, runtime.xinyu_dir, payload)
