from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import list_memory_candidates
from xinyu_learning_closed_loop import build_learning_closed_loop_prompt_block, record_learning_closed_loop_turn
from xinyu_memory_candidate_extractor import extract_memory_candidates
from xinyu_post_reply_self_observation import observe_post_reply_self_observation


OWNER_PRIVATE = {
    "message_type": "private_text",
    "session_id": "qq:private:owner",
    "metadata": {"is_owner_user": True},
}


def test_post_reply_observation_records_hidden_self_state_mechanical_risk(tmp_path: Path) -> None:
    observation = observe_post_reply_self_observation(
        tmp_path,
        OWNER_PRIVATE,
        user_text="你现在感觉怎么样",
        reply="后台队列刚处理完，我会继续优化。",
        final_guard_flags=[],
        quality_flags=[],
        recalled_context="owner_relation pressure exists",
        observed_at="2026-05-23T01:00:00+08:00",
    )

    trace_text = (tmp_path / "runtime/post_reply_self_observation_trace.jsonl").read_text(encoding="utf-8")
    trace_rows = [json.loads(line) for line in trace_text.splitlines()]
    state = (tmp_path / "memory/self/expression_self_learning_state.md").read_text(encoding="utf-8")

    assert observation["recorded"] is True
    assert observation["scores"]["mechanical_risk"] == "high"
    assert observation["scores"]["template_risk"] == "high"
    assert "post_reply_mechanical_risk" in observation["notes"]
    assert "post_reply_missed_self_state_grounding" in observation["notes"]
    assert trace_rows[0]["raw_text_saved"] is False
    assert "你现在感觉怎么样" not in trace_text
    assert "Latest Post Reply Observation" in state
    assert "stable_personality_write: no" in state


def test_post_reply_observation_allows_explicit_technical_diagnostic(tmp_path: Path) -> None:
    observation = observe_post_reply_self_observation(
        tmp_path,
        OWNER_PRIVATE,
        user_text="你现在状态如何，看下后台日志",
        reply="后台日志看起来正常，core 和 gateway 都在。",
        observed_at="2026-05-23T01:01:00+08:00",
    )

    assert observation["technical_exception"] is True
    assert observation["scores"]["mechanical_risk"] == "low"
    assert "post_reply_technical_exception" in observation["notes"]
    assert "post_reply_mechanical_risk" not in observation["notes"]


def test_post_reply_observation_feeds_learning_closed_loop_as_hidden_signal(tmp_path: Path) -> None:
    observation = observe_post_reply_self_observation(
        tmp_path,
        OWNER_PRIVATE,
        user_text="你现在什么状态",
        reply="我理解你的感受，我会继续优化这个体验。",
        observed_at="2026-05-23T01:02:00+08:00",
    )

    result = record_learning_closed_loop_turn(
        tmp_path,
        OWNER_PRIVATE,
        user_text="你现在什么状态",
        reply="我理解你的感受，我会继续优化这个体验。",
        session_key="qq:private:owner",
        visible_turn_kind="ordinary_owner_chat",
        quality_flags=observation["notes"],
        observed_at="2026-05-23T01:02:01+08:00",
    )
    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")
    prompt = build_learning_closed_loop_prompt_block(tmp_path, user_text="你现在感觉怎么样")

    assert result["recorded"] is True
    assert result["failures"][0] == "post_reply_template_voice_risk"
    assert "latest_failure_kind: post_reply_template_voice_risk" in state
    assert "stable personality" not in prompt.lower()
    assert "expected_next_behavior" in prompt


def _successful_observation(root: Path, *, observed_at: str) -> dict[str, object]:
    return observe_post_reply_self_observation(
        root,
        OWNER_PRIVATE,
        user_text="你现在感觉怎么样",
        reply="我刚才有点绷住了，现在想先贴近你一点。",
        observed_at=observed_at,
    )


def test_post_reply_growth_candidate_requires_repeated_success_and_owner_positive_feedback(tmp_path: Path) -> None:
    _successful_observation(tmp_path, observed_at="2026-05-23T01:03:00+08:00")
    observation = _successful_observation(tmp_path, observed_at="2026-05-23T01:04:00+08:00")

    result = extract_memory_candidates(
        tmp_path,
        OWNER_PRIVATE,
        user_text="这次好多了，保持这样",
        assistant_reply="我会记住这个方向，但先不把它写死。",
        source_message_ids=[101],
        post_reply_observation=observation,
    )
    candidates = list_memory_candidates(tmp_path, status="pending", limit=5)
    growth = [row for row in candidates if row["candidate_type"] == "post_reply_growth_candidate"]

    assert result["candidate_count"] == 1
    assert len(growth) == 1
    assert growth[0]["target_gate"] == "personality_growth_review"
    assert growth[0]["target_memory_layer"] == "memory/reflection/growth_log.md"
    assert growth[0]["provenance"]["promotion_requires_review"] is True
    assert growth[0]["provenance"]["stable_memory_write_allowed"] is False
    assert "stable_write_allowed=false" in growth[0]["review_notes"]
    assert "这次好多了" not in growth[0]["candidate_text"]
    assert "我会记住这个方向" not in growth[0]["candidate_text"]
    assert "raw owner/reply text intentionally omitted" in growth[0]["candidate_text"]


def test_post_reply_growth_candidate_not_created_for_single_or_risky_observation(tmp_path: Path) -> None:
    single = _successful_observation(tmp_path, observed_at="2026-05-23T01:05:00+08:00")
    single_result = extract_memory_candidates(
        tmp_path,
        OWNER_PRIVATE,
        user_text="这次好多了",
        assistant_reply="嗯。",
        source_message_ids=[201],
        post_reply_observation=single,
    )
    risky = observe_post_reply_self_observation(
        tmp_path,
        OWNER_PRIVATE,
        user_text="你现在感觉怎么样",
        reply="后台队列已经恢复，我会继续优化。",
        observed_at="2026-05-23T01:06:00+08:00",
    )
    risky_result = extract_memory_candidates(
        tmp_path,
        OWNER_PRIVATE,
        user_text="这次好多了",
        assistant_reply="嗯。",
        source_message_ids=[202],
        post_reply_observation=risky,
    )

    assert single_result["candidate_count"] == 0
    assert risky_result["candidate_count"] == 0
    assert list_memory_candidates(tmp_path, status="pending", limit=5) == []
