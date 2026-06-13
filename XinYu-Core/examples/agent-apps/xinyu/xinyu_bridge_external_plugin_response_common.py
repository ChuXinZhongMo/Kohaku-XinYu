from __future__ import annotations

from typing import Any, Callable


def limited_notes(notes: Any, limit: int, safe_str: Callable[..., str]) -> list[str]:
    try:
        return [safe_str(note) for note in notes[:limit]]
    except (KeyError, TypeError):
        return []


def external_plugin_response_payload(
    *,
    ok: bool,
    accepted: bool,
    result: str,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any] | None = None,
    execution: dict[str, Any] | None = None,
    summary: list[str] | None = None,
    sessions: int,
    notes: list[str],
    error_code: str | None = None,
    memory_changed: bool = False,
    session_created: bool = False,
    plugin: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": ok,
        "accepted": accepted,
        "result": result,
        "plugin_id": plugin_id,
        "capability": capability,
        "prepared": prepared or {},
        "execution": execution or {},
        "summary": summary or [],
    }
    if error_code is not None:
        payload["error_code"] = error_code
    payload.update(
        {
            "memory_changed": memory_changed,
            "session_created": session_created,
            "sessions": sessions,
            "notes": notes,
        }
    )
    if plugin is not None:
        payload["plugin"] = plugin
    return payload
