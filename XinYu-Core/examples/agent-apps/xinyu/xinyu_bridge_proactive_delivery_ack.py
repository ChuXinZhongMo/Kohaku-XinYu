from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_proactive_delivery_contract import is_proactive_outbox_message_id
from xinyu_bridge_proactive_delivery_support import ack_delivery_severity, result_notes


async def acknowledge_proactive(
    runtime: Any,
    payload: dict[str, Any],
    *,
    proactive_ack_bridge_func: Callable[..., Any],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    result = await proactive_ack_bridge_func(
        xinyu_dir=runtime.xinyu_dir,
        memory_root=runtime.memory_root,
        payload=payload,
        cleanup_idle_sessions=runtime._cleanup_idle_sessions,
        session_count=lambda: len(runtime._sessions),
        lock=runtime._global_turn_lock,
    )
    if result.get("ack_recorded"):
        await runtime._desktop_publish_proactive_delivery_from_state(
            status_override=safe_str_func(result.get("ack_status"), "sent"),
            notes=result_notes(result, safe_str_func=safe_str_func),
            severity=ack_delivery_severity(result, safe_str_func=safe_str_func),
        )
    return result


async def qq_outbox_ack(
    runtime: Any,
    payload: dict[str, Any],
    *,
    proactive_ack_bridge_func: Callable[..., Any],
    ack_outbox_message_func: Callable[..., dict[str, Any]],
    to_thread_func: Callable[..., Any],
    safe_str_func: Callable[..., str],
    record_outbound_func: Callable[[Any, dict[str, Any]], None],
) -> dict[str, Any]:
    message_id = safe_str_func(payload.get("message_id")).strip()
    if is_proactive_outbox_message_id(message_id):
        result = await acknowledge_proactive(
            runtime,
            payload,
            proactive_ack_bridge_func=proactive_ack_bridge_func,
            safe_str_func=safe_str_func,
        )
        if result.get("ack_recorded") and result.get("ack_status") == "sent":
            record_outbound_func(runtime, payload)
        return result
    return await to_thread_func(ack_outbox_message_func, runtime.xinyu_dir, payload)


def acknowledge_proactive_fast(
    runtime: Any,
    payload: dict[str, Any],
    *,
    acknowledge_proactive_qq_message_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    result = acknowledge_proactive_qq_message_func(
        runtime.xinyu_dir,
        claim_id=safe_str_func(payload.get("claim_id")).strip(),
        ack_status=safe_str_func(payload.get("ack_status") or payload.get("status"), "sent").strip(),
        adapter_message_id=safe_str_func(payload.get("adapter_message_id") or payload.get("message_id")).strip(),
        adapter_error=safe_str_func(payload.get("adapter_error") or payload.get("error")).strip(),
    )
    result = {**result, "session_created": False, "sessions": len(runtime._sessions)}
    if result.get("ack_recorded"):
        runtime._desktop_publish_proactive_delivery_from_state_threadsafe(
            status_override=safe_str_func(result.get("ack_status"), "sent"),
            notes=result_notes(result, safe_str_func=safe_str_func),
            severity=ack_delivery_severity(result, safe_str_func=safe_str_func),
        )
    return result


def qq_outbox_ack_fast(
    runtime: Any,
    payload: dict[str, Any],
    *,
    acknowledge_proactive_qq_message_func: Callable[..., dict[str, Any]],
    ack_outbox_message_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
    record_outbound_func: Callable[[Any, dict[str, Any]], None],
) -> dict[str, Any]:
    message_id = safe_str_func(payload.get("message_id")).strip()
    if is_proactive_outbox_message_id(message_id):
        result = acknowledge_proactive_fast(
            runtime,
            payload,
            acknowledge_proactive_qq_message_func=acknowledge_proactive_qq_message_func,
            safe_str_func=safe_str_func,
        )
        if result.get("ack_recorded") and result.get("ack_status") == "sent":
            record_outbound_func(runtime, payload)
        return result
    return ack_outbox_message_func(runtime.xinyu_dir, payload)
