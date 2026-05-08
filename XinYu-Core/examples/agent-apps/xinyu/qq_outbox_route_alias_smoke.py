from __future__ import annotations

import asyncio
from types import SimpleNamespace

import xinyu_qq_outbox_client as outbox_client
from xinyu_qq_gateway import NativeQQGateway, PreparedMessage, ReplyTarget
from xinyu_qq_outbox_client import sent_outbox_delivery_route


def main() -> int:
    failures: list[str] = []

    cases = [
        ("outbox-1", "text"),
        ("outbox-1", "image"),
        ("outbox-1", "caption"),
        ("proactive:abc", "text"),
        ("proactive:abc", "caption"),
    ]
    for message_id, delivery_kind in cases:
        gateway_route = NativeQQGateway._sent_outbox_delivery_route(message_id, delivery_kind)
        client_route = sent_outbox_delivery_route(message_id, delivery_kind)
        if gateway_route != client_route:
            failures.append(f"outbox route alias changed for {message_id}/{delivery_kind}: {gateway_route} != {client_route}")

    gateway = object.__new__(NativeQQGateway)
    ok_response = {"status": "ok", "data": {"message_id": "qq-msg-1"}}
    if NativeQQGateway._onebot_action_result is not outbox_client.onebot_action_result:
        failures.append("gateway OneBot action result helper is not a direct method alias")
    if gateway._onebot_action_result(ok_response) != outbox_client.onebot_action_result(gateway, ok_response):
        failures.append("gateway OneBot action result alias no longer delegates")

    outbox_claim = {
        "target": {
            "message_kind": "private",
            "user_id": "42",
            "group_id": "",
        },
    }
    if NativeQQGateway._outbox_target is not outbox_client.gateway_outbox_target:
        failures.append("gateway outbox target helper is not a direct method alias")
    target = gateway._outbox_target(outbox_claim)
    if target != ReplyTarget(message_kind="private", user_id="42", group_id=""):
        failures.append("gateway outbox target alias no longer delegates")
    group_claim = {"target": {"message_kind": "group", "user_id": "42", "group_id": "7"}}
    if gateway._outbox_target(group_claim) is not None:
        failures.append("gateway outbox target alias started accepting non-private target")
    if NativeQQGateway._outbox_message_ack_payload is not outbox_client.outbox_message_ack_payload:
        failures.append("gateway outbox message ack payload helper is not a direct method alias")
    outbox_ack_payload = gateway._outbox_message_ack_payload(
        {
            "message_id": "outbox-1",
            "source": "smoke",
            "message_type": "text",
            "metadata": {"session_id": "qq:private:42"},
        },
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        visible_text="sent reply",
        adapter_message_id="qq-msg-2",
        delivery_kind="text",
    )
    if outbox_ack_payload.get("adapter_message_id") != "qq-msg-2":
        failures.append("gateway outbox message ack payload alias changed adapter id")
    if outbox_ack_payload.get("target", {}).get("user_id") != "42":
        failures.append("gateway outbox message ack payload alias changed target")
    if NativeQQGateway._ack_qq_outbox is not outbox_client.ack_qq_outbox:
        failures.append("gateway QQ outbox ack helper is not a direct method alias")

    class _Client:
        def __init__(self) -> None:
            self.ack_payloads: list[dict[str, str]] = []
            self.message_ack_payloads: list[dict[str, str]] = []

        async def qq_outbox_ack(self, payload: dict[str, str]) -> dict[str, bool]:
            self.ack_payloads.append(dict(payload))
            return {"accepted": True}

        async def message_ack(self, payload: dict[str, str]) -> dict[str, bool]:
            self.message_ack_payloads.append(dict(payload))
            return {"accepted": True}

    gateway.client = _Client()
    asyncio.run(
        gateway._ack_qq_outbox(
            {"message_id": "outbox-1", "claim_id": "claim-1"},
            status="sent",
            adapter_message_id="qq-msg-3",
        )
    )
    if gateway.client.ack_payloads[-1].get("adapter_message_id") != "qq-msg-3":
        failures.append("gateway QQ outbox ack alias changed adapter message id")
    if NativeQQGateway._record_sent_message_ack_payload is not outbox_client.record_sent_message_ack_payload:
        failures.append("gateway sent-message ack record helper is not a direct method alias")
    gateway.config = SimpleNamespace(bridge_token="", message_ack_url="")
    record_result = asyncio.run(gateway._record_sent_message_ack_payload({"adapter_message_id": "qq-msg-4"}))
    if record_result:
        failures.append("gateway sent-message ack record alias ignored disabled bridge token")
    if NativeQQGateway._ack_sent_outbox_delivery is not outbox_client.ack_sent_outbox_delivery:
        failures.append("gateway sent outbox delivery ack helper is not a direct method alias")
    asyncio.run(
        gateway._ack_sent_outbox_delivery(
            {
                "message_id": "outbox-2",
                "source": "smoke",
                "message_type": "text",
                "metadata": {"session_id": "qq:private:42"},
            },
            target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
            visible_text="sent reply",
            adapter_message_id="qq-msg-6",
            delivery_kind="text",
        )
    )
    if gateway.client.message_ack_payloads:
        failures.append("gateway sent outbox delivery ack alias ignored disabled bridge token")

    class _AckSpool:
        def __init__(self) -> None:
            self.pending_payloads: list[dict[str, str]] = []
            self.acked_payloads: list[dict[str, str]] = []

        def append_pending(self, payload: dict[str, str]) -> dict[str, bool]:
            self.pending_payloads.append(dict(payload))
            return {"queued": True}

        def append_acked(self, payload: dict[str, str]) -> dict[str, bool]:
            self.acked_payloads.append(dict(payload))
            return {"acked": True}

    gateway.ack_spool = _AckSpool()
    pending_payload = {"adapter_message_id": "qq-msg-1"}
    if NativeQQGateway._spool_pending_message_ack is not outbox_client.spool_pending_message_ack:
        failures.append("gateway pending ack spool helper is not a direct method alias")
    if not gateway._spool_pending_message_ack(pending_payload):
        failures.append("gateway pending ack spool alias no longer delegates")
    if NativeQQGateway._spool_acked_message_ack is not outbox_client.spool_acked_message_ack:
        failures.append("gateway acked spool helper is not a direct method alias")
    if not gateway._spool_acked_message_ack(pending_payload):
        failures.append("gateway acked spool alias no longer delegates")
    if NativeQQGateway._send_message_ack_payload is not outbox_client.send_message_ack_payload:
        failures.append("gateway send message ack payload helper is not a direct method alias")
    send_ok = asyncio.run(
        gateway._send_message_ack_payload(
            {"adapter_message_id": "qq-msg-5"},
            mark_acked=True,
            spool_on_failure=False,
        )
    )
    if not send_ok:
        failures.append("gateway send message ack payload alias stopped accepting successful send")
    if gateway.client.message_ack_payloads[-1].get("adapter_message_id") != "qq-msg-5":
        failures.append("gateway send message ack payload alias changed sent payload")
    if gateway.ack_spool.acked_payloads[-1].get("adapter_message_id") != "qq-msg-5":
        failures.append("gateway send message ack payload alias stopped marking acked payload")
    if NativeQQGateway._poll_pending_message_acks is not outbox_client.poll_pending_message_acks:
        failures.append("gateway pending message ack poll helper is not a direct method alias")

    prepared = PreparedMessage(
        target=ReplyTarget(message_kind="private", user_id="42", group_id=""),
        payload={"session_id": "qq:private:42", "message_id": "source-1"},
        route="chat",
    )
    core_response = {"session_id": "qq:private:42", "turn_id": "turn-1", "reply_hash": "sha256:reply"}
    if NativeQQGateway._sent_message_ack_payload is not outbox_client.sent_message_ack_payload:
        failures.append("gateway sent-message ack payload helper is not a direct method alias")
    ack_payload = gateway._sent_message_ack_payload(
        prepared,
        reply="visible reply",
        core_response=core_response,
        action_response=ok_response,
    )
    if ack_payload.get("adapter_message_id") != "qq-msg-1" or ack_payload.get("visible_text") != "visible reply":
        failures.append("gateway sent-message ack payload alias no longer delegates")
    if NativeQQGateway._ack_sent_visible_reply is not outbox_client.ack_sent_visible_reply:
        failures.append("gateway sent visible reply ack helper is not a direct method alias")
    asyncio.run(
        gateway._ack_sent_visible_reply(
            prepared,
            reply="visible reply",
            core_response=core_response,
            action_response=ok_response,
        )
    )
    if len(gateway.client.message_ack_payloads) != 1:
        failures.append("gateway sent visible reply ack alias ignored disabled bridge token")
    if NativeQQGateway._flush_pending_message_acks is not outbox_client.flush_pending_message_acks:
        failures.append("gateway pending ack flush helper is not a direct method alias")

    if failures:
        print("XinYu QQ outbox route alias smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ outbox route alias smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
