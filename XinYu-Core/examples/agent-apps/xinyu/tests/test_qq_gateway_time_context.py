from __future__ import annotations

from datetime import datetime

from xinyu_bridge_state_text import payload_event_timestamp_seconds
from xinyu_qq_config import GatewayConfig
from xinyu_qq_gateway import NativeQQGateway
from xinyu_qq_models import ReplyTarget


def test_qq_chat_payload_carries_exact_event_time_iso() -> None:
    event_timestamp = int(datetime.fromisoformat("2026-05-18T13:30:00+08:00").timestamp())
    gateway = NativeQQGateway(
        GatewayConfig(
            require_whitelist=False,
            owner_user_ids=frozenset({"42"}),
            send_replies=False,
        )
    )

    payload = gateway._build_chat_payload(
        {
            "time": event_timestamp,
            "post_type": "message",
            "message_type": "private",
            "message_id": "m1",
            "raw_message": "status",
            "sender": {"nickname": "owner"},
        },
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        text="status",
        rich_context={},
    )

    metadata = payload["metadata"]
    assert payload["timestamp"] == event_timestamp
    assert metadata["qq_event_time_unix"] == event_timestamp
    assert int(datetime.fromisoformat(metadata["qq_event_time_iso"]).timestamp()) == event_timestamp
    assert payload_event_timestamp_seconds(payload) == event_timestamp
