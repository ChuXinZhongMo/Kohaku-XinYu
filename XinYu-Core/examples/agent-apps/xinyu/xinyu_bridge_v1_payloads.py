from __future__ import annotations

from datetime import datetime
from typing import Any


V1_OWNER_SIMPLE_CANARY_ENV = "XINYU_V1_OWNER_SIMPLE_CANARY"
V1_CANARY_GREETING_TEXTS = frozenset({"hi", "hello", "hey", "早", "早安", "晚上好", "你好", "在吗"})
V1_CANARY_ACK_TEXTS = frozenset({"嗯", "嗯嗯", "哦", "好", "好的", "好哦", "行", "知道了", "ok"})


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def timestamp_or_now_iso(value: Any = None) -> str:
    text = safe_str(value).strip()
    if not text:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def command_id(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return safe_str(metadata.get("desktop_command_id") or payload.get("command_id"))


def with_metadata(payload: dict[str, Any], **metadata_updates: Any) -> dict[str, Any]:
    updated = dict(payload)
    metadata = updated.get("metadata")
    updated["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
    updated["metadata"].update(metadata_updates)
    return updated


def shadow_payload(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    safe_str_func=safe_str,
) -> dict[str, Any]:
    updated = with_metadata(payload, v1_shadow_source="xinyu_core_bridge")
    updated.setdefault("text", text)
    user_id = safe_str_func(updated.get("user_id")).strip()
    if user_id and user_id in runtime.v1_owner_user_ids:
        updated["metadata"]["is_owner_user"] = True
    return updated


def owner_canary_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return with_metadata(
        payload,
        is_owner_user=True,
        v1_canary_source="xinyu_core_bridge",
    )


def build_canary_notes(
    *,
    route: str,
    elapsed_ms: int,
    canary_reasons: list[str],
    v1_reply: Any,
    event_sidecar: dict[str, Any],
    cleanup: dict[str, Any],
    guard_flags: list[str],
    safe_str_func=safe_str,
) -> list[str]:
    notes: list[str] = [
        "v1_canary_intercepted",
        f"v1_canary_route:{route}",
        f"v1_canary_elapsed_ms:{elapsed_ms}",
    ]
    notes.extend(canary_reasons[:3])
    notes.extend(safe_str_func(note) for note in getattr(v1_reply, "notes", ())[:5])
    notes.extend(safe_str_func(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    return notes


def build_canary_response(
    *,
    payload: dict[str, Any],
    reply: str,
    memory_changed: bool,
    turn_id: str,
    session_key: str,
    reply_hash: str,
    route: str,
    trace_id: str,
    elapsed_ms: int,
    notes: list[str],
    command_id_func=command_id,
) -> dict[str, Any]:
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": command_id_func(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "v1_canary": {
            "scope": "owner_private_simple_messages_only",
            "route": route,
            "trace_id": trace_id,
            "elapsed_ms": elapsed_ms,
            "fallback_available": True,
        },
        "notes": notes,
    }
