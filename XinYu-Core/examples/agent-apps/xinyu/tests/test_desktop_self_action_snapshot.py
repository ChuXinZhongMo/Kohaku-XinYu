from __future__ import annotations

import json
from pathlib import Path

from xinyu_bridge_desktop_snapshot import desktop_self_action_snapshot


def _write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def _append_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_desktop_self_action_snapshot_surfaces_gateway_patch_executor(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "runtime/self_action_gateway/state.json",
        {
            "updated_at": "2026-05-16T09:44:29+08:00",
            "last_run": {
                "checked_at": "2026-05-16T09:43:11+08:00",
                "selected_goal_id": "curate_failure_replay",
                "candidate_count": 2,
                "executed_action_count": 1,
                "queued_approval_count": 1,
            },
            "approval_queue": {
                "pending_count": 0,
                "approved_waiting_execution_count": 0,
                "executed_count": 2,
                "denied_count": 0,
                "blocked_execution_count": 0,
                "latest_pending_queue_id": "none",
                "latest_approved_queue_id": "none",
                "latest_executed_queue_id": "selfaction-approval-test",
            },
            "latest_approval_execution": {
                "queue_id": "selfaction-approval-test",
                "approval_id": "selfaction-decision-test",
                "goal_id": "curate_failure_replay",
                "action_kind": "self_code_patch_request",
                "approval_scope": "replay_fixture_or_test_patch",
                "execution_result": "handoff_created",
            },
            "last_candidates": [
                {
                    "action_id": "selfact-probe",
                    "goal_id": "curate_failure_replay",
                    "action_kind": "replay_material_probe",
                    "label": "inspect replay material counts",
                    "risk": "low_local",
                    "requires_approval": False,
                    "tool": "state_probe",
                },
                {
                    "action_id": "selfact-patch",
                    "goal_id": "curate_failure_replay",
                    "action_kind": "self_code_patch_request",
                    "label": "request approval for replay fixture promotion patch",
                    "risk": "approval_required",
                    "requires_approval": True,
                    "tool": "approval_queue",
                },
            ],
        },
    )
    _append_jsonl(
        tmp_path / "memory/context/self_action_gateway_approval_queue.jsonl",
        [
            {
                "event_kind": "self_action_approval_queued",
                "queue_id": "selfaction-approval-test",
                "goal_id": "curate_failure_replay",
                "action_kind": "self_code_patch_request",
                "status": "pending_owner_approval",
                "queued_at": "2026-05-16T09:43:11+08:00",
            },
            {
                "event_kind": "self_action_approval_executed",
                "queue_id": "selfaction-approval-test",
                "approval_id": "selfaction-decision-test",
                "goal_id": "curate_failure_replay",
                "action_kind": "self_code_patch_request",
                "status": "executed",
                "result": "handoff_created",
                "checked_at": "2026-05-16T09:44:29+08:00",
            },
        ],
    )
    (tmp_path / "memory/context/self_action_gateway_execution_handoff.md").write_text(
        """
# Self Action Gateway Execution Handoff

## Approved Action
- queue_id: selfaction-approval-test
- approval_id: selfaction-decision-test
- goal_id: curate_failure_replay
- action_kind: self_code_patch_request
- approval_scope: replay_fixture_or_test_patch
- execution_mode: codex_handoff_ticket
- next_executor: codex_after_owner_approval
""".strip()
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / "runtime/self_action_patch_executor/state.json",
        {
            "updated_at": "2026-05-16T09:44:29+08:00",
            "status": "prepared",
            "execution_level": "prepare",
            "last_queue_id": "selfaction-approval-test",
            "last_approval_id": "selfaction-decision-test",
            "last_goal_id": "curate_failure_replay",
            "last_action_kind": "self_code_patch_request",
            "last_task_id": "selfaction-patch-test",
            "last_task_path": "runtime/self_action_patch_executor/tasks/selfaction-patch-test.json",
            "last_task_markdown_path": "memory/context/self_action_patch_executor_task.md",
            "last_codex_status": "not_requested",
            "last_report_path": "",
        },
    )

    snapshot = desktop_self_action_snapshot(tmp_path)

    assert snapshot["observed"] is True
    assert snapshot["selectedGoalId"] == "curate_failure_replay"
    assert snapshot["selectedActionKind"] == "self_code_patch_request"
    assert snapshot["pendingApprovalCount"] == 0
    assert snapshot["approvalQueue"]["executedCount"] == 2
    assert snapshot["latestApprovalEvent"]["eventKind"] == "self_action_approval_executed"
    assert snapshot["handoff"]["exists"] is True
    assert snapshot["handoff"]["nextExecutor"] == "codex_after_owner_approval"
    assert snapshot["patchExecutor"]["status"] == "prepared"
    assert snapshot["patchExecutor"]["taskId"] == "selfaction-patch-test"
    assert snapshot["patchExecutor"]["codexStatus"] == "not_requested"
    assert "codex_execution_not_requested" in snapshot["notes"]
    assert snapshot["candidateActions"][1]["requiresApproval"] is True


def test_desktop_self_action_snapshot_handles_missing_state(tmp_path: Path) -> None:
    snapshot = desktop_self_action_snapshot(tmp_path)

    assert snapshot["observed"] is False
    assert snapshot["pendingApprovalCount"] == 0
    assert snapshot["approvalQueue"]["pendingCount"] == 0
    assert snapshot["handoff"]["exists"] is False
    assert snapshot["patchExecutor"]["status"] == ""
    assert "self_action_state_not_observed" in snapshot["notes"]
