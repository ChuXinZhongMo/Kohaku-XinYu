from __future__ import annotations

import re
from typing import Any

from xinyu_bridge_values import as_bool, safe_str


def is_recent_sticker_question(user_text: str) -> bool:
    compact = re.sub(r"\s+", "", safe_str(user_text))
    if not compact:
        return False
    exact_markers = (
        "我刚发的是什么",
        "刚发的是什么",
        "刚才发的是什么",
        "我刚发了什么",
        "刚发了什么",
        "刚才发了什么",
        "我发的是什么",
        "我发了什么",
        "刚那个表情是什么",
        "刚才那个表情是什么",
        "刚刚那个表情是什么",
    )
    if any(marker in compact for marker in exact_markers):
        return True
    return "刚" in compact and "表情" in compact and any(marker in compact for marker in ("什么", "啥", "内容"))


def current_sticker_question_reply(user_text: str, payload: dict[str, Any]) -> str:
    if not is_recent_sticker_question(user_text):
        return ""
    metadata = payload.get("metadata") if isinstance(payload, dict) else {}
    if not isinstance(metadata, dict):
        return ""
    if as_bool(metadata.get("recent_sticker_unavailable"), default=False):
        return "你刚发的是一张表情包。但这次 QQ 只给了动画表情占位，我没抓到具体画面。"
    if not (
        as_bool(metadata.get("recent_sticker_question"), default=False)
        or as_bool(metadata.get("sticker_import_completed"), default=False)
    ):
        return ""
    if not as_bool(metadata.get("sticker_import_completed"), default=False):
        return ""
    label = safe_str(metadata.get("sticker_mood_label") or metadata.get("sticker_mood")).strip()
    confidence = safe_str(metadata.get("sticker_confidence")).strip()
    image_context = metadata.get("qq_image_context")
    image_context = image_context if isinstance(image_context, dict) else {}
    meaning = safe_str(image_context.get("meaning")).strip()
    if label:
        reply = f"你刚发的是偏{label}的表情包。"
    else:
        reply = "你刚发的是一张表情包。"
    if meaning:
        reply += f"看起来是{meaning}。"
    if confidence.lower() in {"low", "低", "unclear"}:
        reply += "不过这个判断不太稳。"
    return reply


def recent_sticker_question_reply(user_text: str, dialogue_tail: list[dict[str, str]]) -> str:
    if not is_recent_sticker_question(user_text):
        return ""
    for item in reversed(dialogue_tail[-12:]):
        content = safe_str(item.get("content"))
        marker = "【收到的表情记录】"
        if marker not in content:
            continue
        detail = content.split(marker, 1)[1]
        label = ""
        meaning = ""
        confidence = ""
        for key, assign in (("label", "分类="), ("meaning", "语义="), ("confidence", "置信度=")):
            match = re.search(re.escape(assign) + r"([^；\n]+)", detail)
            if not match:
                continue
            if key == "label":
                label = match.group(1).strip()
            elif key == "meaning":
                meaning = match.group(1).strip()
            else:
                confidence = match.group(1).strip()
        if label:
            reply = f"你刚发的是偏{label}的表情包。"
        else:
            reply = "你刚发的是一张表情包。"
        if meaning:
            reply += f"看起来是{meaning}。"
        if confidence and confidence.lower() in {"low", "低", "unclear"}:
            reply += "不过这个判断不太稳。"
        return reply
    return ""
