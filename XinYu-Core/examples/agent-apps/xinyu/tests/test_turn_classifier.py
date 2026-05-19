from __future__ import annotations

from pathlib import Path

from xinyu_turn_classifier import classify_visible_turn


def test_spaced_ai_complaint_is_owner_style_pressure(tmp_path: Path) -> None:
    context = classify_visible_turn(
        tmp_path,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="你又有点像 AI",
    )

    assert context.turn_kind == "owner_style_pressure"
    assert context.owner_style_pressure is True
    assert context.technical_work is False
