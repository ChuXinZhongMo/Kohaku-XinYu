from __future__ import annotations

from pathlib import Path

from xinyu_attention_posture import update_attention_posture
from xinyu_expression_contract import compose_expression_event, expression_for_targets


def test_expression_contract_uses_attention_state_without_adapter_decision(tmp_path: Path) -> None:
    attention = update_attention_posture(
        tmp_path,
        {
            "event_type": "desktop_residue",
            "source": "desktop",
            "observed_at": "2026-05-24T00:30:00+08:00",
            "summary": "要不要我把表达层也接成统一事件？",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "owner_private_question",
        },
        evaluated_at="2026-05-24T00:30:00+08:00",
    )

    expression = compose_expression_event(
        tmp_path,
        adapter_target="desktop",
        source_event_id=attention["event"]["event_id"],
        source_route=attention["route"]["route"],
        created_at="2026-05-24T00:30:01+08:00",
    )

    assert expression.speaking_intention == "ask"
    assert expression.intensity == "high"
    assert expression.visible_posture == "leaning_forward"
    assert expression.text == "要不要我把表达层也接成统一事件？"
    assert expression.identity_layer == "core_only"
    assert expression.adapter_decision_allowed is False
    assert expression.owner_private_only is True


def test_expression_contract_generates_consistent_multi_target_events(tmp_path: Path) -> None:
    update_attention_posture(
        tmp_path,
        {
            "event_type": "private_note",
            "source": "runtime",
            "observed_at": "2026-05-24T00:30:00+08:00",
            "summary": "我看见了，先不打扰",
            "privacy_scope": "owner_private",
            "risk_level": "low",
            "suggested_route": "short_trace",
        },
        evaluated_at="2026-05-24T00:30:00+08:00",
    )

    events = expression_for_targets(tmp_path, created_at="2026-05-24T00:30:01+08:00")
    by_target = {event["adapter_target"]: event for event in events}

    assert set(by_target) == {"qq", "desktop", "avatar", "tts"}
    assert by_target["qq"]["visible_posture"] == "short_private_text"
    assert by_target["desktop"]["visible_posture"] == "quiet_presence"
    assert by_target["avatar"]["emotion_vector"] == by_target["desktop"]["emotion_vector"]
    assert all(event["adapter_decision_allowed"] is False for event in events)
    assert all(event["identity_layer"] == "core_only" for event in events)


def test_expression_contract_redacts_secret_text(tmp_path: Path) -> None:
    expression = compose_expression_event(
        tmp_path,
        adapter_target="qq",
        text="这里有 token=abcdef1234567890 不能露出",
        created_at="2026-05-24T00:30:01+08:00",
    )

    assert "abcdef1234567890" not in expression.text
    assert "<secret>" in expression.text
    assert expression.adapter_target == "qq"
    assert expression.adapter_decision_allowed is False


def test_expression_contract_available_state_can_stay_silent(tmp_path: Path) -> None:
    expression = compose_expression_event(tmp_path, adapter_target="avatar", created_at="2026-05-24T00:30:01+08:00")

    assert expression.speaking_intention == "silent"
    assert expression.visible_posture == "idle_breathing"
    assert expression.intensity == "low"
    assert expression.text == "我在。"
