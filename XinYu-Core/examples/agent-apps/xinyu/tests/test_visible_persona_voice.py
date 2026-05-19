from __future__ import annotations

from types import SimpleNamespace

from xinyu_codex_service import codex_completion_outbox_message, codex_status_reply
from xinyu_visible_persona_voice import (
    compose_async_exploration_outbox_message,
    compose_promise_followup_message,
    compose_proactive_visible_message,
    compose_review_inbox_card,
    compose_review_inbox_command_reply,
    compose_watchdog_visible_message,
)


FORBIDDEN_VISIBLE_MARKERS = (
    "报告名",
    "Outbox",
    "codex-qq-",
    ".md",
    "退出码",
    "Review processed",
    "batch=",
    "resume_id:",
    "queue_id",
    "task_id",
    "Self-code watchdog failed",
)


def _assert_persona_visible(text: str) -> None:
    assert text.strip()
    for marker in FORBIDDEN_VISIBLE_MARKERS:
        assert marker not in text


def test_codex_visible_voice_hides_report_and_exit_metadata(tmp_path) -> None:
    report = tmp_path / "codex-qq-20260507T020900-report.md"
    report.write_text(
        "Request: codex-qq-20260507T020900\n"
        "Owner task: 核查\n"
        "* 这次没有真正的新任务，只是一次误触发。\n",
        encoding="utf-8",
    )
    started = codex_status_reply(
        "done",
        paths={"report_path": str(report), "request_path": str(tmp_path / "codex-qq-20260507T020900.md")},
        auto_study=True,
        exit_code=3221225786,
        task_text="核查当前架构",
    )
    completed = codex_completion_outbox_message(
        tmp_path,
        SimpleNamespace(report_path=str(report), last_message_path="", accepted=True, timed_out=False, exit_code=None),
        text="核查当前架构",
        auto_study=True,
        handoff_notes=[],
    )
    _assert_persona_visible(started)
    _assert_persona_visible(completed)
    assert "我" in started or "我" in completed


def test_control_plane_messages_are_first_person() -> None:
    review = compose_review_inbox_card(
        {
            "items": [
                {"index": 1, "source_kind": "voice", "title": "太像客服", "summary": "需要更短一点"},
            ]
        }
    )
    review_reply = compose_review_inbox_command_reply(processed_count=1, stale_count=0, pending_count=0)
    promise = compose_promise_followup_message({"user_text": "晚上回来汇报"})
    proactive = compose_proactive_visible_message("request_id: x\nlocal action pressure after codex_delegate:none")
    async_reply = compose_async_exploration_outbox_message(
        {"result_quality": "failed", "sanitized_summary": "RuntimeError: boom token=secret", "resume_id": "wait-1"}
    )
    watchdog = compose_watchdog_visible_message("self_code_watchdog_failed", error="RuntimeError: boom")
    for text in (review, review_reply, promise, proactive, async_reply, watchdog):
        _assert_persona_visible(text)
    assert "我" in review
    assert "我" in promise
    assert "token=secret" not in async_reply
