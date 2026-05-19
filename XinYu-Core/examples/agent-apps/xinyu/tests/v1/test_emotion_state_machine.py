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


def test_v1_emotion_dimensions_include_private_negative_expression() -> None:
    state = EmotionState.neutral("2026-01-01T00:00:00+00:00")
    transition = EmotionStateMachine().apply(
        state,
        EmotionDelta(
            {
                "anger": 1.0,
                "annoyance": 0.8,
                "aversion": 0.7,
                "disgust": 0.6,
                "distance_impulse": 0.6,
                "pushback_impulse": 0.5,
            },
            salience=1.0,
            reason="owner_private_negative_expression",
        ),
        timestamp="2026-01-01T00:00:01+00:00",
    )

    assert transition.current.vector.get("anger") > 0.0
    assert transition.current.vector.get("annoyance") > 0.0
    assert transition.current.vector.get("aversion") > 0.0
    assert transition.current.vector.get("disgust") > 0.0
    assert transition.current.vector.get("distance_impulse") > 0.0
    assert transition.current.vector.get("pushback_impulse") > 0.0
