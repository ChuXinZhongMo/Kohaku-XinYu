from __future__ import annotations

import json
from pathlib import Path

from xinyu_contextual_self_replay import (
    load_public_replay_samples,
    replay_samples,
    run_public_dataset_replay,
    run_replay_calibration_report,
)


FIXTURE = Path(__file__).parent / "fixtures" / "contextual_public_replay_sample.jsonl"
HF_ROWS_FIXTURE = Path(__file__).parent / "fixtures" / "contextual_hf_rows_sample.json"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_public_replay_loader_extracts_common_open_dataset_shapes() -> None:
    result = load_public_replay_samples([FIXTURE], limit=10)

    assert result.warnings == ()
    assert len(result.samples) == 5
    assert {sample.dataset for sample in result.samples} == {
        "chmapdata",
        "lmsys-chat-1m",
        "lufy",
        "wildchat",
    }
    assert {sample.expected_scene for sample in result.samples} == {
        "emotional_relation",
        "casual_chat",
        "initiative_feedback",
        "memory_review",
        "project_work",
    }
    assert any(sample.evidence_like for sample in result.samples)


def test_public_replay_loader_extracts_huggingface_rows_api_shape() -> None:
    result = load_public_replay_samples([HF_ROWS_FIXTURE], limit=10)

    assert result.warnings == ()
    assert len(result.samples) == 3
    assert result.samples[0].dataset == "hf-public"
    assert result.samples[0].expected_scene == "runtime_status"
    assert result.samples[1].dataset == "hf-turns"
    assert result.samples[1].expected_scene == "project_work"
    assert result.samples[2].dataset == "hf-raw-dialogue"
    assert result.samples[2].expected_scene == "emotional_relation"


def test_public_dataset_replay_resolves_dataset_name_without_explicit_path(tmp_path: Path) -> None:
    dataset = tmp_path / "library" / "datasets" / "lufy-auto.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    summary = run_public_dataset_replay(
        tmp_path,
        [],
        dataset_name="lufy",
        limit=2,
        started_at="2026-05-13T03:00:00+08:00",
        write_summary=False,
    )

    assert summary["sample_count"] == 2
    assert summary["load_warnings"] == []


def test_public_dataset_replay_drives_contextual_loop_recall_and_observatory(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/recent_context.md",
        """
        - current_goal: replay public dialogue samples through contextual self calibration
        - next_step: inspect scene mismatch and recall sparsity
        """,
    )
    _write(
        tmp_path / "memory/context/initiative_lifecycle_state.md",
        """
        - selected_decision: hold_private
        - selected_score: 42
        - delivery_level: private
        - pending_feedback_count: 1
        """,
    )

    summary = run_public_dataset_replay(
        tmp_path,
        [FIXTURE],
        limit=10,
        started_at="2026-05-13T03:00:00+08:00",
    )

    replay_events = _read_jsonl(tmp_path / "runtime/contextual_self_replay_trace.jsonl")
    self_events = _read_jsonl(tmp_path / "runtime/contextual_self_loop_trace.jsonl")
    recall_events = _read_jsonl(tmp_path / "runtime/contextual_recall_trace.jsonl")
    replay_text = (tmp_path / "runtime/contextual_self_replay_trace.jsonl").read_text(encoding="utf-8")
    self_text = (tmp_path / "runtime/contextual_self_loop_trace.jsonl").read_text(encoding="utf-8")

    assert summary["sample_count"] == 5
    assert summary["scene_match_rate"] == 1.0
    assert summary["observed_scene_counts"]["project_work"] == 1
    assert summary["observed_scene_counts"]["memory_review"] == 1
    assert summary["retrieval_pressure_counts"]["high"] == 1
    assert summary["evidence_like_sample_count"] == 1
    assert summary["evidence_like_sample_recall_rate"] == 1.0
    assert summary["evidence_like_pressure_detected_rate"] == 1.0
    assert "high_pressure_weak_evidence_count" in summary
    assert "high_pressure_usable_evidence_count" in summary
    assert len(replay_events) == 5
    assert len(self_events) == 5
    assert len(recall_events) == 5
    assert any(event["retrieval_pressure_signals"] for event in replay_events)
    assert all("evidence_sufficiency" in event for event in replay_events)
    assert all("answer_discipline" in event for event in replay_events)
    assert all(event["user_text_hash"] for event in replay_events)
    assert "\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u56de\u653e\u6a21\u5757" not in replay_text
    assert "\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u56de\u653e\u6a21\u5757" not in self_text
    assert (tmp_path / "memory/context/contextual_self_replay_state.md").exists()
    assert (tmp_path / "runtime/contextual_self_observatory.json").exists()
    assert (tmp_path / "runtime/contextual_self_replay_calibration_report.json").exists()


def test_replay_calibration_report_is_diagnostic_and_leak_free(tmp_path: Path) -> None:
    run_public_dataset_replay(
        tmp_path,
        [FIXTURE],
        limit=10,
        started_at="2026-05-13T03:00:00+08:00",
    )

    report = run_replay_calibration_report(tmp_path, limit=10, observed_at="2026-05-13T03:10:00+08:00")
    report_text = (tmp_path / "runtime/contextual_self_replay_calibration_report.json").read_text(encoding="utf-8")

    assert report["sample_count"] == 5
    assert report["evidence_like_sample_count"] == 1
    assert report["evidence_like_pressure_detected_rate"] == 1.0
    assert "dataset_pressure_counts" in report
    assert "dataset_sufficiency_counts" in report
    assert "over_retrieval_candidates" in report
    diagnostic_items = report["over_retrieval_candidates"] or report["evidence_like_missed"]
    trace_items = _read_jsonl(tmp_path / "runtime/contextual_self_replay_trace.jsonl")
    if not diagnostic_items:
        diagnostic_items = [trace_items[0]]
    first_candidate = diagnostic_items[0]
    trace_first = trace_items[0]
    assert "text_shape" in first_candidate or "text_shape" in trace_first
    assert "candidate_reason" in first_candidate or "candidate_reason" in trace_first
    assert "user_text_hash" in first_candidate
    assert "no_raw_user_text" in report["notes"]
    assert "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u56de\u7b54" not in report_text
    assert "\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u56de\u653e\u6a21\u5757" not in report_text


def test_replay_samples_reports_scene_mismatches_without_raw_text(tmp_path: Path) -> None:
    load_result = load_public_replay_samples([FIXTURE], limit=1)
    bad_sample = load_result.samples[0].__class__(
        sample_id="bad-label",
        dataset="fixture",
        text=load_result.samples[0].text,
        expected_scene="casual_chat",
        source_ref="fixture",
        turn_index=0,
    )

    summary = replay_samples(
        tmp_path,
        [bad_sample],
        started_at="2026-05-13T03:00:00+08:00",
    )
    trace_text = (tmp_path / "runtime/contextual_self_replay_trace.jsonl").read_text(encoding="utf-8")

    assert summary["scene_match_rate"] == 0.0
    assert summary["mismatches"][0]["sample_id"] == "bad-label"
    assert load_result.samples[0].text not in trace_text
