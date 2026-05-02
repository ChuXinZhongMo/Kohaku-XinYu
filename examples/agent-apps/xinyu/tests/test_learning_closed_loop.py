from __future__ import annotations

from pathlib import Path

from xinyu_learning_closed_loop import (
    build_learning_closed_loop_prompt_block,
    record_learning_closed_loop_self_thought,
    record_learning_closed_loop_turn,
)
from xinyu_self_thought_loop import run_self_thought_loop


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
    assert "status: trial_supported" in state


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
    assert "Codex" in concrete_question


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
