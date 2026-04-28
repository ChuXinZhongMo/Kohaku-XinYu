from __future__ import annotations

from xinyu_v1.emotion.models import EmotionDelta, EmotionState
from xinyu_v1.emotion.state_machine import EmotionStateMachine


def test_emotion_update_is_damped() -> None:
    state = EmotionState.neutral("2026-01-01T00:00:00+00:00")
    transition = EmotionStateMachine().apply(
        state,
        EmotionDelta({"hurt": 1.0, "trust": -1.0}, salience=1.0, reason="test"),
        timestamp="2026-01-01T00:00:01+00:00",
    )

    assert 0.0 < transition.current.vector.get("hurt") <= 0.38
    assert -0.38 <= transition.current.vector.get("trust") < 0.0
    assert "high_salience" in transition.notes

