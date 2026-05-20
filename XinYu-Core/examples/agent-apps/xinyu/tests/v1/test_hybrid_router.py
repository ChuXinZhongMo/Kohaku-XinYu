from __future__ import annotations

from datetime import UTC, datetime

from xinyu_v1.clock import FixedClock
from xinyu_v1.gateway.normalizer import TurnNormalizer
from xinyu_v1.routing.hybrid_router import HybridRouter
from xinyu_v1.types import RouteName


def _turn(text: str):
    return TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC))).normalize(
        {"text": text, "user_id": "u", "session_id": "s"}
    )


def test_greeting_routes_fast_path() -> None:
    decision = HybridRouter().decide(_turn("你好"))
    assert decision.route is RouteName.FAST_PATH


def test_greeting_containing_ack_marker_stays_greeting_only() -> None:
    decision = HybridRouter().decide(_turn("\u665a\u4e0a\u597d"))
    assert decision.route is RouteName.FAST_PATH
    assert decision.classification.intents == ("greeting",)


def test_relationship_pressure_routes_slow_path() -> None:
    decision = HybridRouter().decide(_turn("你刚才那样我有点失望"))
    assert decision.route is RouteName.SLOW_PATH
    assert "relationship_pressure" in decision.classification.intents


def test_english_and_japanese_greetings_route_fast_path() -> None:
    for text in ("hello", "good evening", "こんにちは", "こんばんは"):
        decision = HybridRouter().decide(_turn(text))
        assert decision.route is RouteName.FAST_PATH
        assert "greeting" in decision.classification.intents


def test_english_and_japanese_relationship_pressure_stays_slow_path() -> None:
    for text in ("I am disappointed", "失望した", "寂しい"):
        decision = HybridRouter().decide(_turn(text))
        assert decision.route is RouteName.SLOW_PATH
        assert "relationship_pressure" in decision.classification.intents
