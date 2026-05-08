from __future__ import annotations

from xinyu_qq_gateway import NativeQQGateway
from xinyu_qq_normalizer import (
    clean_cq_text_value,
    cq_bracket_continues_params,
    decode_cq_value,
    extract_text,
    message_kind,
    message_segments_from_event,
    parse_cq_params,
    parse_cq_segments,
    parse_ws_message,
    sender_name,
    strip_cq_segments,
)


def main() -> int:
    failures: list[str] = []

    raw_params = "text=hello&#44;%E4%B8%96%E7%95%8C,file=a%5Db"
    if NativeQQGateway._parse_cq_params(raw_params) != parse_cq_params(raw_params):
        failures.append("gateway CQ params alias no longer delegates")
    if NativeQQGateway._decode_cq_value("a&#91;b&#93;&amp;c") != decode_cq_value("a&#91;b&#93;&amp;c"):
        failures.append("gateway CQ decode alias no longer delegates")

    raw_message = "hello[CQ:image,file=a.jpg,url=http%3A%2F%2Fx]world"
    if NativeQQGateway._parse_cq_segments(raw_message) != parse_cq_segments(raw_message):
        failures.append("gateway CQ segment parser alias no longer delegates")
    if NativeQQGateway._strip_cq_segments(raw_message) != strip_cq_segments(raw_message):
        failures.append("gateway CQ strip alias no longer delegates")
    if clean_cq_text_value(" [CQ:image,file=a.jpg] hello ") != "hello":
        failures.append("clean CQ text value helper changed")
    if NativeQQGateway._clean_cq_text is not clean_cq_text_value:
        failures.append("gateway clean CQ text helper is not a direct static alias")
    if NativeQQGateway._clean_cq_text(" [CQ:image,file=a.jpg] hello ") != clean_cq_text_value(
        " [CQ:image,file=a.jpg] hello "
    ):
        failures.append("gateway clean CQ text alias no longer delegates")

    tricky = "[CQ:json,data={\"x\"] ,still=params]"
    bracket_index = tricky.find("]")
    if NativeQQGateway._cq_bracket_continues_params(tricky, bracket_index) != cq_bracket_continues_params(
        tricky, bracket_index
    ):
        failures.append("gateway CQ bracket continuation alias no longer delegates")

    gateway = object.__new__(NativeQQGateway)
    group_event = {"message_type": "private", "group_id": "10001"}
    if NativeQQGateway._message_kind is not message_kind:
        failures.append("gateway message kind helper is not a direct method alias")
    if gateway._message_kind(group_event) != message_kind(gateway, group_event):
        failures.append("gateway message kind alias no longer delegates")

    segment_event = {"message": [{"type": "text", "data": {"text": "hello"}}, "bad"]}
    if NativeQQGateway._message_segments is not message_segments_from_event:
        failures.append("gateway message segments helper is not a direct static alias")
    if NativeQQGateway._message_segments(segment_event) != message_segments_from_event(segment_event):
        failures.append("gateway message segments alias no longer delegates")

    text_event = {"message": [{"type": "text", "data": {"text": "hello"}}, {"type": "image", "data": {}}]}
    if NativeQQGateway._extract_text is not extract_text:
        failures.append("gateway extract text helper is not a direct method alias")
    if gateway._extract_text(text_event) != extract_text(gateway, text_event):
        failures.append("gateway extract text alias no longer delegates")

    sender_event = {"sender": {"card": "Owner", "nickname": "Nick", "user_id": "42"}}
    if NativeQQGateway._sender_name is not sender_name:
        failures.append("gateway sender name helper is not a direct method alias")
    if gateway._sender_name(sender_event) != sender_name(gateway, sender_event):
        failures.append("gateway sender name alias no longer delegates")

    raw_ws_message = b'{"post_type":"message","message_type":"private"}'
    if NativeQQGateway._parse_ws_message is not parse_ws_message:
        failures.append("gateway websocket parser helper is not a direct method alias")
    if gateway._parse_ws_message(raw_ws_message) != parse_ws_message(gateway, raw_ws_message):
        failures.append("gateway websocket parser alias no longer delegates")

    if failures:
        print("XinYu QQ normalizer aliases smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ normalizer aliases smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
