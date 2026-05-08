from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote

from xinyu_qq_config import as_str_list
import xinyu_qq_normalizer


QQ_FORWARD_CONTEXT_MAX_MESSAGES = 12
QQ_FORWARD_CONTEXT_MAX_TEXT_CHARS = 5000


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def forward_raw_items(payload: Any) -> list[Any]:
    if payload is None:
        return []
    if isinstance(payload, str):
        stripped = payload.strip()
        if not stripped:
            return []
        try:
            return forward_raw_items(json.loads(stripped))
        except json.JSONDecodeError:
            return [stripped]
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("messages", "message", "content", "nodes", "node", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = forward_raw_items(value)
            if nested:
                return nested
        if isinstance(value, str) and value.strip().startswith(("[", "{")):
            nested = forward_raw_items(value)
            if nested:
                return nested
    if any(key in payload for key in ("sender", "user_id", "nickname", "message", "content", "raw_message")):
        return [payload]
    return []


def extract_reply_message_id(event: dict[str, Any]) -> str:
    for key in ("reply_message_id", "reply_id", "source_message_id", "quoted_message_id", "quote_message_id"):
        value = safe_str(event.get(key)).strip()
        if value:
            return value
    reply = event.get("reply")
    if isinstance(reply, dict):
        for key in ("message_id", "id", "reply_id", "source_message_id"):
            value = safe_str(reply.get(key)).strip()
            if value:
                return value

    message = event.get("message")
    if isinstance(message, list):
        for segment in message:
            if not isinstance(segment, dict):
                continue
            if safe_str(segment.get("type")).strip().lower() != "reply":
                continue
            data = segment.get("data")
            if not isinstance(data, dict):
                continue
            for key in ("id", "message_id", "reply_id"):
                value = safe_str(data.get(key)).strip()
                if value:
                    return value

    raw_message = safe_str(event.get("raw_message") or message)
    for segment in xinyu_qq_normalizer.parse_cq_segments(raw_message):
        if safe_str(segment.get("type")).strip().lower() != "reply":
            continue
        params = xinyu_qq_normalizer.segment_data(None, segment)
        for key in ("id", "message_id", "reply_id"):
            value = safe_str(params.get(key)).strip()
            if value:
                return value
    return ""


def extract_forward_message_ids(event: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("forward_message_id", "forward_id", "forward_msg_id", "resid", "res_id"):
        ids.extend(as_str_list(event.get(key)))

    for segment in xinyu_qq_normalizer.message_segments(None, event):
        segment_type = safe_str(segment.get("type")).strip().lower()
        data = xinyu_qq_normalizer.segment_data(None, segment)
        if segment_type == "forward":
            for key in ("id", "message_id", "forward_id", "forward_msg_id", "resid", "res_id"):
                ids.extend(as_str_list(data.get(key)))
            continue
        if segment_type in {"json", "xml"}:
            ids.extend(extract_forward_ids_from_text(safe_str(data.get("data") or data.get("text") or data.get("content"))))

    raw_message = safe_str(event.get("raw_message") or event.get("message"))
    ids.extend(extract_forward_ids_from_text(raw_message))
    return list(dict.fromkeys(item.strip() for item in ids if item and item.strip()))


def extract_forward_ids_from_text(text: str) -> list[str]:
    if not text:
        return []
    candidates = []
    current = text.strip()
    for _ in range(2):
        if current and current not in candidates:
            candidates.append(current)
        decoded = unquote(current)
        if decoded == current:
            break
        current = decoded

    ids: list[str] = []
    for candidate in candidates:
        lowered = candidate.lower()
        if not any(marker in lowered for marker in ("multimsg", "forward", "resid", "m_resid")):
            continue
        try:
            decoded_json = json.loads(candidate)
        except json.JSONDecodeError:
            decoded_json = None
        ids.extend(forward_ids_from_json(decoded_json))
        for match in re.finditer(
            r"""(?ix)
            ["']?(?:m_)?resid["']?\s*[:=]\s*["']?([^"',}\]\s]+)
            |["']?forward(?:_msg)?_id["']?\s*[:=]\s*["']?([^"',}\]\s]+)
            """,
            candidate,
        ):
            ids.append(safe_str(match.group(1) or match.group(2)).strip())
    return list(dict.fromkeys(item for item in ids if item))


def forward_ids_from_json(value: Any) -> list[str]:
    ids: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered_key = safe_str(key).lower()
            if lowered_key in {"resid", "m_resid", "forward_id", "forward_msg_id"}:
                ids.extend(as_str_list(item))
            else:
                ids.extend(forward_ids_from_json(item))
    elif isinstance(value, list):
        for item in value:
            ids.extend(forward_ids_from_json(item))
    return ids


def dedupe_forward_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in messages:
        key = (
            safe_str(item.get("message_id")).strip(),
            safe_str(item.get("sender_name") or item.get("user_id")).strip(),
            safe_str(item.get("text") or item.get("rich_summary") or item.get("raw_message")).strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
