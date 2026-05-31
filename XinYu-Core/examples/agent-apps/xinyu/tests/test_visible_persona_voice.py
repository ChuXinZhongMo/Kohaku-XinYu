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
    direct_question = compose_proactive_visible_message("要不要我先把人格状态卡接到 Desktop？")
    async_reply = compose_async_exploration_outbox_message(
        {"result_quality": "failed", "sanitized_summary": "RuntimeError: boom token=secret", "resume_id": "wait-1"}
    )
    watchdog = compose_watchdog_visible_message("self_code_watchdog_failed", error="RuntimeError: boom")
    for text in (review, review_reply, promise, proactive, direct_question, async_reply, watchdog):
        _assert_persona_visible(text)
    assert direct_question in {
        "Desktop 那张卡还要吗",
        "这个还要吗",
        "Desktop 那张卡还看吗",
    }
    assert "我想问你一件小事" not in direct_question
    loop_question = compose_proactive_visible_message("要不要我现在跑一遍生活事件到主动消息的闭环？")
    wording_question = compose_proactive_visible_message("要不要我先把这些主动消息的句子改得更像平时说话？")
    assert loop_question in {"刚才那条链我接着？", "那我接着？", "刚才那条链继续吗"}
    assert wording_question in {"那几句还要吗", "这个还要吗", "那几句还看吗"}
    assert "我" in review
    assert "我" in promise
    assert "token=secret" not in async_reply


def test_proactive_visible_message_can_use_recent_context_for_topic() -> None:
    reply = compose_proactive_visible_message(
        "要不要继续？",
        recent_context="主人刚说表达层那块怪，想让我先接表达层契约",
    )

    assert reply in {"表现那块我接着？", "那我接着？", "表现那块继续吗"}
    assert "主人" not in reply


def test_proactive_visible_message_drops_control_context_lines() -> None:
    reply = compose_proactive_visible_message(
        "要不要继续？",
        recent_context="request_id: abc\nstatus: ready\n主动消息的句子改得更像平时说话",
    )

    assert reply in {"那几句我接着？", "那我接着？", "那几句继续吗"}
    assert "request_id" not in reply


def test_proactive_visible_message_uses_owner_private_turn_buffer() -> None:
    reply = compose_proactive_visible_message(
        "要不要继续？",
        recent_context=[
            {
                "sessionKind": "qq_group",
                "groupDisplayId": "123",
                "textPreview": "群里说 Desktop 那张卡",
            },
            {
                "sessionKind": "qq_private",
                "isOwner": True,
                "textPreview": "表达层契约这里先接上",
                "replyPreview": "我先看表现那块",
            },
        ],
    )

    assert reply in {"表现那块我接着？", "那我接着？", "表现那块继续吗"}
    assert "群里" not in reply


def test_proactive_visible_message_ignores_non_owner_private_turn_buffer() -> None:
    reply = compose_proactive_visible_message(
        "要不要继续？",
        recent_context=[
            {
                "sessionKind": "qq_group",
                "groupDisplayId": "123",
                "textPreview": "表达层契约这里先接上",
            }
        ],
    )

    assert reply == "要不要继续？"
