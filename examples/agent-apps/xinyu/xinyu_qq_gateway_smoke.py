from __future__ import annotations

from xinyu_qq_gateway import GatewayConfig, NativeQQGateway


def main() -> int:
    config = GatewayConfig(
        whitelist_user_ids=frozenset({"42"}),
        owner_user_ids=frozenset({"42"}),
        group_trigger_prefixes=("心玉", "@心玉", "小心玉"),
    )
    gateway = NativeQQGateway(config)

    private_event = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 42,
        "self_id": 99,
        "message_id": 1001,
        "message": [{"type": "text", "data": {"text": "你好"}}],
        "raw_message": "你好",
        "sender": {"nickname": "owner"},
        "time": 1770000000,
    }
    private_prepared = gateway.prepare_message(private_event)
    assert private_prepared is not None
    assert private_prepared.target.message_kind == "private"
    assert private_prepared.payload["platform"] == "qq"
    assert private_prepared.payload["adapter"] == "xinyu_native_qq_gateway"
    assert private_prepared.payload["text"] == "你好"
    assert private_prepared.payload["metadata"]["is_owner_user"] is True

    ignored_group = {
        "post_type": "message",
        "message_type": "group",
        "group_id": 7,
        "user_id": 42,
        "self_id": 99,
        "message": [{"type": "text", "data": {"text": "普通群聊"}}],
        "raw_message": "普通群聊",
    }
    assert gateway.prepare_message(ignored_group) is None

    prefixed_group = dict(ignored_group)
    prefixed_group["message"] = [{"type": "text", "data": {"text": "心玉 看一下"}}]
    prefixed_group["raw_message"] = "心玉 看一下"
    group_prepared = gateway.prepare_message(prefixed_group)
    assert group_prepared is not None
    assert group_prepared.target.message_kind == "group"
    assert group_prepared.payload["text"] == "看一下"
    assert group_prepared.payload["session_id"] == "qq:group:7:42"

    at_group = dict(ignored_group)
    at_group["message"] = [
        {"type": "at", "data": {"qq": "99"}},
        {"type": "text", "data": {"text": "在吗"}},
    ]
    at_group["raw_message"] = "[CQ:at,qq=99] 在吗"
    at_prepared = gateway.prepare_message(at_group)
    assert at_prepared is not None
    assert at_prepared.payload["text"] == "在吗"

    print("xinyu_qq_gateway_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
