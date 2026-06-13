from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable


async def proactive(
    runtime: Any,
    payload: dict[str, Any],
    *,
    proactive_bridge_func: Callable[..., Any],
    safe_str_func: Callable[..., str],
    result_notes_func: Callable[..., list[str]],
    bridge_request_error_type: type[Exception],
) -> dict[str, Any]:
    try:
        result = await proactive_bridge_func(
            xinyu_dir=runtime.xinyu_dir,
            memory_root=runtime.memory_root,
            payload=payload,
            proactive_min_interval_seconds=runtime.proactive_min_interval_seconds,
            cleanup_idle_sessions=runtime._cleanup_idle_sessions,
            session_count=lambda: len(runtime._sessions),
            lock=runtime._global_turn_lock,
        )
        if result.get("candidate_claimed"):
            await runtime._desktop_publish_proactive_delivery_from_state(
                status_override="claimed",
                notes=result_notes_func(result, safe_str_func=safe_str_func),
            )
        elif safe_str_func(result.get("preview_reply") or result.get("candidate_message")).strip():
            await runtime._desktop_publish_proactive_candidate_ready_from_state(
                notes=result_notes_func(result, safe_str_func=safe_str_func),
            )
        return result
    except ValueError as exc:
        raise bridge_request_error_type(HTTPStatus.BAD_REQUEST, str(exc)) from exc
