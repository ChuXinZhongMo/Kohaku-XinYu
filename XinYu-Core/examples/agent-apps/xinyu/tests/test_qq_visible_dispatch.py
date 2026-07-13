from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from xinyu_qq_models import PreparedMessage, ReplyTarget
from xinyu_qq_visible_dispatch import (
    combined_reply_action_response,
    record_direct_visible_send_shadow,
    send_visible_reply,
    session_id,
    visible_reply,
)


class FakeGateway:
    def __init__(self, root: Path) -> None:
        self.xinyu_dir = root
        self.config = SimpleNamespace(max_reply_chars=12, reply_bubble_delay_seconds=0)
        self.sent: list[str] = []

    def _visible_reply_bubbles(
        self,
        prepared: PreparedMessage,
        reply: str,
        core_response: dict[str, object],
    ) -> list[str]:
        return [part.strip() for part in reply.split("|") if part.strip()]

    async def _resolve_action_websocket(self, websocket, *, wait_seconds: float = 0.0):
        return websocket if websocket is not None else self

    async def send_reply(self, websocket, target: ReplyTarget, text: str) -> dict[str, object]:
        self.sent.append(text)
        return {"status": "ok", "retcode": 0, "data": {"message_id": f"msg-{len(self.sent)}"}}

    def _onebot_action_result(self, response):
        if not response:
            return False, "", "empty"
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        message_id = str(data.get("message_id") or "")
        return response.get("status") == "ok", message_id, str(response.get("message") or "")


def test_session_id_uses_private_and_group_shapes() -> None:
    assert session_id(ReplyTarget(message_kind="private", user_id="42", group_id="")) == "qq:private:42"
    assert session_id(ReplyTarget(message_kind="group", user_id="42", group_id="7")) == "qq:group:7:42"
    assert session_id(ReplyTarget(message_kind="group", user_id="42", group_id="")) == "qq:group:unknown:42"


def test_visible_reply_filters_waiting_and_truncates(tmp_path: Path) -> None:
    gateway = FakeGateway(tmp_path)

    assert visible_reply(gateway, "[WAITING]") == ""
    assert visible_reply(gateway, "  123456789012345  ") == "123456789012\n[truncated]"


def test_visible_reply_strips_internal_prompt_leaks(tmp_path: Path) -> None:
    gateway = FakeGateway(tmp_path)
    gateway.config.max_reply_chars = 200
    raw = (
        "It is not a safety ban on any protected class. "
        "If `resource_posture` is `normal`, treat it as ordinary chat. "
        "/think? </think>\u54e5\uff0c\u665a\u4e0a\u597d\u3002"
        "\u521a\u9192\u8fd8\u662f\u8fd8\u6ca1\u7761\u3002"
    )

    assert visible_reply(gateway, raw) == "\u54e5\uff0c\u665a\u4e0a\u597d\u3002\u521a\u9192\u8fd8\u662f\u8fd8\u6ca1\u7761\u3002"


@pytest.mark.asyncio
async def test_send_visible_reply_combines_bubble_message_ids(tmp_path: Path) -> None:
    gateway = FakeGateway(tmp_path)
    target = ReplyTarget(message_kind="private", user_id="42", group_id="")
    prepared = PreparedMessage(target=target, payload={"session_id": "qq:private:42"})

    result = await send_visible_reply(gateway, None, prepared, "one|two", {"route": "chat"})

    assert gateway.sent == ["one", "two"]
    assert result is not None
    assert result["data"]["message_id"] == "msg-1,msg-2"
    assert result["data"]["reply_bubble_message_ids"] == ["msg-1", "msg-2"]


def test_combined_reply_action_response_fails_on_partial_delivery(tmp_path: Path) -> None:
    gateway = FakeGateway(tmp_path)

    result = combined_reply_action_response(
        gateway,
        [
            {"status": "ok", "retcode": 0, "data": {"message_id": "msg-1"}},
            {"status": "failed", "message": "onebot_action_timeout"},
        ],
    )

    assert result is not None
    assert result["status"] == "failed"
    assert result.get("xinyu_partial_delivery") is True
    assert result["data"]["reply_bubble_sent_count"] == 1
    assert result["data"]["reply_bubble_count"] == 2


def test_combined_reply_action_response_returns_last_when_all_fail(tmp_path: Path) -> None:
    gateway = FakeGateway(tmp_path)

    result = combined_reply_action_response(
        gateway,
        [
            {"status": "failed", "message": "first"},
            {"status": "failed", "message": "second"},
        ],
    )

    assert result == {"status": "failed", "message": "second"}


def test_combined_reply_action_response_preserves_delivery_kinds(tmp_path: Path) -> None:
    gateway = FakeGateway(tmp_path)

    result = combined_reply_action_response(
        gateway,
        [
            {
                "status": "ok",
                "retcode": 0,
                "xinyu_delivery_kind": "voice",
                "data": {"message_id": "msg-1", "delivery_kind": "voice"},
            },
            {
                "status": "ok",
                "retcode": 0,
                "xinyu_delivery_kind": "text",
                "xinyu_voice_fallback_reason": "tts_down",
                "data": {"message_id": "msg-2", "delivery_kind": "text"},
            },
        ],
    )

    assert result is not None
    assert result["xinyu_delivery_kind"] == "mixed"
    assert result["xinyu_voice_fallback_reason"] == "tts_down"
    assert result["data"]["reply_bubble_delivery_kinds"] == ["voice", "text"]
    assert result["data"]["delivery_kind"] == "mixed"


def test_record_direct_visible_send_shadow_uses_hashes(tmp_path: Path) -> None:
    gateway = FakeGateway(tmp_path)
    target = ReplyTarget(message_kind="private", user_id="42", group_id="")
    prepared = PreparedMessage(target=target, payload={"session_id": "qq:private:42"}, route="chat")

    result = record_direct_visible_send_shadow(
        gateway,
        prepared,
        "plain reply",
        {"route": "chat", "turn_id": "turn-sensitive"},
    )

    assert result["recorded"] is True
    assert result["reply_hash"].startswith("sha256:")
    assert result["session_id_hash"]
    assert result["turn_id_hash"]
