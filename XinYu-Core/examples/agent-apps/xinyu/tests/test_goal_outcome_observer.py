from __future__ import annotations

import json
from pathlib import Path

from xinyu_goal_outcome_observer import OBSERVER_STATE_REL, run_goal_outcome_observer
from xinyu_self_chosen_goal_ecology import (
    STATE_JSON_REL,
    STATE_MD_REL,
    TRACE_REL,
    build_self_chosen_goal_decision,
    run_self_chosen_goal_ecology,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_clean_maintenance_records_useful_for_bounded_work_without_raw_note_leak(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    selected = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_goal_outcome_observer(
        tmp_path,
        checked_at="2026-05-16T10:05:00+08:00",
        trigger="test",
        maintenance_notes=[
            "self_thought:held/request_candidate/runtime/secret=abc123456",
            "daily_digest:skipped/false",
            "memory_self_review:ok/0",
        ],
    )

    observer_state = (tmp_path / OBSERVER_STATE_REL).read_text(encoding="utf-8")
    goal_state = (tmp_path / STATE_MD_REL).read_text(encoding="utf-8")
    ecology_json = json.loads((tmp_path / STATE_JSON_REL).read_text(encoding="utf-8"))
    trace = _read_jsonl(tmp_path / TRACE_REL)

    assert selected["selected_goal_id"] == "continue_bounded_work"
    assert result["status"] == "recorded"
    assert result["outcome"] == "useful"
    assert result["reason_code"] == "local_maintenance_completed"
    assert ecology_json["goals"]["continue_bounded_work"]["habit_weight"] > 0
    assert "## Outcome Ecology Report" in goal_state
    assert "last_outcome: useful" in goal_state
    assert "observations_24h:" in goal_state
    assert "secret=abc123456" not in goal_state
    assert "secret=abc123456" not in observer_state
    assert any(row.get("event_kind") == "goal_ecology_outcome_observed" for row in trace)

    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T13:00:00+08:00", trigger="test")
    rewritten_state = (tmp_path / STATE_MD_REL).read_text(encoding="utf-8")
    assert "## Outcome Ecology Report" in rewritten_state
    assert "last_outcome: useful" in rewritten_state


def test_error_note_records_blocked_and_cools_selected_goal(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_goal_outcome_observer(
        tmp_path,
        checked_at="2026-05-16T10:05:00+08:00",
        trigger="test",
        maintenance_notes=["self_thought_error:RuntimeError"],
    )
    later = build_self_chosen_goal_decision(tmp_path, checked_at="2026-05-16T10:06:00+08:00")
    bounded = next(item for item in later.candidates if item.goal_id == "continue_bounded_work")

    assert result["status"] == "recorded"
    assert result["outcome"] == "blocked"
    assert result["reason_code"] == "maintenance_sidecar_error"
    assert bounded.status == "cooldown"
    assert later.selected_goal_id != "continue_bounded_work"


def test_repair_signal_records_useful_feedback_absorption(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        "- status: trial_active\n- repair_count: 1\n- latest_failure_kind: template_voice_failure\n- next_action: apply repair habit",
    )
    selected = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_goal_outcome_observer(tmp_path, checked_at="2026-05-16T10:05:00+08:00", trigger="test")

    assert selected["selected_goal_id"] == "absorb_feedback_repair"
    assert result["status"] == "recorded"
    assert result["outcome"] == "useful"
    assert result["reason_code"] == "learning_repair_signal"


def test_duplicate_observation_is_not_recorded_twice(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    notes = ["self_thought:held/request_candidate/runtime", "daily_digest:skipped/false", "memory_self_review:ok/0"]

    first = run_goal_outcome_observer(
        tmp_path,
        checked_at="2026-05-16T10:05:00+08:00",
        trigger="test",
        maintenance_notes=notes,
    )
    second = run_goal_outcome_observer(
        tmp_path,
        checked_at="2026-05-16T10:06:00+08:00",
        trigger="test",
        maintenance_notes=notes,
    )
    trace = _read_jsonl(tmp_path / TRACE_REL)
    recorded_rows = [row for row in trace if row.get("event_kind") == "goal_ecology_outcome_recorded"]

    assert first["status"] == "recorded"
    assert second["status"] == "skipped_duplicate"
    assert len(recorded_rows) == 1


def test_observer_skips_without_selected_goal(tmp_path: Path) -> None:
    result = run_goal_outcome_observer(tmp_path, checked_at="2026-05-16T10:00:00+08:00")

    assert result["status"] == "skipped"
    assert result["reason"] == "no_selected_goal"
