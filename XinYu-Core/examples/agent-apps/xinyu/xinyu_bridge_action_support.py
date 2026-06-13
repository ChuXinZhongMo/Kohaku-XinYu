from __future__ import annotations

from datetime import datetime
from typing import Any


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def command_id(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return safe_str(metadata.get("desktop_command_id") or payload.get("command_id"))


def timestamp_or_now_iso(value: Any) -> str:
    text = safe_str(value).strip()
    if text:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone().isoformat()
        except ValueError:
            pass
    return datetime.now().astimezone().isoformat()


def bridge_error_status_value(exc: BaseException) -> Any:
    status = getattr(exc, "status", None)
    return getattr(status, "value", status)


def extend_common_finish_notes(
    notes: list[str],
    *,
    event_sidecar: dict[str, Any],
    cleanup: dict[str, Any],
    guard_flags: list[str] | tuple[str, ...],
    safe_str_func=safe_str,
) -> None:
    notes.extend(safe_str_func(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
