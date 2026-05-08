from __future__ import annotations

import xinyu_qq_outbox_client as outbox_client
from xinyu_qq_gateway import NativeQQGateway
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

    if failures:
        print("XinYu QQ outbox route alias smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ outbox route alias smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
