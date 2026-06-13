from __future__ import annotations

import json
from pathlib import Path

from xinyu_computer_control import (
    ACTIONS_REL,
    build_computer_snapshot,
    classify_computer_action,
    evaluate_computer_action,
    is_sensitive_window,
    run_computer_action,
)


def _grant(**over) -> dict:
    base = {"enabled": True, "observe_only": True, "single_step_actions": False}
    base.update(over)
    return base


def _actions(tmp_path: Path) -> list:
    path = tmp_path / ACTIONS_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_observe_only_works_without_execution_grant(tmp_path: Path) -> None:
    result = run_computer_action(
        tmp_path,
        action_kind="screenshot",
        grant=_grant(single_step_actions=False),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is True
    assert result["result"] in {"completed", "simulated"}
    record = _actions(tmp_path)[-1]
    assert record["risk"] == "read_only"
    assert record["coordinate_plane"] == "viewport_0_1000"


def test_proposal_only_never_executes(tmp_path: Path) -> None:
    result = run_computer_action(
        tmp_path,
        action_kind="propose_click",
        x=500,
        y=500,
        grant=_grant(),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is True
    assert result["result"] == "proposed"
    assert result["record"]["last_action_marker"]["type"] == "click"
    assert result["record"]["last_action_marker"]["x"] == 500


def test_click_blocks_without_approval(tmp_path: Path) -> None:
    result = run_computer_action(
        tmp_path,
        action_kind="click",
        x=100,
        y=200,
        grant=_grant(single_step_actions=False),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["decision"]["reason"] == "approval_required"
    assert result["result"] == "blocked"


def test_click_with_single_step_grant_needs_real_backend(tmp_path: Path) -> None:
    decision = evaluate_computer_action("click", grant=_grant(single_step_actions=True))
    assert decision.ok is True
    result = run_computer_action(
        tmp_path,
        action_kind="click",
        x=100,
        y=200,
        grant=_grant(single_step_actions=True),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    # Allowed by policy, but no backend -> typed block, never simulated success.
    assert result["record"]["error_code"] == "computer_backend_unavailable"


def test_arbitrary_control_is_blocked() -> None:
    assert classify_computer_action("arbitrary_keyboard_mouse") == ("high_blocked", True)
    assert classify_computer_action("multi_step") == ("high_blocked", True)


def test_sensitive_window_blocks_execution(tmp_path: Path) -> None:
    assert is_sensitive_window("MyBank Online Login")[0] is True
    result = run_computer_action(
        tmp_path,
        action_kind="click",
        window_title="MyBank Online Login",
        x=10,
        y=10,
        grant=_grant(single_step_actions=True),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["decision"]["reason"].startswith("sensitive_window_blocked")


def test_computer_grant_disabled_blocks_observe(tmp_path: Path) -> None:
    result = run_computer_action(
        tmp_path,
        action_kind="screenshot",
        grant=_grant(enabled=False),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["decision"]["reason"] == "computer_control_grant_disabled"


def test_snapshot_reports_disabled_multistep(tmp_path: Path) -> None:
    run_computer_action(
        tmp_path,
        action_kind="screenshot",
        grant=_grant(),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    snap = build_computer_snapshot(tmp_path)
    assert snap["boundaries"]["multi_step_arbitrary_control"] == "disabled"
    assert snap["observed_count"] >= 1
