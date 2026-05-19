from __future__ import annotations

from typing import Any

import xinyu_qq_forward_context
from xinyu_qq_config import as_str_list as _as_str_list
from xinyu_qq_gateway_utils import maybe_int as _maybe_int
from xinyu_qq_gateway_utils import safe_str as _safe_str
from xinyu_qq_models import PreparedMessage


async def upgrade_reply_file_learning(
    gateway: Any,
    websocket: Any,
    event: dict[str, Any],
    prepared: PreparedMessage | None,
) -> PreparedMessage | None:
    if prepared is None or prepared.local_reply or prepared.route != "chat":
        return prepared
    if not gateway.config.qq_file_learning_enabled:
        return prepared
    if gateway.config.qq_file_learning_private_owner_only and (
        prepared.target.message_kind != "private" or prepared.target.user_id not in gateway.config.owner_user_ids
    ):
        return prepared

    text = _safe_str(prepared.payload.get("text") or gateway._extract_text(event)).strip()
    if not gateway._reply_file_learning_intent(text):
        return prepared
    reply_message_id = gateway._extract_reply_message_id(event)
    if not reply_message_id:
        return prepared

    replied = await gateway._onebot_action_data(websocket, "get_msg", {"message_id": _maybe_int(reply_message_id)})
    if not replied:
        print(f"[xinyu_qq_gateway] could not fetch replied message id={reply_message_id}", flush=True)
        return prepared
    material = gateway._extract_learning_material(replied)
    if material is None:
        print(f"[xinyu_qq_gateway] replied message has no QQ file material id={reply_message_id}", flush=True)
        return prepared

    payload = gateway._build_learning_ingest_payload(
        event,
        target=prepared.target,
        material=material,
        text=text,
    )
    metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
    metadata.update(
        {
            "source": "qq_reply_file_message",
            "replied_message_id": reply_message_id,
            "replied_raw_message": _safe_str(replied.get("raw_message"))[:1000],
        }
    )
    payload["metadata"] = metadata
    return PreparedMessage(target=prepared.target, payload=payload, route="learning_ingest")


async def enrich_reply_context(
    gateway: Any,
    websocket: Any,
    event: dict[str, Any],
    prepared: PreparedMessage | None,
) -> PreparedMessage | None:
    if prepared is None or prepared.local_reply or prepared.route not in {"chat", "codex_execute", "package_install"}:
        return prepared
    reply_message_id = gateway._extract_reply_message_id(event)
    if not reply_message_id:
        return prepared
    metadata = prepared.payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        prepared.payload["metadata"] = metadata
    metadata["qq_reply_message_id"] = reply_message_id
    prepared.payload["reply_message_id"] = reply_message_id

    replied = await gateway._onebot_action_data(websocket, "get_msg", {"message_id": _maybe_int(reply_message_id)})
    if not replied:
        metadata["qq_reply_context_available"] = False
        metadata["qq_reply_context_notes"] = ["reply_fetch_failed"]
        return prepared
    reply_context = gateway._summarize_replied_message(replied)
    metadata["qq_reply_context_available"] = True
    metadata["qq_reply_context"] = reply_context
    prepared.payload["quoted_message"] = reply_context
    return prepared


async def enrich_forward_context(
    gateway: Any,
    websocket: Any,
    event: dict[str, Any],
    prepared: PreparedMessage | None,
) -> PreparedMessage | None:
    if prepared is None or prepared.local_reply or prepared.route not in {"chat", "codex_execute", "package_install"}:
        return prepared

    metadata = prepared.payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        prepared.payload["metadata"] = metadata

    forward_ids = gateway._extract_forward_message_ids(event)
    reply_context = metadata.get("qq_reply_context")
    if isinstance(reply_context, dict):
        forward_ids.extend(_as_str_list(reply_context.get("forward_message_ids")))
    forward_ids = list(dict.fromkeys(item for item in forward_ids if item))

    messages = embedded_forward_messages_from_event(gateway, event)
    fetched_ids: list[str] = []
    failed_ids: list[str] = []
    for forward_id in forward_ids[:3]:
        fetched = await fetch_forward_messages(gateway, websocket, forward_id)
        if fetched:
            fetched_ids.append(forward_id)
            messages.extend(fetched)
        else:
            failed_ids.append(forward_id)

    messages = gateway._dedupe_forward_messages(messages)
    if not forward_ids and not messages:
        return prepared

    context = {
        "forward_ids": forward_ids,
        "message_count": len(messages),
        "messages": messages[:xinyu_qq_forward_context.QQ_FORWARD_CONTEXT_MAX_MESSAGES],
        "fetched_ids": fetched_ids,
        "failed_ids": failed_ids,
    }
    metadata["qq_forward_message_ids"] = forward_ids
    metadata["qq_forward_context_available"] = bool(messages)
    metadata["qq_forward_message_count"] = len(messages)
    metadata["qq_forward_context"] = context
    prepared.payload["forwarded_messages"] = context
    return prepared


def embedded_forward_messages_from_event(gateway: Any, event: dict[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for segment in gateway._message_segments(event):
        segment_type = _safe_str(segment.get("type")).strip().lower()
        data = gateway._segment_data(segment)
        if segment_type == "forward":
            for key in ("messages", "message", "content", "nodes", "data"):
                value = data.get(key)
                messages.extend(forward_messages_from_payload(gateway, value))
        elif segment_type in {"json", "xml"}:
            raw = _safe_str(data.get("data") or data.get("text") or data.get("content")).strip()
            if raw.startswith(("{", "[")):
                messages.extend(forward_messages_from_payload(gateway, raw))
    return gateway._dedupe_forward_messages(messages)


async def fetch_forward_messages(gateway: Any, websocket: Any, forward_id: str) -> list[dict[str, str]]:
    if not forward_id:
        return []
    payload = await gateway._onebot_action_payload(websocket, "get_forward_msg", {"message_id": _maybe_int(forward_id)})
    messages = forward_messages_from_payload(gateway, payload)
    if messages:
        return messages
    payload = await gateway._onebot_action_payload(websocket, "get_forward_msg", {"id": forward_id})
    return forward_messages_from_payload(gateway, payload)


def forward_messages_from_payload(gateway: Any, payload: Any) -> list[dict[str, str]]:
    raw_items = gateway._forward_raw_items(payload)
    messages: list[dict[str, str]] = []
    used_chars = 0
    for item in raw_items:
        message = summarize_forward_item(gateway, item)
        if not message:
            continue
        text_len = len(_safe_str(message.get("text") or message.get("rich_summary") or message.get("raw_message")))
        if messages and used_chars + text_len > xinyu_qq_forward_context.QQ_FORWARD_CONTEXT_MAX_TEXT_CHARS:
            break
        used_chars += text_len
        messages.append(message)
        if len(messages) >= xinyu_qq_forward_context.QQ_FORWARD_CONTEXT_MAX_MESSAGES:
            break
    return messages


def summarize_forward_item(gateway: Any, item: Any) -> dict[str, str]:
    if isinstance(item, str):
        text = gateway._clean_cq_text(item)
        return {"sender_name": "", "user_id": "", "text": text[:1200], "raw_message": item[:1200], "rich_summary": ""}
    if not isinstance(item, dict):
        return {}

    node = item
    data = item.get("data")
    if isinstance(data, dict) and not any(key in item for key in ("message", "content", "raw_message")):
        node = {**item, **data}

    event_like = dict(node)
    if "message" not in event_like and "content" in node:
        event_like["message"] = node.get("content")
    if "raw_message" not in event_like:
        message_value = event_like.get("message")
        if isinstance(message_value, str):
            event_like["raw_message"] = message_value

    text = gateway._clean_cq_text(gateway._extract_text(event_like).strip())
    raw_message = _safe_str(event_like.get("raw_message")).strip()
    rich = gateway._extract_rich_message_context(event_like)
    rich_summary = _safe_str(rich.get("summary")).strip()

    sender = event_like.get("sender")
    sender_name = ""
    user_id = ""
    if isinstance(sender, dict):
        sender_name = (
            _safe_str(sender.get("card")).strip()
            or _safe_str(sender.get("nickname")).strip()
            or _safe_str(sender.get("name")).strip()
            or _safe_str(sender.get("user_id")).strip()
        )
        user_id = _safe_str(sender.get("user_id")).strip()
    sender_name = (
        sender_name
        or _safe_str(event_like.get("nickname")).strip()
        or _safe_str(event_like.get("name")).strip()
        or _safe_str(event_like.get("user_id")).strip()
    )
    user_id = user_id or _safe_str(event_like.get("user_id")).strip()

    if not text and not rich_summary and not raw_message:
        return {}
    return {
        "message_id": _safe_str(event_like.get("message_id")).strip(),
        "sender_name": sender_name[:120],
        "user_id": user_id[:80],
        "text": text[:1200],
        "raw_message": raw_message[:1200],
        "rich_summary": rich_summary[:1200],
        "time": _safe_str(event_like.get("time")).strip(),
    }
