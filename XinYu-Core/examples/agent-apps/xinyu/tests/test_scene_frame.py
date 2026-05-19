from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_scene_frame import build_scene_frame  # noqa: E402
from xinyu_scene_frame import render_scene_frame_prompt_block  # noqa: E402


def test_scene_frame_marks_night_shift_low_energy(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u521a\u4e0b\u5b8c\u591c\u73ed\u6709\u70b9\u56f0\uff0c\u8981\u53bb\u7761\u4e00\u89c9",
        evaluated_at="2026-05-19T08:30:00+08:00",
    )

    assert frame.time_context == "after_night_shift"
    assert frame.owner_state == "low_energy_or_tired"
    assert frame.reply_policy == "short_gentle_low_burden"


def test_scene_frame_marks_temporal_recall_from_recall_block(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u521a\u9192\uff0c\u73b0\u5728\u8be5\u600e\u4e48\u56de\uff1f",
        canonical_recall_context=(
            "## Temporal Context\n"
            "- inference: recent_wake_from_nap | sleep_start=12:30 wake=13:30\n"
            "\n"
            "## Recalled Context\n"
            "- source: dialogue_tail\n"
        ),
    )
    rendered = render_scene_frame_prompt_block(frame)

    assert frame.time_context == "recent_wake_from_rest"
    assert frame.owner_state == "low_energy_or_tired"
    assert frame.memory_relation == "time_bound_recall"
    assert "- memory_relation: time_bound_recall" in rendered


def test_scene_frame_project_work_stays_direct(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u5f00\u59cb\u5b9e\u73b0",
        contextual_scene="project_work",
    )

    assert frame.scene_id == "project_work"
    assert frame.task_mode == "technical_execution"
    assert frame.reply_policy == "direct_task_answer"


@pytest.mark.parametrize(
    "case",
    [
        {
            "id": "after_night_shift_low_energy",
            "user_text": "\u6211\u521a\u4e0b\u5b8c\u591c\u73ed\u6709\u70b9\u56f0\uff0c\u8981\u53bb\u7761\u4e00\u89c9",
            "evaluated_at": "2026-05-19T08:30:00+08:00",
            "expected": {
                "scene_id": "casual_chat",
                "time_context": "after_night_shift",
                "owner_state": "low_energy_or_tired",
                "task_mode": "ordinary_chat",
                "memory_relation": "current_turn_first",
                "reply_policy": "short_gentle_low_burden",
            },
        },
        {
            "id": "just_woke_from_nap_temporal_recall",
            "user_text": "\u6211\u521a\u9192\uff0c\u73b0\u5728\u8be5\u600e\u4e48\u56de\uff1f",
            "canonical_recall_context": (
                "## Temporal Context\n"
                "- inference: recent_wake_from_nap | sleep_start=12:30 wake=13:30\n"
                "\n"
                "## Recalled Context\n"
                "- source: dialogue_tail\n"
            ),
            "expected": {
                "scene_id": "casual_chat",
                "time_context": "recent_wake_from_rest",
                "owner_state": "low_energy_or_tired",
                "task_mode": "ordinary_chat",
                "memory_relation": "time_bound_recall",
                "reply_policy": "short_gentle_low_burden",
            },
        },
        {
            "id": "late_night_technical_work",
            "user_text": "\u7ee7\u7eed\u4fee\u8fd9\u4e2a\u6a21\u5757",
            "contextual_scene": "project_work",
            "evaluated_at": "2026-05-19T02:15:00+08:00",
            "expected": {
                "scene_id": "project_work",
                "time_context": "late_night",
                "owner_state": "unknown_or_unstated",
                "task_mode": "technical_execution",
                "memory_relation": "current_turn_first",
                "reply_policy": "direct_task_answer",
            },
        },
        {
            "id": "relationship_emotional_pressure",
            "user_text": "\u6211\u6709\u70b9\u96be\u53d7\uff0c\u611f\u89c9\u5173\u7cfb\u53d8\u51b7\u6de1\u4e86",
            "expected": {
                "scene_id": "emotional_relation",
                "time_context": "ordinary_time",
                "owner_state": "emotional_pressure_possible",
                "task_mode": "relational_support",
                "memory_relation": "current_turn_first",
                "reply_policy": "warm_boundary_aware",
            },
        },
        {
            "id": "runtime_maintenance_request",
            "user_text": "runtime health metrics",
            "expected": {
                "scene_id": "runtime_status",
                "time_context": "ordinary_time",
                "owner_state": "unknown_or_unstated",
                "task_mode": "runtime_status",
                "memory_relation": "current_turn_first",
                "reply_policy": "compact_structured_answer",
            },
        },
        {
            "id": "explicit_recall_request",
            "user_text": "\u4f60\u8fd8\u8bb0\u5f97\u4e4b\u524d\u8bf4\u8fc7\u7684\u8ba1\u5212\u5417\uff1f",
            "expected": {
                "scene_id": "memory_review",
                "time_context": "ordinary_time",
                "owner_state": "unknown_or_unstated",
                "task_mode": "memory_review",
                "memory_relation": "explicit_recall_request",
                "reply_policy": "compact_structured_answer",
            },
        },
    ],
    ids=lambda case: case["id"],
)
def test_scene_frame_replay_pack_v1(tmp_path: Path, case: dict[str, object]) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text=str(case["user_text"]),
        contextual_scene=str(case.get("contextual_scene") or ""),
        canonical_recall_context=str(case.get("canonical_recall_context") or ""),
        evaluated_at=str(case.get("evaluated_at") or ""),
    )
    rendered = render_scene_frame_prompt_block(frame)
    expected = case["expected"]

    for field, value in expected.items():
        assert getattr(frame, field) == value
        assert f"- {field}: {value}" in rendered
