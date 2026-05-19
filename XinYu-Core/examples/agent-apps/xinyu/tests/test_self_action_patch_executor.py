from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from xinyu_self_action_gateway import APPROVAL_HANDOFF_REL, decide_self_action_approval, run_self_action_gateway
from xinyu_self_action_patch_executor import (
    STATE_JSON_REL,
    STATE_MD_REL,
    TASK_MD_REL,
    TRACE_REL,
    run_self_action_patch_executor,
)
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_approved_handoff(root: Path) -> None:
    _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'goal'\n")
    _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'observer'\n")
    _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'action'\n")
    _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(root, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    run_self_action_gateway(root, checked_at="2026-05-16T10:01:00+08:00", trigger="test")
    decide_self_action_approval(
        root,
        queue_id="latest",
        decision="approved",
        decided_at="2026-05-16T10:02:00+08:00",
        execute=True,
    )


def test_prepare_turns_approved_handoff_into_patch_task(tmp_path: Path) -> None:
    _seed_approved_handoff(tmp_path)

    result = run_self_action_patch_executor(
        tmp_path,
        checked_at="2026-05-16T10:03:00+08:00",
        execution_level="prepare",
    )

    state = json.loads((tmp_path / STATE_JSON_REL).read_text(encoding="utf-8"))
    state_text = (tmp_path / STATE_MD_REL).read_text(encoding="utf-8")
    task_text = (tmp_path / TASK_MD_REL).read_text(encoding="utf-8")
    trace = _read_jsonl(tmp_path / TRACE_REL)

    assert (tmp_path / APPROVAL_HANDOFF_REL).exists()
    assert result["status"] == "prepared"
    assert result["codex"]["status"] == "not_requested"
    assert result["task_id"].startswith("selfaction-patch-")
    assert state["last_codex_status"] == "not_requested"
    assert "execute_codex_mode" in state_text
    assert "Owner-approved Self Action Gateway patch executor task" in task_text
    assert "Self-code implementation mode:" in task_text
    assert "do not reduce it to research-only output" in task_text
    assert "dirty file conflict or running Codex job blocks the patch" in task_text
    assert "stable_memory_write: blocked" in task_text
    assert any(row.get("event_kind") == "self_action_patch_executor_run" for row in trace)


def test_execute_codex_uses_watchdog_and_owner_write_approved_payload(tmp_path: Path, monkeypatch) -> None:
    _seed_approved_handoff(tmp_path)
    seen: dict[str, object] = {}

    def fake_run_codex_delegate(root: Path, payload: dict[str, object]) -> SimpleNamespace:
        seen["root"] = root
        seen["payload"] = payload
        metadata = payload.get("metadata")
        assert isinstance(metadata, dict)
        assert metadata["owner_local_write_approved"] is True
        assert metadata["self_action_patch_executor"] is True
        assert "Self-code watchdog:" in str(payload.get("text"))
        return SimpleNamespace(
            accepted=True,
            timed_out=False,
            exit_code=0,
            reply="done",
            request_path="runtime/codex_delegate/requests/test.json",
            workspace_path="runtime/codex_delegate/workspaces/test",
            report_path="runtime/codex_delegate/outbox/test-report.md",
            last_message_path="runtime/codex_delegate/workspaces/test/last.txt",
            notes=["fake_codex"],
        )

    monkeypatch.setattr("xinyu_self_action_patch_executor.run_codex_delegate", fake_run_codex_delegate)

    result = run_self_action_patch_executor(
        tmp_path,
        checked_at="2026-05-16T10:03:00+08:00",
        execution_level="execute_codex",
        allow_codex=True,
    )

    task_text = (tmp_path / TASK_MD_REL).read_text(encoding="utf-8")
    state = json.loads((tmp_path / STATE_JSON_REL).read_text(encoding="utf-8"))

    assert result["status"] == "codex_completed"
    assert result["codex"]["status"] == "finished"
    assert result["watchdog"]["ok"] is True
    assert result["watchdog"]["manifest_path"]
    assert "snapshot_manifest:" in task_text
    assert state["last_codex_status"] == "finished"
    assert seen["root"] == tmp_path


def test_non_code_handoff_reports_clear_block_reason(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/self_action_gateway_execution_handoff.md",
        """
        # Self Action Gateway Execution Handoff

        ## Approved Action
        - queue_id: selfaction-approval-memory
        - approval_id: selfaction-decision-memory
        - goal_id: absorb_feedback_repair
        - action_kind: stable_memory_change_request
        - approval_scope: stable_memory_or_voice_repair
        - execution_mode: stable_memory_review_ticket
        """,
    )

    result = run_self_action_patch_executor(
        tmp_path,
        checked_at="2026-05-16T10:04:00+08:00",
        execution_level="prepare",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "handoff_not_patch_action"
    assert result["action_kind"] == "stable_memory_change_request"


def test_patch_handoff_requires_code_patch_approval_scope(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/self_action_gateway_execution_handoff.md",
        """
        # Self Action Gateway Execution Handoff

        ## Approved Action
        - queue_id: selfaction-approval-wrong-scope
        - approval_id: selfaction-decision-wrong-scope
        - goal_id: continue_bounded_work
        - action_kind: self_code_patch_request
        - approval_scope: stable_memory_or_voice_repair
        - execution_mode: codex_handoff_ticket
        """,
    )

    result = run_self_action_patch_executor(
        tmp_path,
        checked_at="2026-05-16T10:05:00+08:00",
        execution_level="prepare",
    )

    assert result["status"] == "blocked"
    assert result["reason"] == "handoff_not_code_patch_scope"
    assert result["approval_scope"] == "stable_memory_or_voice_repair"
    assert result["task_path"] == ""
