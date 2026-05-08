from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import unquote


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def message_kind(gateway: Any, event: dict[str, Any]) -> str:
    message_type = _safe_str(event.get("message_type")).lower()
    if message_type == "group" or event.get("group_id") not in {None, "", 0, "0"}:
        return "group"
    return "private"


def message_segments(gateway: Any, event: dict[str, Any]) -> list[dict[str, Any]]:
    message = event.get("message")
    if isinstance(message, list):
        return [segment for segment in message if isinstance(segment, dict)]
    raw_message = _safe_str(event.get("raw_message") or message)
    if not raw_message:
        return []
    return parse_cq_segments(raw_message)


def segment_data(gateway: Any, segment: dict[str, Any]) -> dict[str, Any]:
    data = segment.get("data")
    return data if isinstance(data, dict) else {}


def extract_text(gateway: Any, event: dict[str, Any]) -> str:
    message = event.get("message")
    if isinstance(message, list):
        parts: list[str] = []
        for segment in message:
            if not isinstance(segment, dict):
                continue
            if _safe_str(segment.get("type")).lower() != "text":
                continue
            data = segment.get("data")
            if isinstance(data, dict):
                parts.append(_safe_str(data.get("text")))
        text = "".join(parts).strip()
        if text:
            return text
        return ""
    if isinstance(message, str):
        if "[CQ:" in message:
            return strip_cq_segments(message)
        return message
    return _safe_str(event.get("raw_message"))


def sender_name(gateway: Any, event: dict[str, Any]) -> str:
    sender = event.get("sender")
    if not isinstance(sender, dict):
        return ""
    return (
        _safe_str(sender.get("card")).strip()
        or _safe_str(sender.get("nickname")).strip()
        or _safe_str(sender.get("user_id")).strip()
    )


def clean_cq_text(gateway: Any, text: str) -> str:
    return clean_cq_text_value(text)


def clean_cq_text_value(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    cleaned = re.sub(r"\[CQ:[^\]]+\]", "", stripped, flags=re.I).strip()
    return cleaned or stripped


def parse_cq_params(raw_params: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_part in raw_params.split(","):
        if "=" not in raw_part:
            continue
        key, value = raw_part.split("=", 1)
        data[key.strip()] = decode_cq_value(value)
    return data


def decode_cq_value(value: str) -> str:
    text = unquote(_safe_str(value).strip())
    return (
        text.replace("&#44;", ",")
        .replace("&#91;", "[")
        .replace("&#93;", "]")
        .replace("&amp;", "&")
    )


def cq_bracket_continues_params(raw_message: str, bracket_index: int) -> bool:
    if bracket_index + 1 >= len(raw_message) or raw_message[bracket_index + 1] != ",":
        return False
    return re.match(r"[A-Za-z0-9_-]+\s*=", raw_message[bracket_index + 2 :]) is not None


def parse_cq_segments(raw_message: str) -> list[dict[str, Any]]:
    raw = _safe_str(raw_message)
    if "[CQ:" not in raw:
        return [{"type": "text", "data": {"text": raw}}] if raw else []
    segments: list[dict[str, Any]] = []
    cursor = 0
    while cursor < len(raw):
        start = raw.find("[CQ:", cursor)
        if start < 0:
            text = raw[cursor:]
            if text:
                segments.append({"type": "text", "data": {"text": text}})
            break
        if start > cursor:
            text = raw[cursor:start]
            if text:
                segments.append({"type": "text", "data": {"text": text}})
        type_start = start + 4
        type_end = type_start
        while type_end < len(raw) and raw[type_end] not in {",", "]"}:
            type_end += 1
        if type_end >= len(raw):
            text = raw[start:]
            if text:
                segments.append({"type": "text", "data": {"text": text}})
            break
        segment_type = raw[type_start:type_end].strip().lower()
        if not segment_type:
            cursor = type_end + 1
            continue
        if raw[type_end] == "]":
            segments.append({"type": segment_type, "data": {}})
            cursor = type_end + 1
            continue
        params_start = type_end + 1
        end = params_start
        closing = -1
        while end < len(raw):
            if raw[end] == "]" and not cq_bracket_continues_params(raw, end):
                closing = end
                break
            end += 1
        if closing < 0:
            text = raw[start:]
            if text:
                segments.append({"type": "text", "data": {"text": text}})
            break
        segments.append(
            {
                "type": segment_type,
                "data": parse_cq_params(raw[params_start:closing]),
            }
        )
        cursor = closing + 1
    return segments


def strip_cq_segments(text: str) -> str:
    parts: list[str] = []
    for segment in parse_cq_segments(text):
        data = segment.get("data")
        if isinstance(data, dict) and _safe_str(segment.get("type")).lower() == "text":
            parts.append(_safe_str(data.get("text")))
    return "".join(parts).strip()


def parse_ws_message(gateway: Any, raw_message: Any) -> dict[str, Any] | None:
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8", errors="replace")
    try:
        data = json.loads(str(raw_message))
    except json.JSONDecodeError:
        print("[xinyu_qq_gateway] ignored non-json websocket message", flush=True)
        return None
    if not isinstance(data, dict):
        return None
    return data
