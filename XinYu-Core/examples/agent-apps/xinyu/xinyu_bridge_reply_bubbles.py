from __future__ import annotations

import re

from xinyu_bridge_values import safe_str


def owner_requested_reply_bubble_units(
    *,
    user_text: str,
    reply: str,
    dialogue_tail: list[dict[str, str]],
) -> list[str]:
    compact = re.sub(r"\s+", "", safe_str(user_text)).lower()
    if not compact:
        return []
    split_markers = (
        "每个数字单独发",
        "每个数字单独发出来",
        "每一个数字单独发",
        "一个数字一条",
        "每个数一条",
        "每个字单独发",
        "一个字一条",
        "一条一条发",
        "逐条发",
        "分开发",
        "拆开发",
        "拆成十句",
        "拆成十条",
    )
    if not any(marker in compact for marker in split_markers):
        return []

    ranged = re.search(r"从\s*(\d{1,3})\s*(?:数)?到\s*(\d{1,3})", safe_str(user_text))
    if ranged:
        start = int(ranged.group(1))
        end = int(ranged.group(2))
        step = 1 if end >= start else -1
        count = abs(end - start) + 1
        if 2 <= count <= 20:
            return [str(value) for value in range(start, end + step, step)]

    for candidate in (
        safe_str(reply),
        *(safe_str(item.get("content")) for item in reversed(dialogue_tail[-12:]) if item.get("role") == "assistant"),
    ):
        units = numeric_bubble_units_from_text(candidate)
        if units:
            return units
    return []


def numeric_bubble_units_from_text(text: str) -> list[str]:
    clean = safe_str(text).strip()
    if not clean:
        return []
    numbers = re.findall(r"\d{1,3}", clean)
    if not (2 <= len(numbers) <= 20):
        return []
    residue = re.sub(r"\d{1,3}", "", clean)
    if re.sub(r"[\s,，、.。;；:：\-—]+", "", residue):
        return []
    values = [int(item) for item in numbers]
    if values != list(range(values[0], values[0] + len(values))):
        return []
    return numbers


def looks_like_false_single_bubble_limitation(user_text: str, reply: str) -> bool:
    user_compact = re.sub(r"\s+", "", safe_str(user_text)).lower()
    reply_compact = re.sub(r"\s+", "", safe_str(reply)).lower()
    if not user_compact or not reply_compact:
        return False
    wants_split = any(
        marker in user_compact
        for marker in (
            "单独发",
            "分开发",
            "拆开发",
            "一条一条发",
            "逐条发",
            "一个数字一条",
            "每个数字",
        )
    )
    if not wants_split:
        return False
    false_limits = (
        "一次只能发一条",
        "只能发一条",
        "没法拆成",
        "不能拆成",
        "没办法拆成",
        "发不了十句",
        "发不了这么多",
    )
    return any(marker in reply_compact for marker in false_limits)
