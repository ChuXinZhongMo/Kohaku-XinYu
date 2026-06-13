from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


RECENT_PROACTIVE_MAX_AGE_SECONDS = 6 * 3600


def owner_private_payload_impl(runtime: Any, *, source: str, message_id: str = "") -> dict[str, Any]:
    owner_user_id = runtime._owner_private_user_id()
    session_id = f"qq:private:{owner_user_id}" if owner_user_id else "qq:private:owner"
    return {
        "platform": "qq",
        "adapter": "xinyu_core_bridge",
        "message_type": "private_proactive",
        "session_id": session_id,
        "user_id": owner_user_id,
        "message_id": message_id,
        "metadata": {
            "source": source,
            "is_owner_user": True,
            "proactive_outbound": True,
        },
    }


def append_assistant_to_dialogue_tail_impl(
    runtime: Any,
    session_key: str,
    message: str,
    *,
    recorded_at: str = "",
    safe_str_func: Callable[..., str],
    load_dialogue_tail_func: Callable[..., list[dict[str, Any]]],
    save_dialogue_tail_func: Callable[..., bool],
) -> bool:
    clean = safe_str_func(message).strip()
    if not clean:
        return False
    tail = load_dialogue_tail_func(
        runtime.xinyu_dir,
        session_key,
        max_entries=runtime.dialogue_persisted_tail_entries,
        include_timestamps=True,
    )
    for item in tail[-8:]:
        if item.get("role") == "assistant" and safe_str_func(item.get("content")).strip() == clean:
            return False
    tail.append(
        {
            "role": "assistant",
            "content": clean,
            "recorded_at": recorded_at or datetime.now().astimezone().isoformat(),
        }
    )
    tail.sort(key=lambda item: safe_str_func(item.get("recorded_at")))
    return save_dialogue_tail_func(
        runtime.xinyu_dir,
        session_key,
        tail,
        max_entries=runtime.dialogue_persisted_tail_entries,
    )


def sync_recent_proactive_to_dialogue_tail_impl(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    read_text_safe_func: Callable[..., str],
    state_field_func: Callable[..., str],
    seconds_since_iso_func: Callable[..., float],
    safe_str_func: Callable[..., str],
    save_dialogue_tail_func: Callable[..., bool],
) -> bool:
    if not runtime._owner_private_payload_matches(payload):
        return False
    dispatch = read_text_safe_func(runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
    if state_field_func(dispatch, "last_claim_status") not in {"claimed", "sent"}:
        return False
    message = state_field_func(dispatch, "last_claimed_message")
    if not message or message in {"none", "unknown"}:
        return False
    if seconds_since_iso_func(state_field_func(dispatch, "last_claimed_at"), default=999999.0) > (
        RECENT_PROACTIVE_MAX_AGE_SECONDS
    ):
        return False
    for item in session.dialogue_tail[-8:]:
        if item.get("role") == "assistant" and safe_str_func(item.get("content")).strip() == message:
            return False
    session.dialogue_tail.append(
        {
            "role": "assistant",
            "content": message,
            "recorded_at": state_field_func(dispatch, "last_claimed_at") or datetime.now().astimezone().isoformat(),
        }
    )
    session.dialogue_tail.sort(key=lambda item: safe_str_func(item.get("recorded_at")))
    if len(session.dialogue_tail) > runtime.dialogue_session_tail_entries:
        del session.dialogue_tail[:-runtime.dialogue_session_tail_entries]
    try:
        save_dialogue_tail_func(
            runtime.xinyu_dir,
            session.key,
            session.dialogue_tail,
            max_entries=runtime.dialogue_persisted_tail_entries,
        )
    except Exception:
        pass
    return True
