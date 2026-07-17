from __future__ import annotations

import json
from pathlib import Path

from xinyu_nine_score import (
    OVERALL_CAP_ON_GATE_FAIL,
    agent_safe_scorecard_view,
    apply_offline_reweight,
    compute_nine_score,
    count_empty_idle_sends,
    gates_pass,
    load_nine_score,
    measure_lean_prompt_chars,
    overall_capped_if_gates_fail,
    refresh_nine_scorecard,
    reweight_dimensions_by_hard_outcomes,
    write_nine_score,
)


def test_measure_lean_prompt_chars() -> None:
    assert measure_lean_prompt_chars("abc") == 3
    assert measure_lean_prompt_chars("") == 0


def test_empty_idle_blocked_with_empty_concrete_is_zero(tmp_path: Path) -> None:
    path = tmp_path / "memory" / "context" / "proactive_request_state.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "- source: owner_long_idle",
                "- focus_kind: owner_long_idle",
                "- status: blocked",
                "- concrete_question: ",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert count_empty_idle_sends(tmp_path) == 0


def test_empty_idle_sent_with_empty_concrete_counts(tmp_path: Path) -> None:
    path = tmp_path / "memory" / "context" / "proactive_request_state.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "- source: owner_long_idle",
                "- focus_kind: owner_long_idle",
                "- status: sent",
                "- concrete_question: ",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    assert count_empty_idle_sends(tmp_path) == 1


def test_gates_fail_cap_overall() -> None:
    scores = {f"D{i}_x": 10.0 for i in range(1, 10)}
    # rebuild with real keys
    scores = {
        "D1_oral": 10.0,
        "D2_memory": 10.0,
        "D3_proactive_restraint": 10.0,
        "D4_autonomy_loop": 10.0,
        "D5_live_stability": 10.0,
        "D6_modularity": 10.0,
        "D7_skills": 10.0,
        "D8_body_feedback": 10.0,
        "D9_ops_security": 10.0,
    }
    gates = {
        "fact_hit_rate_72h": 0.5,
        "empty_idle_sends": 0,
        "lean_prompt_p50_chars": 5000,
        "silence_explain_rate": 1.0,
        "future_effect_consumption_rate": 1.0,
        "private_chat_smoke_ok": True,
    }
    assert not gates_pass(gates)
    assert overall_capped_if_gates_fail(scores, gates) == OVERALL_CAP_ON_GATE_FAIL


def test_write_nine_score_roundtrip(tmp_path: Path) -> None:
    report = compute_nine_score(
        tmp_path,
        samples={
            "empty_idle_sends": 0,
            "lean_prompt_p50_chars": 4000,
            "fact_hit_rate_72h": 0.5,
            "silence_explain_rate": 0.0,
            "future_effect_consumption_rate": 0.0,
            "private_chat_smoke_ok": False,
        },
    )
    path = write_nine_score(tmp_path, report)
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert "scores" in data and "overall" in data["scores"]
    assert data["gates"]["empty_idle_sends"] == 0
    assert data["scores"]["overall"] <= OVERALL_CAP_ON_GATE_FAIL
    assert data.get("agent_blind") is True


def test_agent_safe_scorecard_strips_soft_scores() -> None:
    report = {
        "version": 1,
        "computed_at": "t",
        "scores": {"overall": 9.0, "D1_oral": 9.0},
        "gates": {
            "empty_idle_sends": 0,
            "silence_explain_rate": 1.0,
            "future_effect_consumption_rate": 1.0,
            "fact_hit_rate_72h": 0.9,
            "lean_prompt_p50_chars": 4000,
            "private_chat_smoke_ok": True,
        },
        "gates_pass": True,
    }
    safe = agent_safe_scorecard_view(report)
    assert safe["agent_blind"] is True
    assert safe["scores"] is None
    assert safe["gates"]["empty_idle_sends"] == 0
    assert "overall" not in (safe.get("scores") or {})


def test_outcome_reweight_differs_from_equal_on_healthy_gates() -> None:
    healthy = {
        "empty_idle_sends": 0,
        "silence_explain_rate": 1.0,
        "future_effect_consumption_rate": 1.0,
        "fact_hit_rate_72h": 0.95,
        "lean_prompt_p50_chars": 5000,
        "private_chat_smoke_ok": True,
    }
    unhealthy = {
        "empty_idle_sends": 2,
        "silence_explain_rate": 0.2,
        "future_effect_consumption_rate": 0.1,
        "fact_hit_rate_72h": 0.2,
        "lean_prompt_p50_chars": 20000,
        "private_chat_smoke_ok": False,
    }
    w_h = reweight_dimensions_by_hard_outcomes(hard_outcomes=healthy)
    w_u = reweight_dimensions_by_hard_outcomes(hard_outcomes=unhealthy)
    assert abs(sum(w_h.values()) - 1.0) < 1e-6
    assert w_h["D3_proactive_restraint"] > w_u["D3_proactive_restraint"]
    assert w_h["D2_memory"] > w_u["D2_memory"]


def test_apply_offline_reweight_persists(tmp_path: Path) -> None:
    weights = apply_offline_reweight(
        tmp_path,
        {
            "empty_idle_sends": 0,
            "silence_explain_rate": 1.0,
            "future_effect_consumption_rate": 0.9,
            "fact_hit_rate_72h": 0.95,
            "lean_prompt_p50_chars": 4000,
            "private_chat_smoke_ok": True,
        },
    )
    path = tmp_path / "runtime" / "quality" / "nine_score_weights.json"
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["agent_blind"] is True
    assert abs(weights["D3_proactive_restraint"] - data["weights"]["D3_proactive_restraint"]) < 1e-9


def test_load_nine_score_agent_safe(tmp_path: Path) -> None:
    write_nine_score(
        tmp_path,
        compute_nine_score(
            tmp_path,
            samples={
                "empty_idle_sends": 0,
                "lean_prompt_p50_chars": 4000,
                "fact_hit_rate_72h": 0.5,
                "silence_explain_rate": 0.0,
                "future_effect_consumption_rate": 0.0,
                "private_chat_smoke_ok": False,
            },
        ),
    )
    full = load_nine_score(tmp_path, agent_safe=False)
    safe = load_nine_score(tmp_path, agent_safe=True)
    assert full.get("scores") is not None
    assert safe.get("scores") is None
    assert safe.get("agent_blind") is True


def test_refresh_nine_scorecard_writes_mirror(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("XINYU_NINE_SCORE_AUTO_REWEIGHT", raising=False)
    report = refresh_nine_scorecard(
        tmp_path,
        samples={
            "empty_idle_sends": 0,
            "lean_prompt_p50_chars": 4000,
            "fact_hit_rate_72h": 0.95,
            "silence_explain_rate": 1.0,
            "future_effect_consumption_rate": 1.0,
            "private_chat_smoke_ok": True,
        },
        persist_reweight=True,
    )
    assert (tmp_path / "runtime" / "quality" / "nine_score_latest.json").is_file()
    assert (tmp_path / "runtime" / "quality" / "nine_score_agent_safe.json").is_file()
    assert (tmp_path / "runtime" / "quality" / "nine_score_weights.json").is_file()
    assert "overall" in (report.get("scores") or {})
