from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_model_payload import (
    has_visible_chunks,
    int_or_zero,
    owner_private_payload_matches,
    session_output_notes,
)
from xinyu_bridge_values import safe_str as _safe_str


TraceRouteStage = Callable[..., Any]
EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS = 45


def create_empty_visible_retry_event(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    session_key: str,
    safe_str_func: Callable[..., str] = _safe_str,
) -> Any:
    factory = getattr(runtime, "_create_user_input_event", None)
    if not callable(factory):
        return None
    retry_prompt = "\n".join(
        [
            "[internal visible-reply recovery]",
            "The previous model turn returned no visible text.",
            "Reply now to the immediately previous owner QQ private message.",
            "Produce a concise visible Chinese private-chat reply.",
            (
                "Do not call tools, do not output tool blocks, and do not mention this "
                "recovery, model output, logs, memory, or system mechanics."
            ),
            (
                "If the owner explicitly asked XinYu to wait or stay silent, return "
                "exactly [WAITING]. Otherwise do not stay silent."
            ),
        ]
    )
    return factory(
        retry_prompt,
        source="qq_gateway_empty_visible_retry",
        bridge_payload=payload,
        platform=safe_str_func(payload.get("platform"), "qq"),
        message_type=safe_str_func(payload.get("message_type")),
        session_id=session_key,
        user_id=safe_str_func(payload.get("user_id")),
        received_at=safe_str_func(payload.get("received_at") or payload.get("time") or ""),
        turn_id=turn_id,
        recovery_for="empty_visible_reply",
        original_text_len=len(safe_str_func(text)),
    )


async def retry_empty_visible_owner_private_output(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    turn_id: str,
    output_notes: list[str],
    trace_route_stage: TraceRouteStage,
    safe_str_func: Callable[..., str] = _safe_str,
    int_or_zero_func: Callable[[Any], int] = int_or_zero,
    session_output_notes_func: Callable[..., list[str]] = session_output_notes,
    has_visible_chunks_func: Callable[..., bool] = has_visible_chunks,
    owner_private_payload_matches_func: Callable[..., bool] = owner_private_payload_matches,
    create_retry_event_func: Callable[..., Any] = create_empty_visible_retry_event,
    empty_visible_retry_timeout_seconds: int = EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS,
    wait_for_func: Callable[..., Any] = asyncio.wait_for,
) -> list[str]:
    if has_visible_chunks_func(session) or not owner_private_payload_matches_func(runtime, payload):
        return output_notes

    trace_route_stage(
        "model_inject_empty_visible",
        route="slow_live",
        status="empty",
        notes=output_notes,
    )
    retry_event = create_retry_event_func(
        runtime,
        payload=payload,
        text=text,
        turn_id=turn_id,
        session_key=safe_str_func(getattr(session, "key", "")),
    )
    if retry_event is None:
        return output_notes + ["empty_visible_retry_unavailable"]

    retry_timeout = min(
        empty_visible_retry_timeout_seconds,
        max(1, int_or_zero_func(getattr(runtime, "turn_timeout_seconds", 1))),
    )
    trace_route_stage(
        "model_inject_empty_visible_retry_started",
        route="slow_live",
        status="running",
        notes=[f"timeout_seconds:{retry_timeout}"],
    )
    await wait_for_func(
        session.agent.inject_event(retry_event),
        timeout=retry_timeout,
    )
    retry_notes = session_output_notes_func(session)
    if has_visible_chunks_func(session):
        trace_route_stage(
            "model_inject_empty_visible_retry_finished",
            route="slow_live",
            status="ok",
            notes=retry_notes,
        )
        return retry_notes + ["empty_visible_retry_recovered"]

    trace_route_stage(
        "model_inject_empty_visible_retry_finished",
        route="slow_live",
        status="empty",
        notes=retry_notes,
    )
    return retry_notes + ["empty_visible_retry_failed"]
