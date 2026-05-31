from __future__ import annotations

import re
from typing import Any


REFERENCE_MARKERS = (
    "这几句",
    "这两句",
    "这一句",
    "刚才",
    "刚刚",
    "刚说",
    "上面",
    "前面",
    "后面说的",
)

RANGE_REFERENCE_RE = re.compile(r"从.{1,80}?到现在")

BAD_CLARIFY_PATTERNS = (
    re.compile(r"哪[一两几]句"),
    re.compile(r"哪[一两几]段"),
    re.compile(r"告诉我听听"),
    re.compile(r"具体是哪"),
)

CRITIQUE_MARKERS = (
    "不太行",
    "不对",
    "不太对",
    "不自然",
    "退回去",
    "退步",
    "接待腔",
    "怪",
    "生硬",
    "别这样",
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(text: str, *, limit: int = 48) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "..."


def _has_current_reference(text: str) -> bool:
    return any(marker in text for marker in REFERENCE_MARKERS) or bool(RANGE_REFERENCE_RE.search(text))


def _looks_like_bad_clarification(reply: str) -> bool:
    clean = _safe_str(reply)
    return any(pattern.search(clean) for pattern in BAD_CLARIFY_PATTERNS)


def _looks_like_current_reference_feedback(user_text: str) -> bool:
    clean = _safe_str(user_text)
    if not _has_current_reference(clean):
        return False
    if any(marker in clean for marker in CRITIQUE_MARKERS):
        return True
    return any(marker in clean for marker in ("再加", "除了", "都", "这些"))


def recent_assistant_lines(dialogue_tail: list[dict[str, str]], *, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for item in reversed(dialogue_tail):
        if not isinstance(item, dict) or _safe_str(item.get("role")).strip() != "assistant":
            continue
        content = _safe_str(item.get("content")).strip()
        if content:
            lines.append(content)
        if len(lines) >= max(1, int(limit)):
            break
    return list(reversed(lines))


def repair_current_reference_reply(
    *,
    user_text: str,
    reply: str,
    dialogue_tail: list[dict[str, str]],
) -> dict[str, Any]:
    if not _looks_like_current_reference_feedback(user_text):
        return {"changed": False, "reply": reply, "notes": ["no_current_reference_feedback"]}
    if not _looks_like_bad_clarification(reply):
        return {"changed": False, "reply": reply, "notes": ["reply_not_bad_clarification"]}
    lines = recent_assistant_lines(dialogue_tail, limit=3)
    if not lines:
        return {"changed": False, "reply": reply, "notes": ["no_recent_assistant_lines"]}

    if any(marker in user_text for marker in CRITIQUE_MARKERS):
        first = _compact(lines[0])
        last = _compact(lines[-1])
        if len(lines) == 1:
            repaired = f"明白，是我刚才那句“{first}”不对。我记下，不让你再重复指出。"
        else:
            repaired = f"明白，是我刚才从“{first}”到“{last}”这几句退回去了。我记下，不让你再重复指出。"
    else:
        repaired = "明白，你说的是刚才我自己说过的那几句。我先按这个反馈记下，不再反问你是哪一句。"
    return {
        "changed": True,
        "reply": repaired,
        "notes": ["current_reference_clarification_repaired"],
        "resolved_assistant_lines": lines,
    }
