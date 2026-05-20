from __future__ import annotations

import http.client
from pathlib import Path
from typing import Any

import pytest

import xinyu_qq_core_client
from xinyu_qq_core_client import CoreBridgeClient
from xinyu_qq_gateway import BridgeError, GatewayConfig, NativeQQGateway, PreparedMessage, ReplyTarget


def _core_client() -> CoreBridgeClient:
    return CoreBridgeClient(
        chat_url="http://127.0.0.1:8765/chat",
        codex_execute_url="",
        learning_ingest_url="",
        sticker_import_url="",
        package_install_url="",
        review_inbox_command_url="",
        goldmark_mark_url="",
        qq_outbox_claim_url="",
        qq_outbox_ack_url="",
        message_ack_url="",
        token="",
        timeout_seconds=1,
        gateway_version="test",
    )


def test_core_client_normalizes_remote_disconnected(monkeypatch: pytest.MonkeyPatch) -> None:
    class RemoteDisconnectedOpener:
        def open(self, request: Any, timeout: int) -> object:
            raise http.client.RemoteDisconnected("remote end closed connection without response")

    monkeypatch.setattr(xinyu_qq_core_client, "NO_PROXY_OPENER", RemoteDisconnectedOpener())
    client = _core_client()

    with pytest.raises(BridgeError) as caught:
        client._post_json(client.chat_url, {"text": "hi"})

    message = str(caught.value)
    assert "core bridge connection failed" in message
    assert "remote end closed" in message


class _FlakyChatClient:
    def __init__(self, first_error: str) -> None:
        self.first_error = first_error
        self.calls = 0

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            raise BridgeError(self.first_error)
        return {"accepted": True, "reply": "after retry", "echo": payload.get("text", "")}


class _RetryGateway(NativeQQGateway):
    def __init__(self, tmp_path: Path, client: _FlakyChatClient) -> None:
        super().__init__(
            GatewayConfig(
                bridge_token="token",
                gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
                whitelist_user_ids=frozenset({"42"}),
                owner_user_ids=frozenset({"42"}),
                owner_private_coalesce_seconds=0.0,
            )
        )
        self.client = client
        self.sleep_count = 0
        self.traces: list[dict[str, str]] = []

    async def _sleep_before_core_chat_retry(self) -> None:
        self.sleep_count += 1

    def _trace_qq_inbound(
        self,
        event: dict[str, Any],
        *,
        stage: str,
        arrival_seq: int = 0,
        prepared: PreparedMessage | None = None,
        session_queue_key: str = "",
        queue_depth: int | None = None,
        drop_reason: str = "",
        error: str = "",
    ) -> None:
        del event, prepared, session_queue_key, queue_depth
        self.traces.append({"stage": stage, "drop_reason": drop_reason, "error": error})


def _prepared() -> PreparedMessage:
    return PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={
            "text": "hello",
            "session_id": "qq:private:42",
            "metadata": {"qq_arrival_seq": 7, "qq_session_queue_hash": "queue-1"},
        },
        route="chat",
    )


async def test_gateway_retries_core_chat_connection_reset_once(tmp_path: Path) -> None:
    client = _FlakyChatClient("core bridge connection failed: [WinError 10054] connection reset by peer")
    gateway = _RetryGateway(tmp_path, client)

    response = await gateway._chat_with_core_retry(
        {"text": "hello"},
        prepared=_prepared(),
        event={"post_type": "message", "message_type": "private", "user_id": 42},
        metadata={"qq_arrival_seq": 7, "qq_session_queue_hash": "queue-1"},
    )

    assert response["reply"] == "after retry"
    assert client.calls == 2
    assert gateway.sleep_count == 1
    assert gateway.traces == [
        {
            "stage": "core_chat_retry_after_connection_reset",
            "drop_reason": "core_bridge_connection_reset_retry",
            "error": "BridgeError: core bridge connection failed: [WinError 10054] connection reset by peer",
        }
    ]


async def test_gateway_does_not_retry_non_connection_bridge_error(tmp_path: Path) -> None:
    client = _FlakyChatClient("core bridge HTTP 500: boom")
    gateway = _RetryGateway(tmp_path, client)

    with pytest.raises(BridgeError):
        await gateway._chat_with_core_retry(
            {"text": "hello"},
            prepared=_prepared(),
            event={"post_type": "message", "message_type": "private", "user_id": 42},
            metadata={"qq_arrival_seq": 7, "qq_session_queue_hash": "queue-1"},
        )

    assert client.calls == 1
    assert gateway.sleep_count == 0
    assert gateway.traces == []
