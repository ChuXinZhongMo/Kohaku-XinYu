from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from xinyu_gateway_ack_spool import SentAckSpool, ack_unique_key
from xinyu_qq_gateway import BridgeError, GatewayConfig, NativeQQGateway, PreparedMessage, ReplyTarget
from xinyu_sent_reply_index import lookup_sent_reply_by_adapter_msg_id, register_sent_reply_ack


def test_ack_spool_folds_pending_and_acked_events(tmp_path: Path) -> None:
    spool = SentAckSpool(tmp_path / "runtime/gateway_ack_spool.jsonl")
    first = {
        "adapter": "gateway",
        "adapter_message_id": "qq-1",
        "source_route": "chat",
        "ack_attempts": "not-an-int",
        "sent_at": "2026-05-03T09:00:00",
    }
    second = {
        "adapter": "gateway",
        "adapter_message_id": "qq-2",
        "route": "chat",
        "ack_attempts": "2",
    }

    assert ack_unique_key(first) == "gateway|qq-1|chat"
    assert spool.append_pending(first)["queued"] is True
    assert spool.append_pending(second)["queued"] is True
    assert spool.append_acked(first)["acked"] is True

    pending = spool.pending_payloads()
    assert len(pending) == 1
    assert pending[0]["adapter_message_id"] == "qq-2"
    assert pending[0]["ack_attempts"] == 2

    compacted = spool.compact()
    assert compacted["pending_count"] == 1
    assert len(spool.path.read_text(encoding="utf-8").splitlines()) == 1


class _FakeCoreClient:
    def __init__(self, *, fail_ack: bool) -> None:
        self.fail_ack = fail_ack
        self.message_ack_url = "http://127.0.0.1:8765/internal/message/ack"
        self.acks: list[dict[str, Any]] = []
        self.outbox_acks: list[dict[str, Any]] = []

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "accepted": True,
            "reply": "visible reply",
            "session_id": payload.get("session_id", ""),
            "turn_id": "turn-1",
            "reply_hash": "sha256:reply",
            "archive_message_ids": ["user-archive", "assistant-archive"],
            "archive_assistant_message_id": "assistant-archive",
        }

    async def message_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.acks.append(dict(payload))
        if self.fail_ack:
            raise BridgeError("core temporarily down")
        return {"accepted": True, "indexed": True}

    async def qq_outbox_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.outbox_acks.append(dict(payload))
        return {"accepted": True, "ack_recorded": True}


class _AckGateway(NativeQQGateway):
    def __init__(self, config: GatewayConfig, client: _FakeCoreClient) -> None:
        super().__init__(config)
        self.client = client
        # NativeQQGateway recreates ack_spool from config; keep the fake client
        # attribute surface complete for outbox ack helpers.
        self.sent_actions: list[tuple[str, dict[str, Any]]] = []

    async def send_action(self, websocket: Any, action: str, params: dict[str, Any]) -> dict[str, Any] | None:
        self.sent_actions.append((action, params))
        return {"status": "ok", "retcode": 0, "data": {"message_id": "adapter-1"}}


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))


async def test_gateway_scopes_onebot_actions_to_connection(tmp_path: Path) -> None:
    config = GatewayConfig(
        bridge_token="token",
        gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
        whitelist_user_ids=frozenset({"42"}),
        owner_user_ids=frozenset({"42"}),
        group_trigger_prefixes=("xinyu",),
    )
    gateway = NativeQQGateway(config)
    first_ws = _FakeWebSocket()
    second_ws = _FakeWebSocket()
    gateway._websocket_connection_ids[id(first_ws)] = "conn-a"
    gateway._websocket_connection_ids[id(second_ws)] = "conn-b"

    first_task = asyncio.create_task(gateway.send_action(first_ws, "send_private_msg", {"user_id": 42}))
    second_task = asyncio.create_task(gateway.send_action(second_ws, "send_private_msg", {"user_id": 42}))
    await asyncio.sleep(0)

    first_echo = first_ws.sent[0]["echo"]
    second_echo = second_ws.sent[0]["echo"]

    assert gateway._complete_action_response({"echo": first_echo, "status": "ok"}, "conn-b") is False
    assert first_task.done() is False
    gateway._fail_pending_actions_for_connection("conn-a", BridgeError("closed"))

    assert await first_task is None
    assert second_task.done() is False
    assert gateway._complete_action_response(
        {"echo": second_echo, "status": "ok", "retcode": 0, "data": {"message_id": "adapter-2"}},
        "conn-b",
    ) is True
    assert await second_task == {"echo": second_echo, "status": "ok", "retcode": 0, "data": {"message_id": "adapter-2"}}


async def test_gateway_spools_failed_sent_message_ack_and_retries(tmp_path: Path) -> None:
    config = GatewayConfig(
        bridge_token="token",
        gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
        whitelist_user_ids=frozenset({"42"}),
        owner_user_ids=frozenset({"42"}),
        group_trigger_prefixes=("xinyu",),
    )
    failing_client = _FakeCoreClient(fail_ack=True)
    gateway = _AckGateway(config, failing_client)
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={"session_id": "qq:private:42", "message_id": "source-1"},
        route="chat",
    )

    ws = _FakeWebSocket()
    await gateway._dispatch_prepared_message(ws, prepared)

    assert failing_client.acks[0]["adapter_message_id"] == "adapter-1"
    assert failing_client.acks[0]["visible_text"] == "visible reply"
    pending = gateway.ack_spool.pending_payloads()
    assert len(pending) == 1
    assert pending[0]["source_message_id"] == "source-1"

    retry_client = _FakeCoreClient(fail_ack=False)
    gateway.client = retry_client
    result = await gateway._flush_pending_message_acks(limit=5)

    assert result["flushed_count"] == 1
    assert retry_client.acks[0]["ack_attempts"] == 1
    assert gateway.ack_spool.pending_payloads() == []


async def test_gateway_write_ahead_spools_before_successful_sent_message_ack(tmp_path: Path) -> None:
    config = GatewayConfig(
        bridge_token="token",
        gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
        whitelist_user_ids=frozenset({"42"}),
        owner_user_ids=frozenset({"42"}),
        group_trigger_prefixes=("xinyu",),
    )
    client = _FakeCoreClient(fail_ack=False)
    gateway = _AckGateway(config, client)
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={"session_id": "qq:private:42", "message_id": "source-1"},
        route="chat",
    )

    ws = _FakeWebSocket()
    await gateway._dispatch_prepared_message(ws, prepared)

    events = [json.loads(line) for line in gateway.ack_spool.path.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == ["pending", "acked"]
    assert client.acks[0]["adapter_message_id"] == "adapter-1"
    assert gateway.ack_spool.pending_payloads() == []


async def test_gateway_indexes_outbox_visible_delivery_with_write_ahead_spool(tmp_path: Path) -> None:
    config = GatewayConfig(
        bridge_token="token",
        gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
        whitelist_user_ids=frozenset({"42"}),
        owner_user_ids=frozenset({"42"}),
        group_trigger_prefixes=("xinyu",),
    )
    client = _FakeCoreClient(fail_ack=False)
    gateway = _AckGateway(config, client)
    claim = {
        "message_id": "proactive:req-1",
        "claim_id": "claim-1",
        "message_type": "text",
        "message": "visible outbox reply",
        "source": "proactive_presence",
        "metadata": {
            "session_id": "qq:private:42",
            "turn_id": "turn-proactive",
            "archive_assistant_message_id": "archive-proactive",
        },
    }

    await gateway._ack_sent_outbox_delivery(
        claim,
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        visible_text="visible outbox reply",
        adapter_message_id="adapter-outbox-1",
        delivery_kind="text",
    )

    assert client.acks[0]["route"] == "proactive"
    assert client.acks[0]["outbox_message_id"] == "proactive:req-1"
    assert client.acks[0]["turn_id"] == "turn-proactive"
    assert gateway.ack_spool.pending_payloads() == []


async def test_gateway_skips_sent_message_ack_without_bridge_token(tmp_path: Path) -> None:
    config = GatewayConfig(
        bridge_token="",
        gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
        whitelist_user_ids=frozenset({"42"}),
        owner_user_ids=frozenset({"42"}),
        group_trigger_prefixes=("xinyu",),
    )
    client = _FakeCoreClient(fail_ack=True)
    gateway = _AckGateway(config, client)
    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={"session_id": "qq:private:42", "message_id": "source-1"},
        route="chat",
    )

    await gateway._dispatch_prepared_message(None, prepared)

    assert client.acks == []
    assert gateway.ack_spool.pending_payloads() == []


def test_sent_reply_index_lookup_by_adapter_message_id(tmp_path: Path) -> None:
    register_sent_reply_ack(
        tmp_path,
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": "image-1,caption-2",
            "route": "qq_outbox_caption",
            "session_id": "qq:private:42",
            "turn_id": "turn-caption",
            "visible_text": "caption text",
        },
    )

    result = lookup_sent_reply_by_adapter_msg_id(tmp_path, "qq:caption-2")

    assert result["found"] is True
    assert result["entry"]["turn_id"] == "turn-caption"
