from __future__ import annotations

import json
from pathlib import Path

from xinyu_nine_score import write_nine_score, compute_nine_score
from xinyu_nine_score_ab import (
    load_nine_score_ab,
    nine_score_status_fields,
    run_nine_score_ab_sample,
)
from xinyu_status_collect import nine_score_fields


def _healthy_samples() -> dict:
    return {
        "empty_idle_sends": 0,
        "lean_prompt_p50_chars": 4000,
        "fact_hit_rate_72h": 0.95,
        "silence_explain_rate": 1.0,
        "future_effect_consumption_rate": 1.0,
        "private_chat_smoke_ok": True,
        "D1_oral": 8.0,
        "D2_memory": 8.0,
        "D3_proactive_restraint": 9.0,
        "D4_autonomy_loop": 7.0,
        "D5_live_stability": 8.0,
        "D6_modularity": 4.0,
        "D7_skills": 4.0,
        "D8_body_feedback": 6.0,
        "D9_ops_security": 6.0,
    }


def test_ab_sample_persists_and_has_delta(tmp_path: Path) -> None:
    write_nine_score(tmp_path, compute_nine_score(tmp_path, samples=_healthy_samples()))
    report = run_nine_score_ab_sample(tmp_path, samples=_healthy_samples(), persist=True)
    assert "equal" in report and "reweight" in report
    assert "delta_overall" in report
    assert report["agent_blind"] is True
    path = tmp_path / "runtime" / "quality" / "nine_score_ab_latest.json"
    assert path.is_file()
    loaded = load_nine_score_ab(tmp_path)
    assert loaded.get("sampled_at")
    hist = tmp_path / "runtime" / "quality" / "nine_score_ab_history.jsonl"
    assert hist.is_file()
    line = hist.read_text(encoding="utf-8").strip().splitlines()[-1]
    assert "delta_overall" in json.loads(line)


def test_unhealthy_vs_healthy_reweight_direction(tmp_path: Path) -> None:
    healthy = run_nine_score_ab_sample(tmp_path, samples=_healthy_samples(), persist=False)
    unhealthy_samples = dict(_healthy_samples())
    unhealthy_samples.update(
        {
            "empty_idle_sends": 2,
            "silence_explain_rate": 0.2,
            "future_effect_consumption_rate": 0.1,
            "fact_hit_rate_72h": 0.2,
            "lean_prompt_p50_chars": 20000,
            "private_chat_smoke_ok": False,
        }
    )
    unhealthy = run_nine_score_ab_sample(tmp_path, samples=unhealthy_samples, persist=False)
    # Reweight should pull D3/D2 up when healthy relative to unhealthy weight mass.
    h_d3 = healthy["reweight"]["weights"]["D3_proactive_restraint"]
    u_d3 = unhealthy["reweight"]["weights"]["D3_proactive_restraint"]
    assert h_d3 > u_d3


def test_status_fields_include_nine_score(tmp_path: Path) -> None:
    write_nine_score(tmp_path, compute_nine_score(tmp_path, samples=_healthy_samples()))
    run_nine_score_ab_sample(tmp_path, samples=_healthy_samples(), persist=True)
    fields = nine_score_status_fields(tmp_path)
    assert fields["nine_score_agent_blind"] == "true"
    assert fields["nine_score_overall"] != "missing"
    assert fields["nine_score_ab_delta"] != "missing"
    via_collect = nine_score_fields(tmp_path)
    assert via_collect["nine_score_gates_pass"] in {"true", "false"}
