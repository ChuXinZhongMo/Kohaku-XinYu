from __future__ import annotations

from datetime import UTC, datetime

from xinyu_v1.clock import FixedClock
from xinyu_v1.gateway.normalizer import TurnNormalizer
from xinyu_v1.routing.fast_path import FastPathResponder
from xinyu_v1.routing.hybrid_router import HybridRouter


def test_fast_path_greeting_has_no_memory_write() -> None:
    turn = TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC))).normalize(
        {"text": "你好", "user_id": "u", "session_id": "s"}
    )
    decision = HybridRouter().decide(turn)
    result = FastPathResponder().respond(turn, decision.classification)

    assert result.reply
    assert result.memory_changed is False
    assert "fast_path" in result.notes

