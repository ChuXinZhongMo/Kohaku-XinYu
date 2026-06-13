from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import safe_str as _safe_str


def int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def session_output_notes(
    session: Any,
    *,
    safe_str_func: Callable[..., str] = _safe_str,
    int_or_zero_func: Callable[[Any], int] = int_or_zero,
) -> list[str]:
    chunks = getattr(session, "chunks", None)
    if isinstance(chunks, list):
        chunk_count = len(chunks)
        visible_chars = sum(len(safe_str_func(chunk)) for chunk in chunks)
    else:
        chunk_count = 0
        visible_chars = 0

    agent = getattr(session, "agent", None)
    controller = getattr(agent, "controller", None)
    raw_assistant = safe_str_func(getattr(controller, "_last_assistant_content", ""))
    llm = getattr(agent, "llm", None)
    try:
        usage = getattr(llm, "last_usage", {}) if llm is not None else {}
    except Exception:
        usage = {}
    if not isinstance(usage, dict):
        usage = {}
    try:
        tool_calls = getattr(llm, "last_tool_calls", []) if llm is not None else []
    except Exception:
        tool_calls = []
    try:
        tool_call_count = len(tool_calls or [])
    except TypeError:
        tool_call_count = 0

    notes = [
        f"chunk_count:{chunk_count}",
        f"visible_chars:{visible_chars}",
        f"raw_assistant_chars:{len(raw_assistant)}",
        f"completion_tokens:{int_or_zero_func(usage.get('completion_tokens'))}",
        f"tool_call_count:{tool_call_count}",
    ]
    if visible_chars <= 0:
        if raw_assistant:
            notes.append("empty_visible_parser_or_action_output")
        elif int_or_zero_func(usage.get("completion_tokens")) <= 0:
            notes.append("empty_completion_no_visible_tokens")
        else:
            notes.append("empty_visible_model_or_provider_output")
    return notes


def has_visible_chunks(session: Any, *, safe_str_func: Callable[..., str] = _safe_str) -> bool:
    chunks = getattr(session, "chunks", None)
    if not isinstance(chunks, list):
        return False
    return bool("".join(safe_str_func(chunk) for chunk in chunks).strip())


def owner_private_payload_matches(runtime: Any, payload: dict[str, Any]) -> bool:
    matcher = getattr(runtime, "_owner_private_payload_matches", None)
    if not callable(matcher):
        return False
    try:
        return bool(matcher(payload))
    except Exception:
        return False
