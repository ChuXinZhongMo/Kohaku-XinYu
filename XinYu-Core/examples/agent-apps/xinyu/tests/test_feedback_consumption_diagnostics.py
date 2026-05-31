from __future__ import annotations

import json
from pathlib import Path

from xinyu_feedback_consumption_diagnostics import (
    build_feedback_consumption_diagnostics,
    render_feedback_consumption_diagnostics,
    write_feedback_consumption_diagnostics,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_feedback_consumption_diagnostics_reports_rate_without_raw_text(tmp_path: Path) -> None:
    raw_private = "RAW_FEEDBACK_CONSUMPTION_SHOULD_NOT_SURFACE_1001"
    visible_reply = "VISIBLE_REPLY_FEEDBACK_CONSUMPTION_SHOULD_NOT_SURFACE_1001"
    _write_jsonl(
        tmp_path / "runtime/intention_ecology_trace.jsonl",
        [
            {
                "checked_at": "2026-05-29T10:00:00+08:00",
                "ecology_id": "eco-rate-1",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
                "raw_private_body": raw_private,
            },
            {
                "checked_at": "2026-05-29T10:01:00+08:00",
                "ecology_id": "eco-rate-2",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "owner_feedback_effect:owner_reported_template_voice_failure",
                "feedback_consumed_biases": "owner_feedback_effect_bias:repair_relation_visible_risk:-2",
                "feedback_consumed_future_effect": "owner_feedback_future:reduce_template_voice",
                "visible_reply_text": visible_reply,
            },
            {
                "checked_at": "2026-05-29T10:02:00+08:00",
                "ecology_id": "eco-rate-3",
                "feedback_consumption_status": "partial",
                "feedback_consumed_sources": "action_feedback_coverage:runtime_probe_turn_active/running",
                "feedback_consumed_biases": "none",
                "feedback_consumed_future_effect": "none",
            },
            {
                "checked_at": "2026-05-29T10:03:00+08:00",
                "ecology_id": "eco-rate-4",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "owner_response_feedback:desktop_read_locally",
                "feedback_consumed_biases": "owner_response_strategy_bias:desktop_followup_without_reasking",
                "feedback_consumed_future_effect": "owner_response_future:avoid_repeat_prompt",
            },
        ],
    )

    report = build_feedback_consumption_diagnostics(tmp_path)
    rendered = render_feedback_consumption_diagnostics(report)
    paths = write_feedback_consumption_diagnostics(tmp_path, report)
    state = Path(paths["state_path"]).read_text(encoding="utf-8")
    trace = (tmp_path / "runtime/feedback_consumption_diagnostics_trace.jsonl").read_text(encoding="utf-8")

    assert report["status"] == "needs_check"
    assert report["metrics"]["sample_count"] == 4
    assert report["metrics"]["feedback_required_count"] == 4
    assert report["metrics"]["consumed_count"] == 3
    assert report["metrics"]["partial_count"] == 1
    assert report["metrics"]["consumption_rate_pct"] == 75.0
    assert report["latest_sample"]["status"] == "consumed"
    assert report["stage7_feedback_closure"]["status"] == "needs_check"
    assert report["stage7_feedback_closure"]["ready_for_stage8"] is False
    for text in (rendered, state, trace):
        assert raw_private not in text
        assert visible_reply not in text


def test_feedback_consumption_diagnostics_needs_check_when_latest_missing(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/intention_ecology_trace.jsonl",
        [
            {
                "checked_at": "2026-05-29T11:00:00+08:00",
                "ecology_id": "eco-missing-1",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
            },
            {
                "checked_at": "2026-05-29T11:01:00+08:00",
                "ecology_id": "eco-missing-2",
                "feedback_consumed_sources": "owner_feedback_effect:owner_reported_context_discontinuity",
                "feedback_consumed_biases": "none",
                "feedback_consumed_future_effect": "none",
            },
        ],
    )

    report = build_feedback_consumption_diagnostics(tmp_path)

    assert report["ok"] is False
    assert report["status"] == "needs_check"
    assert report["latest_sample"]["status"] == "missing"
    assert report["metrics"]["missing_count"] == 1
    assert report["metrics"]["missing_streak"] == 1
    assert report["stage7_feedback_closure"]["status"] == "needs_check"


def test_feedback_consumption_diagnostics_no_samples(tmp_path: Path) -> None:
    report = build_feedback_consumption_diagnostics(tmp_path)

    assert report["ok"] is True
    assert report["status"] == "no_samples"
    assert report["metrics"]["sample_count"] == 0
    assert report["latest_sample"]["status"] == "none"
    assert report["stage7_feedback_closure"]["status"] == "no_samples"


def test_feedback_consumption_diagnostics_excludes_legacy_rows_from_rate(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/intention_ecology_trace.jsonl",
        [
            {
                "checked_at": "2026-05-29T12:00:00+08:00",
                "ecology_id": "eco-legacy-1",
                "action_feedback_signal": "qq_visible_reply_ack",
                "action_feedback_coverage_signal": "runtime_probe_turn_active",
            },
            {
                "checked_at": "2026-05-29T12:01:00+08:00",
                "ecology_id": "eco-legacy-2",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
            },
        ],
    )

    report = build_feedback_consumption_diagnostics(tmp_path)

    assert report["status"] == "pass"
    assert report["metrics"]["sample_count"] == 2
    assert report["metrics"]["feedback_required_count"] == 1
    assert report["metrics"]["legacy_uninstrumented_count"] == 1
    assert report["metrics"]["consumption_rate_pct"] == 100.0
    assert report["stage7_feedback_closure"]["status"] == "collecting_samples"
    assert report["stage7_feedback_closure"]["ready_for_stage8"] is False


def test_feedback_consumption_diagnostics_marks_stage7_ready_after_consecutive_samples(tmp_path: Path) -> None:
    rows = []
    for index in range(3):
        rows.append(
            {
                "checked_at": f"2026-05-29T14:0{index}:00+08:00",
                "ecology_id": f"eco-ready-{index}",
                "feedback_consumption_status": "consumed",
                "feedback_consumed_sources": "action_feedback:qq_visible_reply_ack",
                "feedback_consumed_biases": "action_feedback_bias:route_confirmed_visible_reply_risk:-4",
                "feedback_consumed_future_effect": "action_feedback_future:confirm_visible_reply_transport",
            }
        )
    _write_jsonl(tmp_path / "runtime/intention_ecology_trace.jsonl", rows)

    report = build_feedback_consumption_diagnostics(tmp_path)

    assert report["status"] == "pass"
    assert report["metrics"]["feedback_required_count"] == 3
    assert report["metrics"]["consumed_streak"] == 3
    assert report["stage7_feedback_closure"]["status"] == "ready"
    assert report["stage7_feedback_closure"]["ready_for_stage8"] is True
