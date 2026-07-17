from __future__ import annotations

from xinyu_proactive_motivation import evaluate_proactive_motivation
from xinyu_silence_reasons import EMPTY_CONCRETE, OWNER_LONG_IDLE_SILENT


def test_owner_long_idle_empty_never_speaks() -> None:
    d = evaluate_proactive_motivation(
        source="owner_long_idle",
        concrete_question="",
        relevance=5,
        urgency=5,
    )
    assert d.speak is False
    assert d.reason == OWNER_LONG_IDLE_SILENT


def test_empty_concrete_blocks() -> None:
    d = evaluate_proactive_motivation(
        source="task",
        concrete_question="",
        relevance=5,
    )
    assert d.speak is False
    assert d.reason == EMPTY_CONCRETE


def test_high_score_with_concrete_speaks() -> None:
    d = evaluate_proactive_motivation(
        source="task",
        concrete_question="构建失败了，要不要看日志？",
        has_finding=True,
        relevance=5,
        info_gap=4,
        expected_impact=4,
    )
    assert d.speak is True
