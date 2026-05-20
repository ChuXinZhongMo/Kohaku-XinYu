from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_semantic_fast_routes import owner_private_direct_repair_reply
from xinyu_bridge_semantic_fast_routes import owner_private_semantic_fast_decision
from xinyu_bridge_semantic_fast_routes import reply_looks_like_stale_plan_residue


class FakeRuntime:
    owner_private_semantic_fast_route = True

    def __init__(self, *, owner_private: bool = True, decision: object | None = None) -> None:
        self.xinyu_dir = "."
        self._v1_app = SimpleNamespace(
            normalizer=SimpleNamespace(normalize=lambda payload: payload),
            router=SimpleNamespace(decide=lambda turn: decision),
        )
        self._owner_private = owner_private

    def _owner_private_payload_matches(self, payload) -> bool:
        del payload
        return self._owner_private


def _decision(*, route: str, intents: list[str], needs_model: bool = False, needs_memory: bool = False):
    return SimpleNamespace(
        route=SimpleNamespace(value=route),
        reasons=("test",),
        classification=SimpleNamespace(
            intents=intents,
            needs_model=needs_model,
            needs_memory=needs_memory,
        ),
    )


def test_owner_private_semantic_fast_decision_allows_low_risk_greeting() -> None:
    runtime = FakeRuntime(decision=_decision(route="fast_path", intents=["greeting"]))

    result = owner_private_semantic_fast_decision(
        runtime,
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        "晚上好",
    )

    assert result["allowed"] is True
    assert result["route"] == "fast_path"
    assert result["intents"] == ("greeting",)
    assert result["direct_reply"] == "\u665a\u4e0a\u597d\u3002"
    assert "semantic_fast_allowed" in result["notes"]


def test_owner_private_semantic_fast_decision_rejects_non_owner_without_v1() -> None:
    runtime = FakeRuntime(owner_private=False)

    result = owner_private_semantic_fast_decision(runtime, {"message_type": "private_text"}, "晚上好")

    assert result == {"allowed": False, "notes": ["not_owner_private"]}


def test_owner_private_semantic_fast_decision_rejects_complex_v1_classification() -> None:
    runtime = FakeRuntime(decision=_decision(route="fast_path", intents=["relationship_pressure"], needs_model=True))

    result = owner_private_semantic_fast_decision(
        runtime,
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        "你刚才很敷衍",
    )

    assert result["allowed"] is False
    assert result["route"] == "fast_path"
    assert result["intents"] == ("relationship_pressure",)
    assert "semantic_fast_not_low_risk" in result["notes"]


def test_owner_private_semantic_fast_decision_rejects_shape_before_v1() -> None:
    runtime = FakeRuntime(decision=_decision(route="fast_path", intents=["greeting"]))

    assert owner_private_semantic_fast_decision(runtime, {"metadata": {"is_owner_user": True}}, "") == {
        "allowed": False,
        "notes": ["empty_text"],
    }
    assert owner_private_semantic_fast_decision(runtime, {"metadata": {"is_owner_user": True}}, "一\n二") == {
        "allowed": False,
        "notes": ["multiline_text"],
    }
    assert owner_private_semantic_fast_decision(runtime, {"metadata": {"is_owner_user": True}}, "很长" * 20) == {
        "allowed": False,
        "notes": ["text_too_long_for_semantic_fast_route"],
    }


def test_owner_private_semantic_fast_decision_directly_handles_current_reply_complaint() -> None:
    runtime = FakeRuntime(
        decision=_decision(route="slow_path", intents=["ordinary_chat"], needs_model=True, needs_memory=True)
    )

    result = owner_private_semantic_fast_decision(
        runtime,
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        "\u4f60\u5728\u8bf4\u4ec0\u4e48",
    )

    assert result["allowed"] is True
    assert result["intents"] == ("reply_quality_complaint",)
    assert result["direct_reply"] == (
        "\u521a\u624d\u90a3\u53e5\u63a5\u9519\u4e86\uff0c"
        "\u662f\u65e7\u4e0a\u4e0b\u6587\u4e32\u8fdb\u6765\u4e86\uff1b"
        "\u8fd9\u53e5\u6211\u6309\u4f60\u5f53\u524d\u95ee\u9898\u6765\u3002"
    )


def test_owner_private_semantic_fast_decision_directly_handles_runtime_status_question() -> None:
    runtime = FakeRuntime(
        decision=_decision(route="slow_path", intents=["ordinary_chat"], needs_model=True, needs_memory=True)
    )

    result = owner_private_semantic_fast_decision(
        runtime,
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        "\uff1f\u554a \u73b0\u5728\u540e\u53f0\u5728\u8dd1\u4ec0\u4e48\u4e1c\u897f",
    )

    assert result["allowed"] is True
    assert result["intents"] == ("runtime_status_question",)
    assert "\u4e0d\u662f QQ \u6ca1\u6536\u5230" in result["direct_reply"]


def test_stale_plan_residue_detector_and_repair_reply() -> None:
    stale_reply = (
        "\u53ef\u4ee5\u3002\u5148\u628a\u8303\u56f4\u538b\u5c0f\u4e00\u70b9\uff0c"
        "\u6309\u672c\u5730\u53ef\u8fd0\u884c\u3001\u53ef\u56de\u6eda\u3001shadow \u8def\u7ebf\u5904\u7406\u3002"
    )

    assert reply_looks_like_stale_plan_residue(stale_reply) is True
    assert reply_looks_like_stale_plan_residue("\u4e0d\u662f\u6ca1\u6536\u5230\u3002") is False
    assert owner_private_direct_repair_reply(object(), "\uff1f\uff1f\uff1f")
