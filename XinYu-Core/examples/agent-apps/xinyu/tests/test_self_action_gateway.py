from __future__ import annotations

import json
from pathlib import Path

from xinyu_self_action_gateway import (
    APPROVAL_QUEUE_REL,
    APPROVAL_HANDOFF_REL,
    STATE_JSON_REL,
    STATE_MD_REL,
    TRACE_REL,
    decide_self_action_approval,
    execute_approved_self_actions,
    list_self_action_approvals,
    run_self_action_gateway,
)
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_compile_targets(root: Path, *, broken: bool = False) -> None:
    _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'goal'\n")
    _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'observer'\n")
    if broken:
        _write(root / "xinyu_self_action_gateway.py", "def broken(:\n    pass\n")
    else:
        _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'action'\n")


def test_bounded_work_executes_low_risk_compile_and_queues_code_approval(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active. token=abc123456")
    selected = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    state_text = (tmp_path / STATE_MD_REL).read_text(encoding="utf-8")
    state_json = json.loads((tmp_path / STATE_JSON_REL).read_text(encoding="utf-8"))
    queue = _read_jsonl(tmp_path / APPROVAL_QUEUE_REL)
    trace = _read_jsonl(tmp_path / TRACE_REL)

    assert selected["selected_goal_id"] == "continue_bounded_work"
    assert result["executed_action_count"] == 1
    assert result["queued_approval_count"] == 1
    assert result["low_risk_results"][0]["action_kind"] == "local_py_compile_probe"
    assert result["low_risk_results"][0]["result"] == "success"
    assert queue[-1]["action_kind"] == "self_code_patch_request"
    assert queue[-1]["status"] == "pending_owner_approval"
    assert state_json["pending_approval_count"] == 1
    assert "low_risk_auto_execute" in state_text
    assert "token=abc123456" not in state_text
    assert any(row.get("event_kind") == "self_action_executed" for row in trace)


def test_repeated_approval_candidate_is_deduped(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    first = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")
    second = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:02:00+08:00", trigger="test")
    queue = _read_jsonl(tmp_path / APPROVAL_QUEUE_REL)

    assert first["queued_approval_count"] == 1
    assert second["queued_approval_count"] == 0
    assert second["skipped_approval_count"] == 1
    assert len(queue) == 1


def test_approval_latest_and_execute_creates_local_handoff(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    listed = list_self_action_approvals(tmp_path)
    queue_id = listed["approval_queue"]["latest_pending_queue_id"]
    approved = decide_self_action_approval(
        tmp_path,
        queue_id="latest",
        decision="approved",
        decided_at="2026-05-16T10:02:00+08:00",
        execute=True,
    )
    relisted = list_self_action_approvals(tmp_path)
    handoff = (tmp_path / APPROVAL_HANDOFF_REL).read_text(encoding="utf-8")
    state_text = (tmp_path / STATE_MD_REL).read_text(encoding="utf-8")
    queue = _read_jsonl(tmp_path / APPROVAL_QUEUE_REL)

    assert queue_id.startswith("selfaction-approval-")
    assert approved["decision"] == "approved"
    assert approved["execution"]["executed_count"] == 1
    assert relisted["approval_queue"]["pending_count"] == 0
    assert relisted["approval_queue"]["executed_count"] == 1
    assert "codex_handoff_ticket" in handoff
    assert "no source file was edited by the gateway" in handoff
    assert "latest_executed_queue_id" in state_text
    assert any(row.get("event_kind") == "self_action_approval_decided" for row in queue)
    assert any(row.get("event_kind") == "self_action_approval_executed" for row in queue)


def test_denied_approval_is_not_executable(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    denied = decide_self_action_approval(
        tmp_path,
        queue_id="latest",
        decision="denied",
        decided_at="2026-05-16T10:02:00+08:00",
    )
    execution = execute_approved_self_actions(tmp_path, queue_id="next", checked_at="2026-05-16T10:03:00+08:00")
    listed = list_self_action_approvals(tmp_path)

    assert denied["decision"] == "denied"
    assert execution["accepted"] is False
    assert execution["reason"] == "no_approved_action"
    assert listed["approval_queue"]["denied_count"] == 1


def test_compile_failure_is_recorded_as_failed_low_risk_action(tmp_path: Path) -> None:
    _seed_compile_targets(tmp_path, broken=True)
    _write(tmp_path / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    low = result["low_risk_results"][0]
    assert low["status"] == "executed"
    assert low["result"] == "failed"
    assert low["error_code"] == "py_compile_failed"
    assert "self_action:executed/continue_bounded_work/failed" in result["notes"]


def test_quiet_goal_runs_boundary_probe_without_outward_queue(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/current_life_posture.md",
        "- no_proactive_constraint: block proactive during rest/silence boundary",
    )
    selected = run_self_chosen_goal_ecology(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:01:00+08:00", trigger="test")

    assert selected["selected_goal_id"] == "quiet_presence"
    assert result["executed_action_count"] == 1
    assert result["queued_approval_count"] == 0
    assert result["low_risk_results"][0]["action_kind"] == "quiet_boundary_probe"
    assert not (tmp_path / APPROVAL_QUEUE_REL).exists()


def test_gateway_without_selected_goal_is_safe_noop(tmp_path: Path) -> None:
    result = run_self_action_gateway(tmp_path, checked_at="2026-05-16T10:00:00+08:00", trigger="test")

    assert result["selected_goal_id"] == "none"
    assert result["candidate_count"] == 0
    assert result["executed_action_count"] == 0
    assert result["queued_approval_count"] == 0
