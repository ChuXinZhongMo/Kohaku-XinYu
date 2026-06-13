from __future__ import annotations

from collections.abc import Callable


SEMANTIC_FAST_ALLOWED_INTENTS = frozenset(
    {"greeting", "ack", "reply_quality_complaint", "runtime_status_question", "owner_state_question"}
)

_REPLY_QUALITY_COMPLAINT_MARKERS = (
    "\u4f60\u5728\u8bf4\u4ec0\u4e48",
    "\u7b54\u975e\u6240\u95ee",
    "\u4ec0\u4e48\u60c5\u51b5",
    "\u6ca1\u53cd\u5e94",
    "\u4e0d\u56de\u8bdd",
    "\u4e0d\u56de\u6d88\u606f",
    "\u600e\u4e48\u8fd9\u4e48\u4e45",
    "\u8fd9\u4e48\u4e45\u624d\u56de",
    "\u524d\u53f0\u6b63\u5728\u56de\u590d",
    "\u6b63\u5728\u56de\u590d",
    "\u6ca1\u6709\u7136\u540e",
    "\u6839\u672c\u6ca1\u56de",
    "\u6ca1\u56de\u6211",
    "\u5957\u6a21\u677f",
    "\u592a\u6a21\u677f",
    "\u8bdd\u672f\u6a21\u677f",
    "\u8d8a\u6539\u8d8a\u51fa\u95ee\u9898",
    "\u4f60\u5728\u5e72\u561b",
    "what are you talking about",
    "why so slow",
)
_RUNTIME_STATUS_MARKERS = (
    "\u540e\u53f0\u5728\u8dd1",
    "\u540e\u53f0\u8dd1",
    "\u5728\u8dd1\u4ec0\u4e48",
    "\u8dd1\u4ec0\u4e48\u4e1c\u897f",
    "\u8fd0\u884c\u72b6\u6001",
    "core \u72b6\u6001",
    "core\u72b6\u6001",
    "qq \u72b6\u6001",
    "qq\u72b6\u6001",
    "napcat \u72b6\u6001",
    "napcat\u72b6\u6001",
    "\u67e5\u4e00\u4e0b\u72b6\u6001",
    "/status",
    "what is running",
)
_OWNER_STATE_QUESTION_MARKERS = (
    "\u8fd8\u597d\u5417",
    "\u8fd8\u597d\u4e48",
    "\u8fd8\u597d\u561b",
    "\u4f60\u600e\u4e48\u6837",
    "\u4f60\u73b0\u5728\u600e\u4e48\u6837",
    "\u73b0\u5728\u600e\u4e48\u6837",
    "\u611f\u89c9\u600e\u4e48\u6837",
    "\u611f\u89c9\u5982\u4f55",
    "\u5fc3\u60c5\u600e\u4e48\u6837",
    "\u72b6\u6001\u600e\u4e48\u6837",
    "\u72b6\u6001\u5982\u4f55",
    "\u4ec0\u4e48\u72b6\u6001",
    "\u4f60\u73b0\u5728\u4ec0\u4e48\u72b6\u6001",
)
_OWNER_STATE_FAST_MAX_CHARS = 24
_CONFUSION_ONLY_MARKERS = ("??", "???", "????", "\uff1f\uff1f", "\uff1f\uff1f\uff1f", "\uff1f\uff1f\uff1f\uff1f")
_STALE_PLAN_REPLY_MARKERS = (
    "\u5148\u628a\u8303\u56f4\u538b\u5c0f",
    "\u672c\u5730\u53ef\u8fd0\u884c",
    "\u53ef\u56de\u6eda",
    "\u6700\u5c0f\u53ef\u8fd0\u884c",
    "\u4e3b\u94fe\u8def",
    "shadow",
)


def _compact_text(text: str) -> str:
    return "".join(text.split())


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _repair_intents_for_text(
    text: str,
    *,
    compact_text_func: Callable[[str], str] = _compact_text,
    contains_any_func: Callable[[str, tuple[str, ...]], bool] = _contains_any,
    runtime_status_markers: tuple[str, ...] = _RUNTIME_STATUS_MARKERS,
    reply_quality_complaint_markers: tuple[str, ...] = _REPLY_QUALITY_COMPLAINT_MARKERS,
    confusion_only_markers: tuple[str, ...] = _CONFUSION_ONLY_MARKERS,
) -> tuple[str, ...]:
    compact = compact_text_func(text)
    if not compact:
        return ()
    intents: list[str] = []
    if contains_any_func(compact, runtime_status_markers):
        intents.append("runtime_status_question")
    if contains_any_func(compact, reply_quality_complaint_markers) or compact in confusion_only_markers:
        intents.append("reply_quality_complaint")
    return tuple(intents)


def _looks_like_owner_state_question(
    text: str,
    *,
    compact_text_func: Callable[[str], str] = _compact_text,
    owner_state_question_markers: tuple[str, ...] = _OWNER_STATE_QUESTION_MARKERS,
) -> bool:
    compact = compact_text_func(text)
    if not compact:
        return False
    return any(marker in compact for marker in owner_state_question_markers)
