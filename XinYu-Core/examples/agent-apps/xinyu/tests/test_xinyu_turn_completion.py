from __future__ import annotations

from xinyu_turn_completion import (
    STATE_COLLECTING_SEGMENTS,
    STATE_READY_TO_REPLY,
    STATE_WAITING_THOUGHT,
    evaluate_turn_completion,
)


def test_explicit_hold_waits_without_generation() -> None:
    decision = evaluate_turn_completion(["\u7b49\u4e0b\uff0c\u6211\u7ec4\u7ec7\u4e0b"])

    assert decision.state == STATE_WAITING_THOUGHT
    assert decision.reason == "explicit_hold"
    assert decision.wait_seconds == 90.0
    assert decision.should_generate is False


def test_continuation_waits_for_more_segments() -> None:
    decision = evaluate_turn_completion(["\u4e0d\u662f\uff0c\u6211\u7684\u610f\u601d\u662f\u8981\u770b\u540e\u9762\u8865\u5145"])

    assert decision.state == STATE_COLLECTING_SEGMENTS
    assert decision.reason == "continuation_marker"
    assert decision.wait_seconds == 25.0
    assert decision.should_generate is True


def test_handoff_or_complete_request_replies_quickly() -> None:
    handoff = evaluate_turn_completion(["\u4f60\u8bf4\u5427"])
    request = evaluate_turn_completion(["\u5e2e\u6211\u4fee\u590d\u4e00\u4e0b"])
    question = evaluate_turn_completion(["\u90a3deepseekv4\u5462"])

    assert handoff.state == STATE_READY_TO_REPLY
    assert handoff.wait_seconds == 3.0
    assert request.reason == "complete_request"
    assert request.should_generate is True
    assert question.reason == "complete_request"
    assert question.should_generate is True


def test_short_fragment_gets_human_sized_pause() -> None:
    decision = evaluate_turn_completion(["\u6bd4\u5982"])

    assert decision.state == STATE_COLLECTING_SEGMENTS
    assert decision.reason == "short_fragment"
    assert decision.wait_seconds == 15.0
    assert decision.should_generate is True


def test_short_confirmation_waits_without_generation() -> None:
    decision = evaluate_turn_completion(["\u5bf9\u7684"])

    assert decision.state == STATE_WAITING_THOUGHT
    assert decision.reason == "low_info_ack"
    assert decision.should_generate is False


def test_hold_with_task_is_treated_as_actionable() -> None:
    decision = evaluate_turn_completion(["\u7b49\u4e0b\uff0c\u5e2e\u6211\u6539\u8fd9\u4e2a"])

    assert decision.state == STATE_READY_TO_REPLY
    assert decision.reason == "complete_request"
    assert decision.should_generate is True
