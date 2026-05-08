from __future__ import annotations

from xinyu_qq_gateway import NativeQQGateway
from xinyu_qq_normalizer import (
    cq_bracket_continues_params,
    decode_cq_value,
    message_kind,
    parse_cq_params,
    parse_cq_segments,
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

    if failures:
        print("XinYu QQ normalizer aliases smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ normalizer aliases smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
