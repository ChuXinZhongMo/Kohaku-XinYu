from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

from xinyu_bridge_values import safe_str
from xinyu_text_variants import readable_markers


OWNER_REPLY_PREVIEW_KEEP_MARKERS = readable_markers(
    "drop it",
    "let it go",
    "stop thinking about it",
    "stop bringing it up",
    "do not bring it up",
    "don't bring it up",
    "do not ask again",
    "don't ask again",
    "annoying",
    "too much",
    "\u522b\u518d\u63d0",
    "\u522b\u95ee",
    "\u4e0d\u7528\u518d\u63d0",
    "\u4e00\u76f4\u60e6\u8bb0",
    "\u6709\u70b9\u95ee\u9898",
    "\u592a\u70e6",
)


def one_line_preview(value: Any, *, limit: int = 180, safe_str_func: Callable[..., str] = safe_str) -> str:
    text = re.sub(r"\s+", " ", safe_str_func(value)).strip()
    if not text:
        return "none"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def owner_reply_preview(
    value: Any,
    *,
    keep_markers: tuple[str, ...] = OWNER_REPLY_PREVIEW_KEEP_MARKERS,
    safe_str_func: Callable[..., str] = safe_str,
    one_line_preview_func: Callable[..., str] = one_line_preview,
) -> str:
    text = safe_str_func(value)
    lowered = text.lower()
    if not any(marker.lower() in lowered for marker in keep_markers):
        return "preview_redacted"
    return one_line_preview_func(text)


def short_sha256_ref(value: Any, *, safe_str_func: Callable[..., str]) -> str:
    return hashlib.sha256(safe_str_func(value).encode("utf-8", errors="replace")).hexdigest()[:16]


def owner_reply_summary_block(
    *,
    answered_at: str,
    owner_reply_preview_text: str,
    owner_reply_ref: str,
    xinyu_reply_ref: str,
) -> str:
    return (
        "\n## Last Owner Reply To Proactive\n"
        f"- owner_replied_at: {answered_at}\n"
        f"- owner_reply_preview: {owner_reply_preview_text}\n"
        f"- owner_reply_ref: sha256:{owner_reply_ref}\n"
        f"- xinyu_reply_ref: sha256:{xinyu_reply_ref}\n"
        "- raw_owner_reply_retained: false\n"
        "- visible_reply_text_retained: false\n"
    )
