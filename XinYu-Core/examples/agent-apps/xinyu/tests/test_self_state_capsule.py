from __future__ import annotations

from types import SimpleNamespace

from xinyu_self_state_capsule import STATE_REL
from xinyu_self_state_capsule import build_self_state_capsule
from xinyu_self_state_capsule import build_self_state_capsule_prompt_block
from xinyu_self_state_capsule import classify_self_state_query


OWNER_PRIVATE = {
    "message_type": "private_text",
    "session_id": "qq:private:owner",
    "metadata": {"is_owner_user": True},
}


def test_classifies_owner_state_feeling_thought_and_delay_queries() -> None:
    assert classify_self_state_query("\u4f60\u73b0\u5728\u611f\u89c9\u600e\u4e48\u6837") == "feeling_inquiry"
    assert classify_self_state_query("\u4f60\u5728\u60f3\u4ec0\u4e48") == "thought_inquiry"
    assert classify_self_state_query("\u600e\u4e48\u4e0d\u56de") == "delay_or_no_reply"
    assert classify_self_state_query("\u4f60\u73b0\u5728\u4ec0\u4e48\u72b6\u6001") == "state_inquiry"
    assert classify_self_state_query("\u7ee7\u7eed\u505a\u540e\u9762\u7684\u4efb\u52a1") == "none"


def test_builds_hidden_capsule_without_raw_user_text(tmp_path) -> None:
    (tmp_path / "memory/self").mkdir(parents=True)
    (tmp_path / "memory/context").mkdir(parents=True)
    (tmp_path / "memory/self/learning_closed_loop_state.md").write_text(
        "- status: trial_active\n- latest_failure_kind: owner_reported_template_voice_failure\n",
        encoding="utf-8",
    )
    raw_user_text = "\u4f60\u73b0\u5728\u611f\u89c9\u600e\u4e48\u6837"

    block = build_self_state_capsule_prompt_block(
        tmp_path,
        OWNER_PRIVATE,
        user_text=raw_user_text,
        recalled_context="relationship memory exists",
        write_state=True,
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert "self state capsule sidecar:" in block
    assert "query_kind: feeling_inquiry" in block
    assert "present first-person state" in block
    assert "not as a service status" in block
    assert raw_user_text not in block
    assert raw_user_text not in state
    assert "- raw_user_text_saved: false" in state
    assert "- memory_basis: recalled_context,learning_closed_loop" in state


def test_non_owner_and_irrelevant_owner_turns_do_not_activate(tmp_path) -> None:
    non_owner = build_self_state_capsule(
        tmp_path,
        {"message_type": "private_text", "metadata": {"is_owner_user": False}},
        user_text="\u4f60\u73b0\u5728\u611f\u89c9\u600e\u4e48\u6837",
    )
    ordinary = build_self_state_capsule(
        tmp_path,
        OWNER_PRIVATE,
        user_text="\u7ee7\u7eed\u505a\u540e\u9762\u7684\u4efb\u52a1",
    )

    assert non_owner.active is False
    assert ordinary.active is False


def test_style_pressure_activates_even_without_direct_state_question(tmp_path) -> None:
    capsule = build_self_state_capsule(
        tmp_path,
        OWNER_PRIVATE,
        user_text="\u4f60\u8fd9\u53c8\u50cf\u6a21\u677f",
        visible_turn=SimpleNamespace(owner_style_pressure=True),
    )

    assert capsule.active is True
    assert capsule.query_kind == "style_pressure_self_state"
    assert capsule.posture == "close_to_current_exchange_no_self_report"
