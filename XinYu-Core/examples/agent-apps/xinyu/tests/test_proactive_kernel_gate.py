from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_proactive_kernel_gate import read_proactive_kernel_gate  # noqa: E402
from xinyu_proactivity_scorer import (  # noqa: E402
    ProactiveCandidate,
    build_proactive_gate_context,
    decide_proactive_candidate,
    run_proactivity_scorer_shadow,
    score_proactive_candidate,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _task_done_candidate(checked_at: str) -> ProactiveCandidate:
    return ProactiveCandidate(
        candidate_id="proshadow-test-task-done",
        source_type="task_done",
        source_ref="runtime_program_awareness:codex_delegate",
        intent_type="report_completion",
        owner_visible_text="A delegated task finished.",
        content_preview="status=finished",
        utility_hint="owner delegated task finished",
        emotional_weight=10,
        novelty_hint="finished",
        confidence=82,
        risk_flags=(),
        created_at=checked_at,
        expires_at="2026-06-30T23:59:59+08:00",
    )


def test_read_proactive_kernel_gate_review_pressure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_signals(root: Path) -> dict:
        return {
            "available": True,
            "pending_review_count": 4,
            "structural_impact_recent": False,
            "slow_signal_count": 1,
            "kernel_pressure": True,
        }

    monkeypatch.setattr("xinyu_proactive_kernel_gate.read_kernel_pressure_signals", fake_signals)
    gate = read_proactive_kernel_gate(Path("/tmp/unused"))
    assert gate["emergence_level"] == "kernel_review_pressure"
    assert gate["hold_non_urgent"] is True
    assert gate["score_penalty"] >= 14
    assert gate["send_threshold_boost"] >= 12


def test_kernel_pressure_downgrades_task_done_from_send_now(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked_at = "2026-06-30T12:00:00+08:00"

    def quiet_gate(root: Path) -> dict:
        return {
            "available": True,
            "emergence_level": "quiet",
            "score_penalty": 0,
            "interruption_bonus": 0,
            "inbox_threshold_boost": 0,
            "send_threshold_boost": 0,
            "hold_non_urgent": False,
            "pending_review_count": 0,
            "structural_impact_recent": False,
            "kernel_pressure": False,
            "slow_signal_count": 0,
        }

    def pressured_gate(root: Path) -> dict:
        return {
            "available": True,
            "emergence_level": "kernel_review_pressure",
            "score_penalty": 20,
            "interruption_bonus": 10,
            "inbox_threshold_boost": 6,
            "send_threshold_boost": 12,
            "hold_non_urgent": True,
            "pending_review_count": 4,
            "structural_impact_recent": False,
            "kernel_pressure": True,
            "slow_signal_count": 1,
        }

    candidate = _task_done_candidate(checked_at)
    baseline_context = {"kernel_gate": quiet_gate(tmp_path)}
    pressured_context = {"kernel_gate": pressured_gate(tmp_path)}

    baseline_score = score_proactive_candidate(
        candidate,
        checked_at=checked_at,
        gate_context=baseline_context,
    )
    pressured_score = score_proactive_candidate(
        candidate,
        checked_at=checked_at,
        gate_context=pressured_context,
    )
    baseline_decision = decide_proactive_candidate(
        candidate,
        baseline_score,
        checked_at=checked_at,
        gate_context=baseline_context,
    )
    pressured_decision = decide_proactive_candidate(
        candidate,
        pressured_score,
        checked_at=checked_at,
        gate_context=pressured_context,
    )

    assert baseline_decision.recommendation == "send_now"
    assert pressured_decision.recommendation in {"hold", "inbox", "drop"}
    assert "kernel_review_pressure_hold" in pressured_decision.hard_blocks
    assert "kernel_score_penalty" in pressured_score.reasons_negative
    assert pressured_score.interruption_cost > baseline_score.interruption_cost


def test_shadow_scorer_uses_kernel_gate_from_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(
        tmp_path / "memory/context/runtime_program_awareness.md",
        "- codex_delegate: status=finished owner=ok\n",
    )
    _write(
        tmp_path / "memory/context/proactive_decision_context.md",
        "- owner_recent_private_minutes: 120\n- desktop_active: false\n",
    )

    def pressured_gate(root: Path) -> dict:
        return {
            "available": True,
            "emergence_level": "kernel_structural_pressure",
            "score_penalty": 18,
            "interruption_bonus": 12,
            "inbox_threshold_boost": 8,
            "send_threshold_boost": 18,
            "hold_non_urgent": True,
            "pending_review_count": 2,
            "structural_impact_recent": True,
            "kernel_pressure": True,
            "slow_signal_count": 0,
        }

    monkeypatch.setattr("xinyu_proactivity_scorer.read_proactive_kernel_gate", pressured_gate)

    result = run_proactivity_scorer_shadow(tmp_path, checked_at="2026-06-30T12:00:00+08:00")
    assert result["source_type"] == "task_done"
    assert result["recommendation"] in {"hold", "inbox", "drop"}
    assert "kernel_review_pressure_hold" in result["hard_blocks"]


def test_build_proactive_gate_context_merges_kernel_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(tmp_path / "memory/context/proactive_decision_context.md", "- owner_recent_private_minutes: 30\n")

    def fake_gate(root: Path) -> dict:
        return {
            "available": True,
            "emergence_level": "kernel_slow_signal_pressure",
            "score_penalty": 8,
            "interruption_bonus": 4,
            "inbox_threshold_boost": 4,
            "send_threshold_boost": 8,
            "hold_non_urgent": False,
            "pending_review_count": 0,
            "structural_impact_recent": False,
            "kernel_pressure": True,
            "slow_signal_count": 3,
        }

    monkeypatch.setattr("xinyu_proactivity_scorer.read_proactive_kernel_gate", fake_gate)
    context = build_proactive_gate_context(tmp_path, checked_at="2026-06-30T12:00:00+08:00")
    assert context["kernel_emergence_level"] == "kernel_slow_signal_pressure"
    assert context["kernel_gate"]["slow_signal_count"] == 3