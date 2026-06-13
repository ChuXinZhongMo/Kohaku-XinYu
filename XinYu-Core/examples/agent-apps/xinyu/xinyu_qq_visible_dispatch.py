from __future__ import annotations

import asyncio
from typing import Any

from xinyu_qq_gateway_utils import safe_str as _safe_str
from xinyu_qq_models import PreparedMessage, ReplyTarget
from xinyu_qq_visible_send_shadow import record_visible_send_shadow
from xinyu_visible_reply_guard import dedupe_visible_reply
from xinyu_visible_text_sanitizer import sanitize_visible_text


def session_id(target: ReplyTarget) -> str:
    if target.message_kind == "group":
        return f"qq:group:{target.group_id or 'unknown'}:{target.user_id}"
    return f"qq:private:{target.user_id}"


def visible_reply(gateway: Any, text: str) -> str:
    reply = text.strip()
    if reply in {"[WAITING]", "WAITING"}:
        return ""
    reply = sanitize_visible_text(reply).strip()
    reply = dedupe_visible_reply(reply).text
    max_reply_chars = getattr(gateway.config, "max_reply_chars", 0)
    if max_reply_chars and len(reply) > max_reply_chars:
        return reply[:max_reply_chars].rstrip() + "\n[truncated]"
    return reply


async def send_visible_reply(
    gateway: Any,
    websocket: Any,
    prepared: PreparedMessage,
    reply: str,
    core_response: dict[str, Any],
) -> dict[str, Any] | None:
    bubbles = gateway._visible_reply_bubbles(prepared, reply, core_response)
    if not bubbles:
        return None
    responses: list[dict[str, Any] | None] = []
    for index, bubble in enumerate(bubbles):
        if index > 0:
            delay = max(0.0, gateway.config.reply_bubble_delay_seconds)
            if delay:
                await asyncio.sleep(delay)
        responses.append(await gateway.send_reply(websocket, prepared.target, bubble))
    return combined_reply_action_response(gateway, responses)


def record_direct_visible_send_shadow(
    gateway: Any,
    prepared: PreparedMessage,
    reply: str,
    core_response: dict[str, Any],
) -> dict[str, Any]:
    payload = prepared.payload if isinstance(prepared.payload, dict) else {}
    return record_visible_send_shadow(
        gateway.xinyu_dir,
        reply=reply,
        source="direct_chat_pre_send",
        route=_safe_str(core_response.get("route") or prepared.route or "chat"),
        target_kind=prepared.target.message_kind,
        session_id=_safe_str(core_response.get("session_id") or payload.get("session_id")),
        turn_id=_safe_str(core_response.get("turn_id")),
        reply_hash=_safe_str(core_response.get("reply_hash")),
        metadata={
            "source_route": prepared.route or "chat",
            "message_type": prepared.target.message_kind,
        },
    )


def record_outbox_visible_send_shadow(
    gateway: Any,
    claim: dict[str, Any],
    target: ReplyTarget,
    message: str,
    *,
    delivery_kind: str,
) -> dict[str, Any]:
    metadata = claim.get("metadata")
    metadata = dict(metadata) if isinstance(metadata, dict) else {}
    return record_visible_send_shadow(
        gateway.xinyu_dir,
        reply=message,
        source="qq_outbox_pre_send",
        route=_safe_str(metadata.get("source_route") or claim.get("source") or "qq_outbox"),
        target_kind=target.message_kind,
        session_id=_safe_str(metadata.get("session_id")),
        turn_id=_safe_str(metadata.get("turn_id") or metadata.get("source_turn_id") or metadata.get("runtime_turn_id")),
        message_id=_safe_str(claim.get("message_id")),
        delivery_kind=delivery_kind,
        reply_hash=_safe_str(metadata.get("visible_text_hash") or metadata.get("reply_hash")),
        metadata={
            "outbox_source": claim.get("source"),
            "outbox_message_type": claim.get("message_type"),
            "source_route": metadata.get("source_route"),
            "delivery_kind": delivery_kind,
            "message_type": target.message_kind,
        },
    )


def combined_reply_action_response(gateway: Any, responses: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    if not responses:
        return None
    if len(responses) == 1:
        return responses[0]
    message_ids: list[str] = []
    delivery_kinds: list[str] = []
    fallback_reasons: list[str] = []
    errors: list[str] = []
    for response in responses:
        ok, adapter_message_id, adapter_error = gateway._onebot_action_result(response)
        if isinstance(response, dict):
            delivery_kind = _safe_str(response.get("xinyu_delivery_kind")).strip()
            if not delivery_kind:
                data = response.get("data")
                if isinstance(data, dict):
                    delivery_kind = _safe_str(data.get("delivery_kind")).strip()
            if delivery_kind:
                delivery_kinds.append(delivery_kind)
            fallback_reason = _safe_str(response.get("xinyu_voice_fallback_reason")).strip()
            if fallback_reason:
                fallback_reasons.append(fallback_reason)
        if ok and adapter_message_id:
            message_ids.append(adapter_message_id)
        elif adapter_error:
            errors.append(adapter_error)
    if message_ids:
        if not delivery_kinds:
            combined_kind = "text"
        else:
            combined_kind = delivery_kinds[0] if all(kind == delivery_kinds[0] for kind in delivery_kinds) else "mixed"
        return {
            "status": "ok",
            "retcode": 0,
            "xinyu_delivery_kind": combined_kind,
            "xinyu_voice_fallback_reason": "; ".join(fallback_reasons),
            "data": {
                "message_id": ",".join(message_ids),
                "reply_bubble_message_ids": message_ids,
                "reply_bubble_delivery_kinds": delivery_kinds,
                "reply_bubble_count": len(responses),
                "delivery_kind": combined_kind,
            },
            "message": "; ".join(errors),
        }
    return responses[-1]
