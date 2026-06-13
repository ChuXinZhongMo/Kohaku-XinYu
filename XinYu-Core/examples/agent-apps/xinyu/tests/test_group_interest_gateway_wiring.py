from __future__ import annotations

from pathlib import Path

from xinyu_qq_config import GatewayConfig
from xinyu_qq_gateway import NativeQQGateway


def _gateway(tmp_path: Path) -> NativeQQGateway:
    gateway = NativeQQGateway(
        GatewayConfig(
            require_whitelist=False,
            allowed_group_ids=frozenset({"g1"}),
            group_shadow_enabled=True,
            group_shadow_allowed_group_ids=frozenset({"g1"}),
            group_shadow_max_text_chars=300,
            group_interest_reply_enabled=True,
            group_interest_reply_allowed_group_ids=frozenset({"g1"}),
            group_interest_reply_min_score=1,
            group_interest_reply_cooldown_seconds=0,
            group_interest_followup_max_turns=1,
        )
    )
    gateway.xinyu_dir = tmp_path
    return gateway


def _event(text: str) -> dict:
    return {
        "post_type": "message",
        "message_type": "group",
        "platform": "qq",
        "group_id": "g1",
        "user_id": "u1",
        "self_id": "bot",
        "message_id": "m1",
        "message": text,
        "raw_message": text,
        "time": 1_700_000_000,
    }


def test_gateway_allows_interesting_unmentioned_group_message(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    event = _event("AI memory 怎么让群聊也能被记住？")

    shadow = gateway._maybe_record_group_shadow_event(event)
    prepared = gateway.prepare_message(event)

    assert shadow["group_interest"]["should_reply"] is True
    assert prepared is not None
    metadata = prepared.payload["metadata"]
    assert metadata["qq_group_trigger_reason"] == "group_interest_open"
    assert metadata["qq_group_interest_reply"] is True
    assert metadata["qq_group_interest_score"] >= 1


def test_gateway_keeps_low_signal_group_message_shadow_only(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    event = _event("哈哈")

    shadow = gateway._maybe_record_group_shadow_event(event)
    prepared = gateway.prepare_message(event)

    assert shadow["group_interest"]["should_reply"] is False
    assert prepared is None
