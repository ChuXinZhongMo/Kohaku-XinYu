from __future__ import annotations

import json
from pathlib import Path

from xinyu_self_chosen_goal_ecology import (
    STATE_JSON_REL,
    STATE_MD_REL,
    TRACE_REL,
    build_self_chosen_goal_decision,
    record_self_chosen_goal_outcome,
    run_self_chosen_goal_ecology,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_technical_residue_selects_bounded_work_and_writes_safe_state(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/recent_context.md",
        "Codex runtime retrieval replay pytest work remains active. token=abc123456",
    )

    result = run_self_chosen_goal_ecology(
        tmp_path,
        checked_at="2026-05-16T10:00:00+08:00",
        trigger="test",
    )

    state = (tmp_path / STATE_MD_REL).read_text(encoding="utf-8")
    trace = _read_jsonl(tmp_path / TRACE_REL)

    assert result["selected_goal_id"] == "continue_bounded_work"
    assert "action_policy: state_only_no_outward_action" in state
    assert "never sends messages, edits files, calls tools" in state
    assert "token=abc123456" not in state
    assert "sha256:" in state
    assert trace[-1]["selected_goal_id"] == "continue_bounded_work"


def test_no_pressure_defaults_to_quiet_presence(tmp_path: Path) -> None:
    result = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00")

    assert result["selected_goal_id"] == "quiet_presence"
    assert result["action_policy"] == "state_only_no_outward_action"


def test_successful_outcome_increases_goal_habit_after_cooldown(tmp_path: Path) -> None:
    _write(
        tmp_path / "runtime/replay_candidates/chat_replay_export_summary.json",
        json.dumps({"selected_count": 3}, ensure_ascii=False),
    )

    first = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00")
    outcome = record_self_chosen_goal_outcome(
        tmp_path,
        "curate_failure_replay",
        "success",
        observed_at="2026-05-16T10:10:00+08:00",
        note="private text should be hashed only",
    )
    later = build_self_chosen_goal_decision(tmp_path, checked_at="2026-05-16T13:00:00+08:00")
    state = json.loads((tmp_path / STATE_JSON_REL).read_text(encoding="utf-8"))

    assert first["selected_goal_id"] == "curate_failure_replay"
    assert outcome["habit_weight_after"] > outcome["habit_weight_before"]
    assert state["goals"]["curate_failure_replay"]["last_note_hash"]
    assert later.selected_goal_id == "curate_failure_replay"


def test_blocked_outcome_puts_goal_on_cooldown_and_switches_choice(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest retrieval work remains active.")
    first = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00")
    record_self_chosen_goal_outcome(
        tmp_path,
        "continue_bounded_work",
        "blocked",
        observed_at="2026-05-16T10:01:00+08:00",
    )

    second = build_self_chosen_goal_decision(tmp_path, checked_at="2026-05-16T10:02:00+08:00")
    continue_candidate = next(item for item in second.candidates if item.goal_id == "continue_bounded_work")

    assert first["selected_goal_id"] == "continue_bounded_work"
    assert continue_candidate.status == "cooldown"
    assert second.selected_goal_id != "continue_bounded_work"


def test_quiet_pressure_selects_quiet_presence(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/current_life_posture.md", "- no_proactive_constraint: block proactive during rest/silence boundary")
    _write(
        tmp_path / "runtime/life_kernel/self_choice_state.json",
        json.dumps(
            {
                "version": 1,
                "runtime_affect": {"urge_to_express": 0.2, "self_closure": 0.8, "fatigue": 0.8},
                "affective_sediment": {},
            },
            ensure_ascii=False,
        ),
    )

    result = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00")

    assert result["selected_goal_id"] == "quiet_presence"
    assert result["action_policy"] == "state_only_no_outward_action"


def test_repair_pressure_can_drive_feedback_absorption_goal(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/self/learning_closed_loop_state.md",
        "- status: trial_active\n- latest_failure_kind: template_voice_failure\n- next_action: apply repair habit",
    )

    result = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00")

    assert result["selected_goal_id"] == "absorb_feedback_repair"
