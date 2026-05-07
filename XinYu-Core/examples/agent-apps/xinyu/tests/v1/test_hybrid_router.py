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


def test_relationship_pressure_routes_slow_path() -> None:
    decision = HybridRouter().decide(_turn("你刚才那样我有点失望"))
    assert decision.route is RouteName.SLOW_PATH
    assert "relationship_pressure" in decision.classification.intents

