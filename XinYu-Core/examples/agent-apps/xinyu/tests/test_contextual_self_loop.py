from __future__ import annotations

import json
from pathlib import Path

from xinyu_contextual_self_loop import (
    build_contextual_self_loop_prompt_block,
    classify_context_scene,
    context_file_policy,
    evaluate_retrieval_pressure,
    run_contextual_self_loop,
)


def test_contextual_self_loop_classifies_memory_review() -> None:
    assert classify_context_scene("人本质上的context很短，但会选择性遗忘和检索") == "memory_review"


def test_contextual_self_loop_classifies_common_chinese_scenes() -> None:
    cases = {
        "\u8fd9\u6bb5\u8bb0\u5fc6\u8981\u4e0d\u8981\u8fdb\u5165\u4e0a\u4e0b\u6587": "memory_review",
        "\u4e3b\u52a8\u6027\u53cd\u9988\u5e94\u8be5\u600e\u4e48\u5f71\u54cd\u4e0b\u4e00\u6b21\u63d0\u9192": "initiative_feedback",
        "\u73b0\u5728\u8fd0\u884c\u72b6\u6001\u548c\u6307\u6807\u600e\u4e48\u6837": "runtime_status",
        "\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u6a21\u5757\u548c\u6d4b\u8bd5": "project_work",
        "\u63a5\u5165runtime presence": "project_work",
        "\u6211\u4eca\u5929\u6709\u70b9\u96be\u53d7\uff0c\u60f3\u8ba9\u4f60\u966a\u6211\u4e00\u4e0b": "emotional_relation",
    }

    for text, expected in cases.items():
        assert classify_context_scene(text) == expected


def test_contextual_self_loop_writes_state_and_trace(tmp_path: Path) -> None:
    result = run_contextual_self_loop(
        tmp_path,
        user_text="把这个地基实现并接入测试",
        trigger="test",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    state = (tmp_path / "memory/context/contextual_self_loop_state.md").read_text(encoding="utf-8")
    trace_lines = (tmp_path / "runtime/contextual_self_loop_trace.jsonl").read_text(encoding="utf-8").splitlines()
    event = json.loads(trace_lines[-1])

    assert result["current_scene"] == "project_work"
    assert result["working_self"] == "quiet_project_partner"
    assert "current_scene: project_work" in state
    assert "short_context_first: true" in state
    assert event["current_scene"] == "project_work"
    assert event["user_text_hash"]
    assert "把这个地基实现" not in json.dumps(event, ensure_ascii=False)


def test_contextual_self_loop_keeps_scene_separate_from_retrieval_pressure(tmp_path: Path) -> None:
    text = "\u4e3a\u4ec0\u4e48\u8fd9\u4e2a\u8981\u6839\u636e\u524d\u9762\u7684\u5bf9\u8bdd\uff1f"
    pressure, signals = evaluate_retrieval_pressure(text)
    result = run_contextual_self_loop(
        tmp_path,
        user_text=text,
        trigger="test",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )
    state = (tmp_path / "memory/context/contextual_self_loop_state.md").read_text(encoding="utf-8")
    event = json.loads((tmp_path / "runtime/contextual_self_loop_trace.jsonl").read_text(encoding="utf-8").splitlines()[-1])

    assert pressure == "high"
    assert "evidence_question" in signals
    assert result["current_scene"] == "casual_chat"
    assert result["retrieval_pressure"] == "high"
    assert "long_history_evidence" in result["retrieval_intents"]
    assert "retrieval_pressure: high" in state
    assert event["retrieval_pressure"] == "high"


def test_contextual_self_loop_detects_isolated_person_fact_pressure() -> None:
    pressure, signals = evaluate_retrieval_pressure("What is Akane studying?")
    noisy_pressure, noisy_signals = evaluate_retrieval_pressure("WWhat will Akane do in Cambodia?")
    lowercase_pressure, lowercase_signals = evaluate_retrieval_pressure(
        "do you think English songs help me? i think it is good for listening"
    )
    profile_pressure, profile_signals = evaluate_retrieval_pressure(
        "Chris is quite innocent, shy, cheerful, and has a heart of gold. He also seems soulful."
    )

    assert pressure == "medium"
    assert "isolated_person_fact_query" in signals
    assert noisy_pressure == "medium"
    assert "isolated_person_fact_query" in noisy_signals
    assert lowercase_pressure in {"none", "low"}
    assert "isolated_person_fact_query" not in lowercase_signals
    assert profile_pressure == "none"
    assert "isolated_person_fact_query" not in profile_signals


def test_contextual_self_loop_prompt_is_hidden_orchestration(tmp_path: Path) -> None:
    block = build_contextual_self_loop_prompt_block(
        tmp_path,
        user_text="最近的主动反馈要怎么影响下一次打扰？",
        trigger="test",
        evaluated_at="2026-05-13T03:00:00+08:00",
    )

    assert "Contextual Self Loop" in block
    assert "current_scene: initiative_feedback" in block
    assert "visibility_rule:" in block
    assert "initiative_metrics" in block


def test_context_file_policy_suppresses_unrelated_layers() -> None:
    casual = context_file_policy(
        "casual_chat",
        rel_path="memory/context/runtime_self_presence.md",
        layer="runtime_presence",
        default_limit=1200,
    )
    initiative = context_file_policy(
        "initiative_feedback",
        rel_path="memory/context/initiative_lifecycle_state.md",
        layer="initiative_lifecycle",
        default_limit=1200,
    )

    assert casual["include"] is False
    assert casual["reason"] == "suppressed_for_casual_chat"
    assert initiative["include"] is True
    assert initiative["limit"] > 0
