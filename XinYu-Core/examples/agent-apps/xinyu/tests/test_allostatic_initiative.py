from __future__ import annotations

from datetime import datetime, timedelta, timezone

from xinyu_allostatic_initiative import (
    compute_predicted_deviation,
    compute_satiety,
    evaluate_allostatic_signals,
)
from xinyu_proactive_motivation import evaluate_proactive_motivation
from xinyu_silence_reasons import OWNER_LONG_IDLE_SILENT


def test_satiety_decays() -> None:
    now = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
    recent = (now - timedelta(minutes=10)).isoformat()
    old = (now - timedelta(hours=3)).isoformat()
    assert compute_satiety(last_success_at=recent, satiety_minutes=45, now=now) > 0.5
    assert compute_satiety(last_success_at=old, satiety_minutes=45, now=now) == 0.0


def test_predicted_deviation_higher_with_finding() -> None:
    low = compute_predicted_deviation(hours_since_owner=1, has_finding=False)
    high = compute_predicted_deviation(
        hours_since_owner=20, has_finding=True, concrete_pending=True
    )
    assert high > low


def test_idle_low_deviation_silences_via_motivation() -> None:
    d = evaluate_proactive_motivation(
        source="owner_long_idle",
        concrete_question="随便问问在吗",
        has_finding=True,
        relevance=5,
        urgency=5,
        hours_since_owner=0.5,
        open_threads=0,
        last_success_at=datetime.now().astimezone().isoformat(),
        satiety_minutes=60,
    )
    assert d.speak is False
    assert d.allostatic is not None


def test_idle_empty_still_silent() -> None:
    d = evaluate_proactive_motivation(
        source="owner_long_idle",
        concrete_question="",
        relevance=5,
        hours_since_owner=48,
        has_finding=False,
    )
    assert d.speak is False
    assert d.reason == OWNER_LONG_IDLE_SILENT


def test_task_with_finding_can_speak_without_allostatic_inputs() -> None:
    # Backward compatible path: no allostatic kwargs → same as before.
    d = evaluate_proactive_motivation(
        source="task",
        concrete_question="构建失败了，要不要看日志？",
        has_finding=True,
        relevance=5,
        info_gap=4,
        expected_impact=4,
        use_allostatic=False,
    )
    assert d.speak is True


def test_signals_pe_urgency_shape() -> None:
    s = evaluate_allostatic_signals(
        source="task",
        has_finding=True,
        concrete_question="有具体 finding",
        hours_since_owner=12,
        last_outcome_ok=False,
        repeated_failure_count=2,
    )
    assert s.pe_stress >= 0.55
    assert 0.0 <= s.stick_deficit <= 1.0
