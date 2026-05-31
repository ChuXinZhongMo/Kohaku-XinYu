from __future__ import annotations

from pathlib import Path

from xinyu_learning_closed_loop import (
    SUCCESS_MARKERS,
    build_learning_closed_loop_prompt_block,
    record_learning_closed_loop_self_thought,
    record_learning_closed_loop_turn,
)
from xinyu_self_thought_loop import run_self_thought_loop
from xinyu_text_variants import legacy_mojibake_variants, readable_markers


def _owner_payload() -> dict[str, object]:
    return {
        "message_type": "private",
        "user_id": "owner",
        "metadata": {"is_owner_user": True},
    }


def test_closed_loop_records_guard_failure_as_replay_case(tmp_path: Path) -> None:
    result = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="看看现在还缺什么",
        reply="",
        session_key="qq:private:owner",
        visible_turn_kind="ordinary_owner_chat",
        final_guard_flags=["pseudo_tool_call_naturalized", "final_guard_blocked_unsendable_reply"],
        observed_at="2026-05-02T04:00:00+08:00",
    )

    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")
    cases = (tmp_path / "memory/self/learning_closed_loop_cases.md").read_text(encoding="utf-8")
    prompt = build_learning_closed_loop_prompt_block(tmp_path, user_text="看看现在还缺什么")

    assert result["recorded"] is True
    assert result["failures"][0] == "visible_pseudo_tool_leak"
    assert "status: trial_active" in state
    assert "latest_failure_kind: visible_pseudo_tool_leak" in state
    assert "先按当前上下文说下一句人话" in state
    assert "case_type: failure" in cases
    assert "expected_next_behavior" in prompt
    assert "visible_rule" in prompt


def test_closed_loop_turn_feedback_updates_trial_counts(tmp_path: Path) -> None:
    first = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="不是哥们，现在哪像人了，模板味太重",
        reply="嗯，我会继续调整。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:01:00+08:00",
    )
    second = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这句自然多了",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:00+08:00",
    )

    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")

    assert first["failures"][0] == "owner_reported_template_voice_failure"
    assert second["success"] is True
    assert "repair_count: 1" in state
    assert "success_count: 1" in state
    assert "success_streak: 1" in state
    assert "active_trial_key: owner_reported_template_voice_failure" in state
    assert "trial_success_count: 1" in state
    assert "trial_success_streak: 1" in state
    assert "latest_success_trial_key: owner_reported_template_voice_failure" in state
    assert "success_evidence_status: same_trial_explicit_owner_success" in state
    assert "status: trial_supported" in state


def test_readable_markers_keeps_clean_form_first() -> None:
    markers = readable_markers("自然多了")
    # The clean literal stays the first element; legacy mojibake variants are
    # appended for matching, never substituted in.
    assert markers[0] == "自然多了"
    assert len(markers) > 1
    assert SUCCESS_MARKERS[0] == "自然多了"
    assert "自然多了" in SUCCESS_MARKERS


def test_closed_loop_success_matches_legacy_mojibake_feedback(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="不是哥们，现在哪像人了，模板味太重",
        reply="嗯，我会继续调整。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T05:00:00+08:00",
    )
    variants = legacy_mojibake_variants("自然多了")
    assert variants, "expected legacy mojibake variants to exist"
    mojibaked = variants[0]
    assert mojibaked != "自然多了"

    result = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        # Owner praise that arrived through an old wrongly-decoded pipeline must
        # still register as success via the legacy variant matchers.
        user_text=mojibaked,
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T05:01:00+08:00",
    )
    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")

    assert result["success"] is True
    assert "trial_success_streak: 1" in state
    assert "success_evidence_status: same_trial_explicit_owner_success" in state


def test_closed_loop_memory_mechanics_guard_suppresses_concurrent_success(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_supported
- latest_failure_kind: memory_mechanics_leak
- active_trial_key: memory_mechanics_leak
- active_trial_habit: 需要记忆时先接住对话，只说记得/不确定/想确认什么，不念文件和状态卡。
- expected_next_behavior: 需要记忆时先接住对话，只说记得/不确定/想确认什么，不念文件和状态卡。
- repair_count: 5
- success_count: 1
- success_streak: 1
- trial_success_count: 1
- trial_success_streak: 1
- promotion_signal: false
- last_owner_reaction: explicit_success

## Success Evidence
- latest_success_trial_key: memory_mechanics_leak
- success_evidence_status: same_trial_explicit_owner_success
""",
        encoding="utf-8",
    )

    # Same turn: owner praise (clean success marker) AND a memory-mechanics guard
    # failure. The concurrent critical failure must suppress the success.
    result = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这句自然多了",
        reply="（先读一下记忆文件再说）",
        session_key="qq:private:owner",
        final_guard_flags=["visible_memory_mechanics_naturalized"],
        observed_at="2026-05-02T06:00:00+08:00",
    )
    state = state_path.read_text(encoding="utf-8")

    assert result["failures"][0] == "memory_mechanics_leak"
    assert result["success"] is False
    assert "learning_closed_loop_success_suppressed_by_concurrent_failure" in result["notes"]
    assert "trial_success_streak: 0" in state
    assert "success_evidence_status: reset_by_failure" in state
    assert "active_trial_key: memory_mechanics_leak" in state


def test_closed_loop_ignores_loose_time_and_learning_words(tmp_path: Path) -> None:
    time_result = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="今天有点累，先慢一点",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:30+08:00",
    )
    learning_result = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这个做不到吗",
        reply="我再看看。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:40+08:00",
    )

    assert time_result["recorded"] is False
    assert learning_result["recorded"] is False


def test_closed_loop_success_feedback_requires_active_trial_context(tmp_path: Path) -> None:
    unrelated = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="好多了",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:50+08:00",
    )
    first = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="不要模板话",
        reply="我会调整。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:55+08:00",
    )
    vague = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="身体好多了",
        reply="那就好。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:56+08:00",
    )
    bound = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这句好多了",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:57+08:00",
    )

    assert unrelated["recorded"] is False
    assert first["failures"] == ["owner_reported_template_voice_failure"]
    assert vague["recorded"] is False
    assert bound["success"] is True


def test_closed_loop_success_evidence_resets_when_trial_key_changes(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="不要模板话",
        reply="我会调整。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:57+08:00",
    )
    first_success = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这句自然多了",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:58+08:00",
    )
    second_success = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这样可以",
        reply="好。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:59+08:00",
    )

    supported = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")

    assert first_success["success"] is True
    assert second_success["success"] is True
    assert "trial_success_count: 2" in supported
    assert "trial_success_streak: 2" in supported
    assert "latest_success_trial_key: owner_reported_template_voice_failure" in supported
    assert "success_evidence_status: same_trial_explicit_owner_success" in supported
    assert "promotion_signal: possible_after_self_review" in supported

    changed = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="上下文不连通，怎么聊下去",
        reply="",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:03:00+08:00",
    )

    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")

    assert changed["failures"] == ["owner_reported_context_discontinuity"]
    assert "active_trial_key: owner_reported_context_discontinuity" in state
    assert "trial_success_count: 0" in state
    assert "trial_success_streak: 0" in state
    assert "success_evidence_status: reset_by_failure" in state
    assert "promotion_signal: false" in state


def test_closed_loop_treats_resolved_template_feedback_as_same_trial_success(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="不要模板话",
        reply="我会调整。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:03:01+08:00",
    )
    resolved = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这次没模板味了",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:03:02+08:00",
    )
    effective = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这次修复有效",
        reply="好。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:03:03+08:00",
    )

    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")

    assert resolved["success"] is True
    assert resolved["failures"] == []
    assert effective["success"] is True
    assert "trial_success_count: 2" in state
    assert "trial_success_streak: 2" in state
    assert "latest_success_trial_key: owner_reported_template_voice_failure" in state
    assert "promotion_signal: possible_after_self_review" in state


def test_closed_loop_keeps_mixed_template_feedback_as_failure(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="不要模板话",
        reply="我会调整。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:03:04+08:00",
    )
    mixed = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="这句自然多了，但是还是有模板味",
        reply="嗯。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:03:05+08:00",
    )

    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")

    assert mixed["success"] is False
    assert mixed["failures"] == ["owner_reported_template_voice_failure"]
    assert "learning_closed_loop_success_suppressed_by_concurrent_failure" in mixed["notes"]
    assert "trial_success_streak: 0" in state
    assert "success_evidence_status: reset_by_failure" in state


def test_closed_loop_dedupes_replay_cases(tmp_path: Path) -> None:
    first = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="上下文不连通，怎么聊下去",
        reply="",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:58+08:00",
    )
    second = record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="上下文不连通，怎么聊下去",
        reply="",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:02:59+08:00",
    )

    cases = (tmp_path / "memory/self/learning_closed_loop_cases.md").read_text(encoding="utf-8")

    assert len(first["case_ids"]) == 1
    assert second["case_ids"] == []
    assert "learning_closed_loop_case_deduped" in second["notes"]
    assert cases.count("case_type: failure") == 1


def test_prompt_block_stays_off_for_unrelated_live_turns(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="不要模板话",
        reply="我会调整。",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:03:00+08:00",
    )

    unrelated = build_learning_closed_loop_prompt_block(tmp_path, user_text="今天吃什么")
    relevant = build_learning_closed_loop_prompt_block(tmp_path, user_text="这句还是模板")

    assert unrelated == ""
    assert "owner_reported_template_voice_failure" in relevant


def test_prompt_block_cools_down_repeated_context_repairs(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """---
title: Learning Closed Loop State
memory_type: learning_closed_loop_state
---

# Learning Closed Loop State

## Current Loop
- status: trial_active
- latest_failure_kind: owner_reported_context_discontinuity
- active_trial_habit: answer from recent real context first
- expected_next_behavior: connect to the latest real turn before explaining
- repair_count: 12
- success_count: 0
- success_streak: 0
""",
        encoding="utf-8",
    )

    soft_callback = build_learning_closed_loop_prompt_block(tmp_path, user_text="刚才那个呢")
    direct_repair = build_learning_closed_loop_prompt_block(tmp_path, user_text="上下文不连贯，没接住")

    assert soft_callback == ""
    assert "owner_reported_context_discontinuity" in direct_repair
    assert "realtime_pressure_limit: direct_failure_only" in direct_repair


def test_prompt_block_cools_context_pressure_despite_old_global_successes(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_active
- latest_failure_kind: owner_reported_context_discontinuity
- active_trial_habit: answer from recent real context first
- expected_next_behavior: connect to the latest real turn before explaining
- repair_count: 94
- success_count: 3
- success_streak: 0
- trial_success_count: 3
- trial_success_streak: 0
- success_evidence_status: none
""",
        encoding="utf-8",
    )

    soft_callback = build_learning_closed_loop_prompt_block(tmp_path, user_text="刚才那个呢")
    direct_repair = build_learning_closed_loop_prompt_block(tmp_path, user_text="上下文不连贯，没接住")

    assert soft_callback == ""
    assert "owner_reported_context_discontinuity" in direct_repair
    assert "realtime_pressure_limit: direct_failure_only" in direct_repair


def test_prompt_block_keeps_low_information_ack_canary_under_high_repair_count(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """# Learning Closed Loop State

## Current Loop
- status: trial_active
- latest_failure_kind: post_reply_low_information_ack_risk
- active_trial_habit: do not answer a live owner probe with a bare ack
- expected_next_behavior: anchor one concrete point from the current owner turn
- repair_count: 94
- success_count: 3
- success_streak: 0
- trial_success_count: 3
- trial_success_streak: 0
- success_evidence_status: none
""",
        encoding="utf-8",
    )

    prompt = build_learning_closed_loop_prompt_block(tmp_path, user_text="所以现在怎么做")

    assert "post_reply_low_information_ack_risk" in prompt
    assert "realtime_pressure_limit" not in prompt


def test_closed_loop_links_self_thought_to_memory_route(tmp_path: Path) -> None:
    result = record_learning_closed_loop_self_thought(
        tmp_path,
        thought={
            "focus_kind": "dream_residue",
            "outcome": "request_candidate",
            "candidate_enabled": True,
            "research_needed": False,
        },
        request={"status": "ready", "kind": "dream_share"},
        observed_at="2026-05-02T04:03:00+08:00",
    )

    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")

    assert result["recorded"] is True
    assert result["route"] == "self_thought_to_proactive_request_memory"
    assert "last_self_thought_focus: dream_residue" in state
    assert "self_thought_memory_route: self_thought_to_proactive_request_memory" in state


def test_self_thought_can_focus_on_active_closed_loop_trial(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="上下文不连通，怎么聊下去",
        reply="",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:04:00+08:00",
    )

    result = run_self_thought_loop(
        tmp_path,
        checked_at="2026-05-02T04:05:00+08:00",
        trigger="test",
        force=True,
    )

    assert result["focus_kind"] == "learning_closed_loop"
    assert result["outcome"] == "queue_reflection"


def test_self_thought_does_not_refocus_same_closed_loop_trial(tmp_path: Path) -> None:
    record_learning_closed_loop_turn(
        tmp_path,
        _owner_payload(),
        user_text="上下文不连通，怎么聊下去",
        reply="",
        session_key="qq:private:owner",
        observed_at="2026-05-02T04:04:00+08:00",
    )
    first = run_self_thought_loop(
        tmp_path,
        checked_at="2026-05-02T04:05:00+08:00",
        trigger="test",
        force=True,
    )
    record_learning_closed_loop_self_thought(
        tmp_path,
        thought={
            "focus_kind": first["focus_kind"],
            "outcome": first["outcome"],
            "candidate_enabled": False,
            "research_needed": False,
        },
        request={"status": "none"},
        observed_at="2026-05-02T04:05:01+08:00",
    )
    record_learning_closed_loop_self_thought(
        tmp_path,
        thought={
            "focus_kind": "dream_residue",
            "outcome": "request_candidate",
            "candidate_enabled": True,
            "research_needed": False,
        },
        request={"status": "ready"},
        observed_at="2026-05-02T04:05:30+08:00",
    )

    second = run_self_thought_loop(
        tmp_path,
        checked_at="2026-05-02T04:06:00+08:00",
        trigger="test",
        force=True,
    )

    assert first["focus_kind"] == "learning_closed_loop"
    assert second["focus_kind"] != "learning_closed_loop"
    assert "learning_closed_loop_already_reflected" in second["notes"]
    state = (tmp_path / "memory/self/learning_closed_loop_state.md").read_text(encoding="utf-8")
    assert "last_self_thought_focus: dream_residue" in state
    assert "last_learning_loop_reflected_failure: owner_reported_context_discontinuity" in state


def test_self_thought_codex_running_does_not_starve_shareable_dream(tmp_path: Path) -> None:
    (tmp_path / "runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/codex_presence_state.json").write_text(
        '{"status":"running","job_id":"codex-smoke","timed_out":false}\n',
        encoding="utf-8",
    )
    (tmp_path / "memory/context/thought_seeds.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory/context/thought_seeds.md").write_text(
        """# Thought Seeds

## Latest Dream
- latest_dream_id: dream-2026-05-02-auto
- latest_fragments: 走廊尽头有一间教室，灯亮着但没有人说话
- reality_boundary: 这只是梦，不是现实新发生的事
""",
        encoding="utf-8",
    )

    result = run_self_thought_loop(
        tmp_path,
        checked_at="2026-05-02T04:07:00+08:00",
        trigger="test",
        force=True,
    )

    assert result["focus_kind"] == "dream_residue"
    assert result["intention"] == "share_dream"
    assert "codex_running_observed" in result["notes"]
    state = (tmp_path / "memory/context/self_thought_state.md").read_text(encoding="utf-8")
    concrete_question = next(line for line in state.splitlines() if line.startswith("- concrete_question: "))
    assert "我知道这只是梦" not in concrete_question
    assert "不是现实新发生的事" not in concrete_question
    assert "梦" in concrete_question


def test_self_thought_reflection_share_humanizes_internal_architecture_label(tmp_path: Path) -> None:
    (tmp_path / "memory/reflection").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory/reflection/reflection_queue.md").write_text(
        """# Reflection Queue

## item-2026-05-02-001
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: owner_feedback
- priority: high
- waking_residue: owner said template voice and context do not connect
- boundary: reflection material only

## item-2026-05-02-002
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: owner_feedback
- priority: medium
- waking_residue: owner said template voice and context do not connect
- boundary: reflection material only

## item-2026-05-02-003
- topic: owner flagged shallow context and mechanical voice as persistent architecture defects
- source: owner_feedback
- priority: medium
- waking_residue: owner said template voice and context do not connect
- boundary: reflection material only
""",
        encoding="utf-8",
    )

    result = run_self_thought_loop(
        tmp_path,
        checked_at="2026-05-02T04:09:00+08:00",
        trigger="test",
        force=True,
    )

    state = (tmp_path / "memory/context/self_thought_state.md").read_text(encoding="utf-8")
    concrete_question = next(line for line in state.splitlines() if line.startswith("- concrete_question: "))

    assert result["focus_kind"] == "reflection_queue"
    assert result["intention"] == "share_reflection"
    assert result["candidate_enabled"] is True
    assert "owner flagged" not in concrete_question
    assert "architecture defects" not in concrete_question
    assert "接不上上下文" in concrete_question
    assert "自查" in concrete_question


def test_self_thought_research_handoff_without_results_does_not_starve_dream(tmp_path: Path) -> None:
    (tmp_path / "memory/knowledge").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory/context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory/knowledge/source_requests.md").write_text(
        """# Source Requests

## request-2026-05-02-003
- question_id: q-006
- target: general
- query: general reliable source
- url: none
- status: pending_url
- followup_kind: source_diversity
""",
        encoding="utf-8",
    )
    (tmp_path / "memory/context/research_handoff_state.md").write_text(
        """# Research Handoff State

## Last Evaluation
- evaluated_at: 2026-05-02T04:00:00+08:00
- status: activation_ready
- provider_results: 0
- codex_status: none

## Handoff
- source_request_id: request-2026-05-02-003
""",
        encoding="utf-8",
    )
    (tmp_path / "memory/context/thought_seeds.md").write_text(
        """# Thought Seeds

## Latest Dream
- latest_dream_id: dream-2026-05-02-auto
- latest_fragments: 有一间教室，灯亮着但没有人说话
- reality_boundary: 这只是梦，不是现实新发生的事
""",
        encoding="utf-8",
    )

    result = run_self_thought_loop(
        tmp_path,
        checked_at="2026-05-02T04:10:00+08:00",
        trigger="test",
        force=True,
    )

    assert result["focus_kind"] == "dream_residue"
    assert result["intention"] == "share_dream"
    assert "research_handoff_recent_no_result_request-2026-05-02-003" in result["notes"]
