from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ops.validation.live_chat_regression_baseline import CASES
from xinyu_bridge_semantic_fast_routes import owner_private_semantic_fast_decision
from xinyu_tool_intent_router import ToolIntentRouter
from xinyu_tool_targets import TargetRegistry


OWNER_PAYLOAD = {"message_type": "private_text", "metadata": {"is_owner_user": True}}
GROUP_PAYLOAD = {
    "message_type": "group_text",
    "group_id": "scenario-group",
    "user_id": "scenario-member",
    "metadata": {"is_owner_user": False},
}


class FakeRuntime:
    owner_private_semantic_fast_route = True

    def __init__(self, *, owner_private: bool = True, decision: object | None = None) -> None:
        self.xinyu_dir = "."
        self._owner_private = owner_private
        self._v1_app = SimpleNamespace(
            normalizer=SimpleNamespace(normalize=lambda payload: payload),
            router=SimpleNamespace(decide=lambda turn: decision or _decision()),
        )

    def _owner_private_payload_matches(self, payload: dict) -> bool:
        del payload
        return self._owner_private


def _decision(*, route: str = "slow_path", intents: tuple[str, ...] = ("ordinary_chat",)):
    return SimpleNamespace(
        route=SimpleNamespace(value=route),
        reasons=("pressure_regression",),
        classification=SimpleNamespace(
            intents=intents,
            needs_model=True,
            needs_memory=True,
        ),
    )


@pytest.mark.parametrize(
    "text",
    (
        "状态如何，丫头",
        "你感觉怎么样",
        "你现在怎么样",
        "心情怎么样",
    ),
)
def test_owner_state_questions_use_live_persona_path_not_status_tool(tmp_path: Path, text: str) -> None:
    tool_decision = ToolIntentRouter(TargetRegistry(tmp_path)).route(text, OWNER_PAYLOAD, turn_id="pressure-state")
    fast_decision = owner_private_semantic_fast_decision(FakeRuntime(), OWNER_PAYLOAD, text)

    assert tool_decision.kind == "no_action"
    assert fast_decision["allowed"] is True
    assert fast_decision["intents"] == ("owner_state_question",)
    assert fast_decision["direct_reply"] == ""
    assert "owner_state_question_live_renderer_required" in fast_decision["notes"]


@pytest.mark.parametrize(
    "text",
    (
        "收到消息了，前台显示正在回复，然后就没有然后了？",
        "怎么这么久才回",
        "你这不就是套模板吗",
        "根本没回我，什么情况",
        "怎么越改越出问题",
    ),
)
def test_delay_empty_reply_and_template_complaints_go_to_live_model(text: str) -> None:
    decision = owner_private_semantic_fast_decision(FakeRuntime(), OWNER_PAYLOAD, text)

    assert decision["allowed"] is False
    assert "reply_quality_complaint" in decision["intents"]
    assert "reply_quality_complaint_needs_live_model" in decision["notes"]
    assert "semantic_fast_not_low_risk" in decision["notes"]


def test_group_other_bot_boundary_stays_out_of_owner_private_fast_and_tools(tmp_path: Path) -> None:
    text = "艾莉怎么不说话了，bot 那边是不是没反应"

    tool_decision = ToolIntentRouter(TargetRegistry(tmp_path)).route(text, GROUP_PAYLOAD, turn_id="pressure-group")
    fast_decision = owner_private_semantic_fast_decision(FakeRuntime(owner_private=False), GROUP_PAYLOAD, text)

    assert tool_decision.kind == "no_action"
    assert fast_decision == {"allowed": False, "notes": ["not_owner_private"]}


def test_live_pressure_baseline_contains_sanitized_last_night_failure_shapes() -> None:
    by_id = {case["id"]: case for case in CASES}

    for case_id in (
        "owner_state_feeling",
        "owner_state_how_feels",
        "delayed_frontend_reply_stuck",
        "template_complaint_plain",
        "no_response_plain",
    ):
        assert case_id in by_id

    rendered = "\n".join(f"{case['id']} {case['text']}" for case in CASES)
    assert "26921" not in rendered
    assert "C:\\Users" not in rendered
    assert "D:\\" not in rendered
