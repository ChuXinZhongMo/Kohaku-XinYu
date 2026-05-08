from __future__ import annotations

import xinyu_qq_forward_context as forward_context
from xinyu_qq_gateway import NativeQQGateway


def main() -> int:
    failures: list[str] = []

    payload = {
        "data": {
            "messages": [
                {"message_id": "1", "sender": {"nickname": "a"}, "message": "hello"},
                {"message_id": "2", "sender": {"nickname": "b"}, "message": "world"},
            ]
        }
    }
    raw_items = forward_context.forward_raw_items(payload)
    if len(raw_items) != 2 or raw_items[0].get("message_id") != "1":
        failures.append(f"nested forward raw item extraction changed: {raw_items!r}")

    raw_json = '[{"message_id": "3", "raw_message": "json item"}]'
    if forward_context.forward_raw_items(raw_json)[0].get("message_id") != "3":
        failures.append("JSON string forward raw item extraction changed")
    if forward_context.forward_raw_items("plain text") != ["plain text"]:
        failures.append("plain string forward raw item fallback changed")
    reply_event = {"raw_message": "[CQ:reply,id=reply-1]hello"}
    if forward_context.extract_reply_message_id(reply_event) != "reply-1":
        failures.append("CQ reply id extraction changed")
    forward_event = {
        "message": [
            {
                "type": "json",
                "data": {"data": '{"app":"com.tencent.multimsg","meta":{"detail":{"resid":"forward-1"}}}'},
            }
        ],
        "raw_message": "",
    }
    if forward_context.extract_forward_message_ids(forward_event) != ["forward-1"]:
        failures.append("forward id extraction from JSON segment changed")
    if forward_context.extract_forward_ids_from_text("m_resid=forward-2") != ["forward-2"]:
        failures.append("forward id regex extraction changed")

    messages = [
        {"message_id": "1", "sender_name": "a", "text": "same", "rich_summary": "", "raw_message": ""},
        {"message_id": "1", "sender_name": "a", "text": "same", "rich_summary": "", "raw_message": ""},
        {"message_id": "2", "sender_name": "a", "text": "same", "rich_summary": "", "raw_message": ""},
    ]
    deduped = forward_context.dedupe_forward_messages(messages)
    if [item["message_id"] for item in deduped] != ["1", "2"]:
        failures.append(f"forward message de-duplication changed: {deduped!r}")

    if NativeQQGateway._forward_raw_items(raw_json)[0].get("message_id") != "3":
        failures.append("gateway forward raw item wrapper no longer delegates")
    if NativeQQGateway._extract_forward_ids_from_text("forward_id=forward-3") != ["forward-3"]:
        failures.append("gateway forward id text wrapper no longer delegates")
    if NativeQQGateway._dedupe_forward_messages(messages) != deduped:
        failures.append("gateway forward de-duplication wrapper no longer delegates")

    if failures:
        print("XinYu QQ forward context smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ forward context smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
