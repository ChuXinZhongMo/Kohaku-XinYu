from __future__ import annotations

from typing import Any, Callable


def runtime_repair_status_notes(
    *,
    digest_ok: bool,
    gateway_ok: bool,
    event_sidecar: dict[str, Any],
    guard_flags: list[str],
    cleanup: dict[str, Any],
    safe_str_func: Callable[..., str],
) -> list[str]:
    notes: list[str] = [
        "runtime_repair_status_intercepted",
        f"core_digest:{'ok' if digest_ok else 'mismatch'}",
        f"qq_gateway:{'listening' if gateway_ok else 'not_listening'}",
    ]
    notes.extend(safe_str_func(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    return notes


def runtime_repair_status_result(
    *,
    reply: str,
    memory_changed: bool,
    turn_id: str,
    session_key: str,
    reply_hash: str,
    digest_ok: bool,
    gateway_ok: bool,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "runtime_repair_status": {
            "core_digest": "ok" if digest_ok else "mismatch",
            "qq_gateway": "listening" if gateway_ok else "not_listening",
        },
        "notes": notes,
    }
