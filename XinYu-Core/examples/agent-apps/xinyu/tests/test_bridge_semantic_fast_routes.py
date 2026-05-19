from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_semantic_fast_routes import owner_private_semantic_fast_decision


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
