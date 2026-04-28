from __future__ import annotations

from datetime import UTC, datetime

from xinyu_v1.clock import FixedClock
from xinyu_v1.gateway.normalizer import TurnNormalizer
from xinyu_v1.response.models import DraftReply
from xinyu_v1.response.renderer import ResponseRenderer


def test_response_renderer_blocks_private_marker() -> None:
    turn = TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC))).normalize(
        {"text": "hi", "user_id": "u", "session_id": "s"}
    )
    final = ResponseRenderer().render(DraftReply(text="Authorization: Bearer secret", source="test"), turn)

    assert final.accepted is False
    assert final.text == ""

