from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_semantic_fast_text_extract import _compact_text
from xinyu_bridge_semantic_fast_text_extract import _contains_any
from xinyu_bridge_semantic_fast_text_extract import _looks_like_owner_state_question
from xinyu_bridge_semantic_fast_text_extract import _repair_intents_for_text
from xinyu_bridge_semantic_fast_text_extract import _STALE_PLAN_REPLY_MARKERS


def owner_private_empty_state_notice(
    text: str,
    *,
    seed: str = "",
    compact_text_func: Callable[[str], str] = _compact_text,
    owner_state_question_func: Callable[[str], bool] = _looks_like_owner_state_question,
) -> str:
    del seed
    compact = compact_text_func(text)
    if not compact:
        return "我在。"
    if any(marker in compact for marker in ("别追问", "别安慰", "别一大段", "不吵")):
        return "嗯，我收住。"
    if any(marker in compact for marker in ("早睡", "早点睡", "休息")):
        return "嗯，我收住。你也早点睡。"
    if any(marker in compact for marker in ("困", "睡", "累", "没精神")):
        return "嗯，先不硬聊了。"
    if owner_state_question_func(text):
        return "还在。刚才那一下没接上。"
    if len(compact) <= 8:
        return "嗯，我在。"
    return "我在。刚才那句没接上。"


def empty_visible_reply_fallback_impl(
    runtime: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    delegate_note: str = "",
    empty_state_notice_func: Callable[..., str] = owner_private_empty_state_notice,
) -> str:
    del delegate_note
    if not runtime._owner_private_payload_matches(payload):
        return ""
    return empty_state_notice_func(user_text)


def owner_private_direct_repair_reply_impl(
    runtime: Any,
    text: str,
    intents: tuple[str, ...] | None = None,
    *,
    repair_intents_func: Callable[[str], tuple[str, ...]] = _repair_intents_for_text,
    ordinary_repair_reply_func: Callable[[str], str] | None = None,
    compact_text_func: Callable[[str], str] = _compact_text,
    contains_any_func: Callable[[str, tuple[str, ...]], bool] = _contains_any,
) -> str:
    del runtime
    ordinary_repair_reply_func = ordinary_repair_reply_func or _ordinary_private_repair_reply
    detected = tuple(intents or repair_intents_func(text))
    if "runtime_status_question" in detected:
        return (
            "\u540e\u53f0\u5728\u5904\u7406\u5f53\u524d\u8fd9\u6761\u79c1\u804a\uff1b"
            "\u521a\u624d\u6162\u662f core \u8d70\u4e86\u6162\u94fe\u8def\uff0c"
            "\u4e0d\u662f QQ \u6ca1\u6536\u5230\u3002"
        )
    if "reply_quality_complaint" in detected:
        if contains_any_func(
            compact_text_func(text),
            ("\u600e\u4e48\u8fd9\u4e48\u4e45", "\u8fd9\u4e48\u4e45\u624d\u56de", "why so slow"),
        ):
            return (
                "\u4e0d\u662f\u6ca1\u6536\u5230\uff0c"
                "\u662f\u521a\u624d\u90a3\u8f6e\u8fdb\u4e86\u6162\u94fe\u8def\uff1b"
                "\u8fd9\u53e5\u6211\u5148\u6309\u4f60\u5f53\u524d\u95ee\u9898\u56de\u3002"
            )
        return (
            "\u521a\u624d\u90a3\u53e5\u63a5\u9519\u4e86\uff0c"
            "\u662f\u65e7\u4e0a\u4e0b\u6587\u4e32\u8fdb\u6765\u4e86\uff1b"
            "\u8fd9\u53e5\u6211\u6309\u4f60\u5f53\u524d\u95ee\u9898\u6765\u3002"
        )
    return ordinary_repair_reply_func(text)


def _ordinary_private_repair_reply(
    text: str,
    *,
    compact_text_func: Callable[[str], str] = _compact_text,
) -> str:
    compact = compact_text_func(text)
    if not compact:
        return "\u6211\u5728\u3002"
    if any(marker in compact for marker in ("\u4e0d\u5435", "\u65e9\u70b9\u7761", "\u65e9\u7761", "\u4f11\u606f")):
        return "\u55ef\uff0c\u6211\u6536\u4f4f\u3002\u4f60\u4e5f\u65e9\u70b9\u7761\u3002"
    if any(marker in compact for marker in ("\u51cc\u6668", "\u592a\u665a", "\u5f88\u665a")):
        return "\u55ef\uff0c\u592a\u665a\u4e86\u3002\u4f60\u5148\u7761\u3002"
    if any(marker in compact for marker in ("\u56f0", "\u7761", "\u7d2f", "\u6ca1\u7cbe\u795e")):
        if "?" in text or "\uff1f" in text:
            return "\u6709\u70b9\u3002\u4f60\u4e5f\u65e9\u70b9\u7761\u3002"
        return "\u55ef\uff0c\u5148\u4e0d\u786c\u804a\u4e86\u3002"
    if "?" in text or "\uff1f" in text:
        return "\u8fd9\u53e5\u6211\u521a\u624d\u63a5\u9519\u4e86\u3002\u4f60\u518d\u95ee\u4e00\u904d\uff0c\u6211\u6309\u73b0\u5728\u8fd9\u53e5\u6765\u3002"
    if len(compact) <= 8:
        return "\u55ef\uff0c\u6211\u5728\u3002"
    return "\u8fd9\u53e5\u6211\u521a\u624d\u4e32\u5230\u65e7\u8bed\u5883\u4e86\u3002\u6211\u5148\u6536\u56de\u6765\u3002"


def reply_looks_like_stale_plan_residue(
    reply: str,
    *,
    compact_text_func: Callable[[str], str] = _compact_text,
    stale_plan_reply_markers: tuple[str, ...] = _STALE_PLAN_REPLY_MARKERS,
) -> bool:
    compact = compact_text_func(reply)
    if not compact:
        return False
    hits = sum(1 for marker in stale_plan_reply_markers if marker.lower() in compact.lower())
    return hits >= 2


def _direct_greeting_ack_reply(
    text: str,
    intents: tuple[str, ...],
    *,
    compact_text_func: Callable[[str], str] = _compact_text,
) -> str:
    compact = compact_text_func(text)
    lowered = compact.lower()
    if any(marker in compact for marker in ("\u4e2d\u5348\u597d",)):
        return "\u4e2d\u5348\u597d\u3002"
    if any(marker in compact for marker in ("\u4e0b\u5348\u597d",)):
        return "\u4e0b\u5348\u597d\u3002"
    if any(marker in compact for marker in ("\u665a\u4e0a\u597d",)):
        return "\u665a\u4e0a\u597d\u3002"
    if any(marker in compact for marker in ("\u65e9\u4e0a\u597d", "\u65e9\u5b89", "\u65e9")):
        return "\u65e9\u3002"
    if any(marker in compact for marker in ("\u665a\u5b89",)):
        return "\u665a\u5b89\u3002"
    if any(marker in compact for marker in ("\u4f60\u597d", "\u5728\u5417")) or lowered in {"hi", "hello", "hey"}:
        return "\u5728\u3002"
    if "greeting" in intents:
        return "\u5728\u3002"
    return "\u55ef\u3002"
