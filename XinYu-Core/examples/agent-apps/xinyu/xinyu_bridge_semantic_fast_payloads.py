from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
from typing import Any, Callable


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


def provider_failover_context(provider: Any, context: dict[str, Any] | None) -> Any:
    if provider is None or not context:
        return nullcontext()
    try:
        from xinyu_runtime.llm.failover import provider_failover_context as build_provider_failover_context
    except ModuleNotFoundError:
        return nullcontext()
    return build_provider_failover_context(provider, context)


def owner_private_llm_failover_context_impl(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    as_bool_func: Callable[..., bool],
    attachment_signal_func: Callable[[dict[str, Any]], bool],
    codex_request_func: Callable[[str], bool],
    local_write_request_func: Callable[[str], bool],
    safe_str_func: Callable[..., str] = safe_str,
) -> dict[str, Any]:
    if not runtime._owner_private_payload_matches(payload):
        return {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    if as_bool_func(metadata.get("control_plane"), default=False):
        return {}
    if attachment_signal_func(payload):
        return {}
    if codex_request_func(text) or local_write_request_func(text):
        return {}
    source = safe_str_func(metadata.get("source")).strip()
    if source and source != "onebot_message_event":
        return {}
    message_type = safe_str_func(payload.get("message_type")).lower()
    if message_type and not message_type.startswith("private"):
        return {}
    return {
        "enabled": True,
        "scope": "owner_private_chat",
        "source": source or "onebot_message_event",
        "turn_id": turn_id,
        "session_key": session_key,
        "user_text": text,
        "trace_root": str(runtime.xinyu_dir),
        "context": {
            "recent_turns": [],
            "persona_state": "",
            "owner_profile": "",
            "runtime_state": "",
            "memory_recall": [],
        },
        "capabilities": {
            "codex_available": False,
            "external_api_available": False,
            "local_tools_available": True,
        },
        "constraints": {
            "max_reply_chars": 240,
            "allow_tool_request": False,
            "allow_memory_candidate": False,
        },
    }
