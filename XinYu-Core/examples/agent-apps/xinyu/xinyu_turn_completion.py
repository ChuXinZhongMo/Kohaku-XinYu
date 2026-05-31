from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


STATE_COLLECTING_SEGMENTS = "COLLECTING_SEGMENTS"
STATE_WAITING_THOUGHT = "WAITING_THOUGHT"
STATE_READY_TO_REPLY = "READY_TO_REPLY"


@dataclass(frozen=True)
class TurnCompletionDecision:
    state: str
    wait_seconds: float
    reason: str
    should_generate: bool
    notes: tuple[str, ...] = ()


_TRIM_CHARS = " \t\r\n,.;:!?~`'\"()[]{}<>\u3002\uff0c\uff01\uff1f\uff1b\uff1a\u3001\u2026\u2014-"


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip(_TRIM_CHARS).lower()


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = str(text or "").lower()
    return any(marker and marker in lowered for marker in markers)


def _starts_or_equals_any(text: str, markers: tuple[str, ...]) -> bool:
    compact = _compact(text)
    return any(compact == marker or compact.startswith(marker) for marker in markers)


def _ends_any(text: str, suffixes: tuple[str, ...]) -> bool:
    stripped = str(text or "").strip()
    return any(stripped.endswith(suffix) for suffix in suffixes)


def _clean_fragments(fragments: Iterable[str]) -> list[str]:
    return [str(fragment or "").strip() for fragment in fragments if str(fragment or "").strip()]


_HOLD_MARKERS = (
    "\u7b49\u4e0b",
    "\u7b49\u4e00\u4e0b",
    "\u7b49\u4f1a",
    "\u7b49\u7b49",
    "\u5148\u522b\u56de",
    "\u522b\u56de",
    "\u5148\u522b\u52a8",
    "\u6211\u60f3\u60f3",
    "\u518d\u60f3\u60f3",
    "\u7b49\u6211\u60f3\u60f3",
    "\u60f3\u60f3\u529e\u6cd5",
    "\u5148\u60f3\u60f3",
    "\u6211\u770b\u770b",
    "\u6211\u7ec4\u7ec7\u4e0b",
    "\u6211\u7ec4\u7ec7\u4e00\u4e0b",
    "\u6211\u6253\u5b57",
    "hold on",
    "wait",
)

_LOW_INFO_EXACT = (
    "\u55ef",
    "\u55ef\u55ef",
    "\u54e6",
    "\u597d",
    "\u597d\u7684",
    "\u5bf9",
    "\u5bf9\u7684",
    "\u884c",
    "\u53ef\u4ee5",
    "\u77e5\u9053\u4e86",
)

_CONTINUATION_PREFIXES = (
    "\u4e0d\u662f",
    "\u4e0d\u5bf9",
    "\u6211\u610f\u601d\u662f",
    "\u6211\u7684\u610f\u601d\u662f",
    "\u6211\u662f\u8bf4",
    "\u5c31\u662f",
    "\u7136\u540e",
    "\u8fd8\u6709",
    "\u53e6\u5916",
    "\u800c\u4e14",
    "\u4f46\u662f",
    "\u4e0d\u8fc7",
    "\u56e0\u4e3a",
    "\u63a5\u7740",
)

_CONTINUATION_SUFFIXES = (
    ",",
    "\uff0c",
    "\u3001",
    "...",
    "\u2026",
    "\u2026\u2026",
)

_HANDOFF_MARKERS = (
    "\u4f60\u8bf4\u5427",
    "\u4f60\u8bf4",
    "\u600e\u4e48\u770b",
    "\u600e\u4e48\u60f3",
    "\u4f60\u6765",
    "\u73b0\u5728\u56de",
    "\u53ef\u4ee5\u56de",
    "\u56de\u5427",
    "\u6765\u5427",
    "\u6309\u4f60\u7684\u63a8\u8350",
    "\u5f00\u59cb\u505a",
    "\u5f00\u59cb\u5427",
    "\u5c31\u8fd9\u6837",
)

_TASK_MARKERS = (
    "\u5e2e\u6211",
    "\u4fee\u590d",
    "\u4fee\u4e00\u4e0b",
    "\u6539",
    "\u6539\u8fc7\u53bb",
    "\u6dfb\u52a0",
    "\u52a0\u4e2a",
    "\u5b9e\u73b0",
    "\u5199",
    "\u6574\u5408",
    "\u6574\u7406",
    "\u770b\u770b",
    "\u68c0\u67e5",
    "\u6d4b\u8bd5",
    "\u8dd1",
    "\u8fd0\u884c",
    "\u542f\u52a8",
    "\u7ee7\u7eed",
    "\u5220",
    "\u66ff\u6362",
    "\u63a5\u5165",
    "\u63a5\u4e0a",
    "fix",
    "run",
    "test",
)

_HARD_TASK_MARKERS = tuple(marker for marker in _TASK_MARKERS if marker != "\u770b\u770b")

_QUESTION_MARKERS = (
    "?",
    "\uff1f",
    "\u4ec0\u4e48",
    "\u4e3a\u4ec0\u4e48",
    "\u600e\u4e48",
    "\u80fd\u4e0d\u80fd",
    "\u662f\u4e0d\u662f",
    "\u6709\u6ca1\u6709",
    "\u5982\u4f55",
    "\u54ea",
    "\u5417",
    "\u5462",
)


def evaluate_turn_completion(
    fragments: Iterable[str],
    *,
    base_wait_seconds: float = 2.0,
    max_fragments: int = 8,
) -> TurnCompletionDecision:
    """Return a deterministic wait policy for human segmented input."""
    clean = _clean_fragments(fragments)
    base_wait = max(0.0, float(base_wait_seconds or 0.0))
    quick_wait = max(base_wait, 3.0)
    if not clean:
        return TurnCompletionDecision(
            state=STATE_WAITING_THOUGHT,
            wait_seconds=base_wait,
            reason="empty_turn",
            should_generate=False,
            notes=("empty_turn",),
        )

    last = clean[-1]
    combined = "\n".join(clean)
    compact_last = _compact(last)
    compact_combined = _compact(combined)
    notes: list[str] = [f"fragment_count:{len(clean)}"]

    has_handoff = _contains_any(combined, _HANDOFF_MARKERS)
    has_task = _contains_any(combined, _TASK_MARKERS)
    has_question = _contains_any(combined, _QUESTION_MARKERS)
    has_hold = _contains_any(last, _HOLD_MARKERS)
    has_continuation = _starts_or_equals_any(last, _CONTINUATION_PREFIXES) or _ends_any(last, _CONTINUATION_SUFFIXES)

    if len(clean) >= max(2, int(max_fragments or 8)):
        return TurnCompletionDecision(
            state=STATE_READY_TO_REPLY,
            wait_seconds=quick_wait,
            reason="max_fragments",
            should_generate=True,
            notes=tuple(notes + ["max_fragments"]),
        )

    if has_handoff:
        return TurnCompletionDecision(
            state=STATE_READY_TO_REPLY,
            wait_seconds=quick_wait,
            reason="handoff_marker",
            should_generate=True,
            notes=tuple(notes + ["handoff_marker"]),
        )

    if has_hold and not _contains_any(combined, _HARD_TASK_MARKERS) and not has_question:
        return TurnCompletionDecision(
            state=STATE_WAITING_THOUGHT,
            wait_seconds=max(base_wait, 90.0),
            reason="explicit_hold",
            should_generate=False,
            notes=tuple(notes + ["explicit_hold"]),
        )

    if has_task or has_question:
        return TurnCompletionDecision(
            state=STATE_READY_TO_REPLY,
            wait_seconds=quick_wait,
            reason="complete_request",
            should_generate=True,
            notes=tuple(notes + ["complete_request"]),
        )

    if has_hold:
        return TurnCompletionDecision(
            state=STATE_WAITING_THOUGHT,
            wait_seconds=max(base_wait, 90.0),
            reason="explicit_hold",
            should_generate=False,
            notes=tuple(notes + ["explicit_hold"]),
        )

    if len(clean) == 1 and compact_last in _LOW_INFO_EXACT:
        return TurnCompletionDecision(
            state=STATE_WAITING_THOUGHT,
            wait_seconds=max(base_wait, 12.0),
            reason="low_info_ack",
            should_generate=False,
            notes=tuple(notes + ["low_info_ack"]),
        )

    if has_continuation:
        should_generate = len(compact_combined) > 8
        return TurnCompletionDecision(
            state=STATE_COLLECTING_SEGMENTS,
            wait_seconds=max(base_wait, 25.0),
            reason="continuation_marker",
            should_generate=should_generate,
            notes=tuple(notes + ["continuation_marker"]),
        )

    if len(compact_last) <= 12:
        return TurnCompletionDecision(
            state=STATE_COLLECTING_SEGMENTS,
            wait_seconds=max(base_wait, 15.0),
            reason="short_fragment",
            should_generate=True,
            notes=tuple(notes + ["short_fragment"]),
        )

    return TurnCompletionDecision(
        state=STATE_COLLECTING_SEGMENTS,
        wait_seconds=max(base_wait, 8.0),
        reason="ordinary_pause",
        should_generate=True,
        notes=tuple(notes + ["ordinary_pause"]),
    )
