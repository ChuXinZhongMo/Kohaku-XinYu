from __future__ import annotations

from typing import Any

from xinyu_bridge_utility_common import ensure_open
from xinyu_bridge_utility_common import ensure_payload


async def message_ack(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = ensure_payload(payload, deps)
    result = await deps.to_thread(deps.register_sent_reply_ack, runtime.xinyu_dir, payload)
    await deps.to_thread(
        deps.record_action_feedback_from_message_ack,
        runtime.xinyu_dir,
        payload,
        ack_result=result,
    )
    return result


async def message_drop(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    deps: Any,
) -> dict[str, Any]:
    ensure_open(runtime, deps)
    payload = ensure_payload(payload, deps)
    reply = str(payload.get("reply") or payload.get("visible_text") or "").strip()
    reply_hash = str(payload.get("reply_hash") or payload.get("visible_text_hash") or "").strip()
    notes: list[str] = []

    tail_removed = await _drop_dialogue_tail(
        runtime,
        payload,
        reply=reply,
        reply_hash=reply_hash,
        notes=notes,
        deps=deps,
    )
    archive_result = await deps.to_thread(
        deps.retract_archived_assistant_message,
        runtime.xinyu_dir,
        message_id=payload.get("archive_assistant_message_id"),
        expected_reply=reply,
    )
    _extend_notes(notes, archive_result)
    result = {
        "accepted": True,
        "dropped": True,
        "tail_removed": tail_removed,
        "archive_deleted": bool(archive_result.get("deleted")),
        "archive_deleted_count": int(archive_result.get("deleted_count") or 0),
        "notes": notes,
    }
    await deps.to_thread(
        deps.record_action_feedback_from_message_drop,
        runtime.xinyu_dir,
        payload,
        drop_result=result,
    )
    return result


async def _drop_dialogue_tail(
    runtime: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    reply_hash: str,
    notes: list[str],
    deps: Any,
) -> bool:
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        notes.append("missing_session_id")
        return False

    if await _drop_live_session_tail(
        runtime,
        session_id,
        reply=reply,
        reply_hash=reply_hash,
        notes=notes,
        deps=deps,
    ):
        return True

    tail_result = await deps.to_thread(
        deps.remove_matching_assistant_reply,
        runtime.xinyu_dir,
        session_id,
        reply=reply,
        reply_hash=reply_hash,
    )
    _extend_notes(notes, tail_result)
    return bool(tail_result.get("removed"))


async def _drop_live_session_tail(
    runtime: Any,
    session_id: str,
    *,
    reply: str,
    reply_hash: str,
    notes: list[str],
    deps: Any,
) -> bool:
    sessions_lock = getattr(runtime, "_sessions_lock", None)
    if sessions_lock is None:
        return False
    async with sessions_lock:
        session = getattr(runtime, "_sessions", {}).get(session_id)
        tail = getattr(session, "dialogue_tail", None)
        if not isinstance(tail, list):
            return False

        result = deps.remove_matching_assistant_reply_from_tail(
            tail,
            reply=reply,
            reply_hash=reply_hash,
        )
        _extend_notes(notes, result)
        if not result.get("removed"):
            return False

        await deps.to_thread(
            deps.save_dialogue_tail,
            runtime.xinyu_dir,
            session_id,
            tail,
            max_entries=getattr(runtime, "dialogue_persisted_tail_entries", None),
        )
        return True


def _extend_notes(notes: list[str], result: dict[str, Any]) -> None:
    notes.extend(str(note) for note in result.get("notes", []) if note)
