from __future__ import annotations

import re
from typing import Any, Iterable


ATTACHMENT_KEYS = (
    "attachments",
    "attachment",
    "image_path",
    "file_path",
    "file_name",
    "image",
    "file",
    "raw_image",
    "raw_images",
)


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def payload_has_attachment_signal(payload: dict[str, Any]) -> bool:
    for key in ATTACHMENT_KEYS:
        value = payload.get(key)
        if isinstance(value, (list, tuple, dict)) and value:
            return True
        if safe_str(value).strip():
            return True
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        for key in ATTACHMENT_KEYS:
            value = metadata.get(key)
            if isinstance(value, (list, tuple, dict)) and value:
                return True
            if safe_str(value).strip():
                return True
    return False


def canary_payload_allowed(
    *,
    v1_enabled: bool,
    owner_simple_canary: bool,
    owner_private: bool,
    payload: dict[str, Any],
    text: str,
    owner_simple_canary_env: str,
    greeting_texts: Iterable[str],
    ack_texts: Iterable[str],
) -> tuple[bool, list[str]]:
    if not v1_enabled:
        return False, ["v1_disabled"]
    if not owner_simple_canary:
        return False, [f"{owner_simple_canary_env}=false"]
    if not owner_private:
        return False, ["not_owner_private"]
    if payload_has_attachment_signal(payload):
        return False, ["attachment_present"]
    compact = re.sub(r"\s+", "", safe_str(text)).strip()
    if not compact:
        return False, ["empty_text"]
    if "\n" in safe_str(text) or "\r" in safe_str(text):
        return False, ["multiline_text"]
    if len(compact) > 20:
        return False, ["text_too_long_for_simple_canary"]
    lowered = compact.lower()
    greetings = set(greeting_texts)
    acks = set(ack_texts)
    if compact in greetings or lowered in greetings:
        return True, ["simple_greeting"]
    if compact in acks or lowered in acks:
        return True, ["simple_ack"]
    return False, ["not_simple_greeting_or_ack"]
