from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
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
    return await asyncio.to_thread(register_sent_reply_ack, runtime.xinyu_dir, payload)


async def goldmark_mark_request(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    return await asyncio.to_thread(mark_goldmark_request_bridge, runtime.xinyu_dir, payload)
