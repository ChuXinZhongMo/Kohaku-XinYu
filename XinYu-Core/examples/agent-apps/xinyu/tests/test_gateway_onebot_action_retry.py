from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from xinyu_qq_gateway import GatewayConfig, NativeQQGateway


class _RetryWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(self, raw: str) -> None:
        self.sent.append(json.loads(raw))


async def test_send_action_retries_after_timeout(tmp_path: Path) -> None:
    config = GatewayConfig(
        bridge_token="token",
        gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
        onebot_action_timeout_seconds=0.2,
        onebot_action_max_retries=1,
        onebot_action_retry_delay_seconds=0.05,
    )
    gateway = NativeQQGateway(config)
    websocket = _RetryWebSocket()
    gateway._websocket_connection_ids[id(websocket)] = "conn-a"
    gateway._live_napcat_websocket = websocket

    task = asyncio.create_task(gateway.send_action(websocket, "send_private_msg", {"user_id": 42, "message": "hi"}))
    await asyncio.sleep(0.05)
    assert len(websocket.sent) == 1

    await asyncio.sleep(0.3)
    assert len(websocket.sent) == 2

    second_echo = websocket.sent[1]["echo"]
    gateway._complete_action_response(
        {"echo": second_echo, "status": "ok", "retcode": 0, "data": {"message_id": "adapter-2"}},
        "conn-a",
    )
    response = await task
    assert response is not None
    assert response["data"]["message_id"] == "adapter-2"


async def test_send_action_injects_message_timeout_ms(tmp_path: Path) -> None:
    config = GatewayConfig(
        bridge_token="token",
        gateway_ack_spool_path=str(tmp_path / "runtime/gateway_ack_spool.jsonl"),
        onebot_action_timeout_seconds=45,
        onebot_action_max_retries=0,
    )
    gateway = NativeQQGateway(config)
    websocket = _RetryWebSocket()
    gateway._websocket_connection_ids[id(websocket)] = "conn-a"
    gateway._live_napcat_websocket = websocket

    task = asyncio.create_task(gateway.send_action(websocket, "send_private_msg", {"user_id": 42, "message": "hi"}))
    await asyncio.sleep(0.01)
    assert websocket.sent[0]["params"]["timeout"] == 45000
    gateway._complete_action_response(
        {"echo": websocket.sent[0]["echo"], "status": "ok", "retcode": 0, "data": {"message_id": "adapter-1"}},
        "conn-a",
    )
    await task