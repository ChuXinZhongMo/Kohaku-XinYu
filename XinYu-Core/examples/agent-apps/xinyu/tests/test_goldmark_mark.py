from __future__ import annotations

from pathlib import Path

from xinyu_goldmark import mark_goldmark_request, read_goldmark_overlay
from xinyu_qq_gateway import GatewayConfig, NativeQQGateway
from xinyu_sent_reply_index import register_sent_reply_ack


def test_goldmark_mark_request_writes_overlay_entry(tmp_path: Path) -> None:
    register_sent_reply_ack(
        tmp_path,
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": "1124871716",
            "route": "chat",
            "session_id": "qq:private:42",
            "turn_id": "turn-20260503T193453-sha256:354080c682",
            "archive_assistant_message_id": "",
            "visible_text": "嗯，知道了。",
        },
    )

    result = mark_goldmark_request(
        tmp_path,
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": "1124871716",
            "route": "chat",
            "owner_note": "这句可以",
            "source_message_id": "cmd-1",
        },
    )

    assert result["marked"] is True
    assert result["mark_id"] == "gm-20260503-T193453"

    overlay = read_goldmark_overlay(tmp_path)
    assert len(overlay) == 1
    assert overlay[0]["turn_id"] == "turn-20260503T193453-sha256:354080c682"
    assert overlay[0]["adapter_msg_id"] == "1124871716"
    assert overlay[0]["owner_note"] == "这句可以"
    assert overlay[0]["stage"] == "p4b_mvp_mark_only"
    assert overlay[0]["dehydration_status"] == "pending"
    assert overlay[0]["vibe_features"] is None


def test_goldmark_mark_request_reports_missing_target(tmp_path: Path) -> None:
    result = mark_goldmark_request(
        tmp_path,
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": "missing",
            "route": "chat",
        },
    )

    assert result["marked"] is False
    assert result["error"] == "target_not_found"
    assert result["http_status"] == 404
    assert read_goldmark_overlay(tmp_path) == []


def test_gateway_intercepts_owner_private_reply_mark() -> None:
    gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="token",
            whitelist_user_ids=frozenset({"42"}),
            owner_user_ids=frozenset({"42"}),
            group_trigger_prefixes=("xinyu",),
        )
    )
    event = {
        "post_type": "message",
        "message_type": "private",
        "user_id": "42",
        "message_id": "cmd-1",
        "time": 1714739693,
        "message": [
            {"type": "reply", "data": {"id": "1124871716"}},
            {"type": "text", "data": {"text": "!mark 这句可以"}},
        ],
        "raw_message": "[CQ:reply,id=1124871716]!mark 这句可以",
    }

    prepared = gateway.prepare_message(event)

    assert prepared is not None
    assert prepared.route == "goldmark_mark"
    assert prepared.payload["adapter_message_id"] == "1124871716"
    assert prepared.payload["owner_note"] == "这句可以"
    assert prepared.payload["route"] == "chat"


def test_gateway_mark_requires_reply_message() -> None:
    gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="token",
            whitelist_user_ids=frozenset({"42"}),
            owner_user_ids=frozenset({"42"}),
            group_trigger_prefixes=("xinyu",),
        )
    )
    event = {
        "post_type": "message",
        "message_type": "private",
        "user_id": "42",
        "message_id": "cmd-1",
        "time": 1714739693,
        "message": [{"type": "text", "data": {"text": "!mark"}}],
        "raw_message": "!mark",
    }

    prepared = gateway.prepare_message(event)

    assert prepared is not None
    assert prepared.local_reply
    assert prepared.route == "local_reply"
