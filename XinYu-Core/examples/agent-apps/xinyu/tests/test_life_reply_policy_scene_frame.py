from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_life_reply_policy import apply_life_reply_policy  # noqa: E402
from xinyu_life_reply_policy import build_life_reply_policy  # noqa: E402
from xinyu_life_reply_policy import build_life_reply_prompt_block  # noqa: E402
from xinyu_scene_frame import build_scene_frame  # noqa: E402


def test_life_reply_policy_consumes_low_burden_scene_frame(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u521a\u9192\uff0c\u73b0\u5728\u8be5\u600e\u4e48\u56de\uff1f",
        canonical_recall_context=(
            "## Temporal Context\n"
            "- inference: recent_wake_from_nap | sleep_start=12:30 wake=13:30\n"
        ),
    )

    policy = build_life_reply_policy(user_text="\u6211\u521a\u9192", scene_frame=frame)
    block = build_life_reply_prompt_block(policy)

    assert policy["mode"] == "low_energy"
    assert policy["reply_pressure"] == "short"
    assert policy["suppress_optional_question"] is True
    assert policy["scene_frame"]["reply_policy"] == "short_gentle_low_burden"
    assert "scene_frame=short_gentle_low_burden" in policy["reasons"]
    assert "- scene_reply_policy: short_gentle_low_burden" in block
    assert "- scene_memory_relation: time_bound_recall" in block

    shaped = apply_life_reply_policy(
        "\u55ef\uff0c\u6211\u5728\u3002\u4f60\u5148\u6162\u4e00\u70b9\u3002\u6211\u628a\u8bdd\u653e\u8f7b\u3002\u8981\u4e0d\u8981\u6211\u7ee7\u7eed\u95ee\uff1f",
        policy=policy,
        user_text="\u6211\u521a\u9192",
    )

    assert shaped["changed"] is True
    assert "\u8981\u4e0d\u8981" not in shaped["reply"]


def test_life_reply_policy_scene_frame_marks_technical_direct(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u6a21\u5757",
        contextual_scene="project_work",
    )

    policy = build_life_reply_policy(user_text="\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u6a21\u5757", scene_frame=frame)

    assert policy["technical_turn"] is True
    assert policy["reply_pressure"] == "normal"
    assert policy["scene_frame"]["reply_policy"] == "direct_task_answer"


def test_life_reply_policy_scene_frame_marks_relationship_boundary(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u6709\u70b9\u96be\u53d7\uff0c\u611f\u89c9\u5173\u7cfb\u53d8\u51b7\u6de1\u4e86",
    )

    policy = build_life_reply_policy(user_text="\u6211\u6709\u70b9\u96be\u53d7", scene_frame=frame)
    block = build_life_reply_prompt_block(policy)

    assert policy["mode"] == "relation_aware"
    assert policy["reply_pressure"] == "warm_boundaried"
    assert policy["max_sentences"] == 3
    assert policy["scene_frame"]["reply_policy"] == "warm_boundary_aware"
    assert "- scene_reply_policy: warm_boundary_aware" in block


def test_life_reply_policy_blocks_bare_ack_without_template_for_life_chat() -> None:
    shaped = apply_life_reply_policy(
        "嗯。",
        policy={"technical_turn": False, "mode": "steady", "max_sentences": 3},
        user_text="唉",
    )

    assert shaped["changed"] is True
    assert shaped["reply"] == ""
    assert "life_reply_bare_ack_blocked_no_template" in shaped["notes"]

    state_question = apply_life_reply_policy(
        "嗯。",
        policy={"technical_turn": False, "mode": "steady", "max_sentences": 3},
        user_text="还好吗",
    )

    assert state_question["reply"] == ""
    assert "life_reply_bare_ack_blocked_no_template" in state_question["notes"]


def test_life_reply_policy_keeps_bare_ack_for_technical_turn() -> None:
    shaped = apply_life_reply_policy(
        "嗯。",
        policy={"technical_turn": True, "mode": "steady", "max_sentences": 5},
        user_text="继续修这个 bug",
    )

    assert shaped["changed"] is False
    assert shaped["reply"] == "嗯。"
