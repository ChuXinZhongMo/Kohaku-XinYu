from __future__ import annotations

import json
from pathlib import Path

from xinyu_action_feedback_coverage import (
    build_action_feedback_coverage_report,
    render_action_feedback_coverage_report,
    write_action_feedback_coverage,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _seed_qq_ack(root: Path) -> None:
    _write(
        root / "memory/context/action_feedback_state.md",
        """
        - status: active
        - checked_at: 2026-05-27T14:40:21+08:00
        - event_id: actfb-test
        - feedback_signal: qq_visible_reply_ack
        - feedback_source: internal_message_ack
        - action_result: delivered
        - route: chat
        - target_kind: private
        - future_effect: confirm_visible_reply_transport_for_next_turn
        - scoring_effect: keep_current_route_available
        - memory_effect: sent_reply_index_updated
        - raw_private_body_retained: false
        - visible_reply_text_retained: false
        """,
    )


def test_coverage_passes_with_qq_ack_and_codex_finished(tmp_path: Path) -> None:
    _seed_qq_ack(tmp_path)
    _write_json(
        tmp_path / "runtime/codex_presence_state.json",
        {
            "updated_at": "2026-05-27T14:41:00+08:00",
            "status": "finished",
            "job_id": "codex-job-1",
            "exit_code": 0,
            "timed_out": False,
        },
    )

    report = build_action_feedback_coverage_report(tmp_path, generated_at="2026-05-27T14:42:00+08:00")

    assert report["status"] == "pass"
    assert report["metrics"]["observed_surface_count"] == 2
    assert report["metrics"]["non_qq_surface_count"] == 1
    assert report["surfaces"]["codex"]["feedback_signal"] == "codex_delegate_finished"
    assert report["surfaces"]["codex"]["lifecycle_status"] == "succeeded"
    assert report["surfaces"]["qq"]["surface_status"] == "observed"
    assert report["surfaces"]["qq"]["lifecycle_status"] == "acked"


def test_coverage_reads_desktop_feedback_without_private_text(tmp_path: Path) -> None:
    raw_private = "RAW_DESKTOP_OWNER_TEXT_SHOULD_NOT_SURFACE_4471"
    _write(
        tmp_path / "memory/context/proactive_request_state.md",
        f"""
        - request_id: proreq-1
        - created_at: 2026-05-27T15:00:00+08:00
        - status: active
        - requested_action: owner_answer
        - request_answer_state: read_locally
        - last_ack_status: acked
        - adapter_error: none
        - concrete_question: {raw_private}
        """,
    )

    report = build_action_feedback_coverage_report(tmp_path, generated_at="2026-05-27T15:01:00+08:00")
    output = render_action_feedback_coverage_report(report)
    write_action_feedback_coverage(tmp_path, report)
    state = (tmp_path / "memory/context/action_feedback_coverage_state.md").read_text(encoding="utf-8")
    trace = (tmp_path / "runtime/action_feedback_coverage_trace.jsonl").read_text(encoding="utf-8")

    assert report["surfaces"]["desktop"]["feedback_signal"] == "desktop_read_locally"
    assert report["surfaces"]["desktop"]["lifecycle_status"] == "acked"
    assert "- desktop_lifecycle_status: acked" in state
    assert '"surface_lifecycles"' in trace
    assert raw_private not in output
    assert raw_private not in state
    assert raw_private not in trace


def test_coverage_reads_local_tool_probe_success(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "runtime/self_action_gateway/trace.jsonl",
        [
            {
                "event_kind": "self_action_executed",
                "checked_at": "2026-05-27T15:02:00+08:00",
                "action_id": "selfact-1",
                "action_kind": "local_py_compile_probe",
                "status": "executed",
                "result": "success",
                "error_code": "",
            }
        ],
    )

    report = build_action_feedback_coverage_report(tmp_path)

    assert report["surfaces"]["local_tool"]["feedback_signal"] == "local_tool_probe_succeeded"
    assert report["surfaces"]["local_tool"]["surface_status"] == "observed"
    assert report["surfaces"]["local_tool"]["lifecycle_status"] == "succeeded"
    assert report["metrics"]["non_qq_surface_count"] == 1


def test_coverage_reads_patch_executor_prepared(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/self_action_patch_executor_state.md",
        """
        - checked_at: 2026-05-27T15:03:00+08:00
        - status: prepared
        - execution_level: prepare
        - queue_id: queue-1
        - task_id: patch-task-1
        - codex_status: not_requested
        - task_path: runtime/self_action_patch_executor/tasks/patch-task-1.json
        """,
    )

    report = build_action_feedback_coverage_report(tmp_path)

    assert report["surfaces"]["patch_executor"]["feedback_signal"] == "patch_task_prepared"
    assert report["surfaces"]["patch_executor"]["action_result"] == "prepared"
    assert report["surfaces"]["patch_executor"]["lifecycle_status"] == "prepared"


def test_coverage_marks_code_restart_required_needs_check(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/code_change_awareness_state.md",
        """
        - updated_at: 2026-05-27T15:04:00+08:00
        - status: changed
        - source_changed: true
        - current_project_digest: abc123
        - bridge_restart_required: true
        - runtime_restart_required: false
        - gateway_restart_may_be_needed: false
        """,
    )

    report = build_action_feedback_coverage_report(tmp_path)

    assert report["status"] == "needs_check"
    assert report["metrics"]["failure_count"] == 1
    assert report["surfaces"]["code_probe"]["feedback_signal"] == "code_probe_restart_required"
    assert report["surfaces"]["code_probe"]["lifecycle_status"] == "needs_check"


def test_coverage_runtime_presence_does_not_copy_previews(tmp_path: Path) -> None:
    raw_user = "RAW_RUNTIME_USER_PREVIEW_SHOULD_NOT_SURFACE_8291"
    raw_reply = "RAW_RUNTIME_REPLY_PREVIEW_SHOULD_NOT_SURFACE_8292"
    _write(
        tmp_path / "memory/context/runtime_self_presence.md",
        f"""
        - updated_at: 2026-05-27T15:05:00+08:00
        - bridge_process: running
        - current_turn_state: idle
        - last_turn_id: turn-1
        - last_turn_at: 2026-05-27T15:04:50+08:00
        - last_turn_status: ok
        - last_user_preview: {raw_user}
        - last_reply_preview: {raw_reply}
        """,
    )

    report = build_action_feedback_coverage_report(tmp_path)
    output = render_action_feedback_coverage_report(report)
    write_action_feedback_coverage(tmp_path, report)
    state = (tmp_path / "memory/context/action_feedback_coverage_state.md").read_text(encoding="utf-8")
    trace = (tmp_path / "runtime/action_feedback_coverage_trace.jsonl").read_text(encoding="utf-8")

    assert report["surfaces"]["runtime_probe"]["feedback_signal"] == "runtime_probe_ok"
    assert report["surfaces"]["runtime_probe"]["lifecycle_status"] == "succeeded"
    assert raw_user not in output
    assert raw_reply not in output
    assert raw_user not in state
    assert raw_reply not in state
    assert raw_user not in trace
    assert raw_reply not in trace
