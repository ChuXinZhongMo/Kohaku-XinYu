from __future__ import annotations

from xinyu_qq_gateway import PreparedMessage as GatewayPreparedMessage
from xinyu_qq_gateway import ReplyTarget as GatewayReplyTarget
from xinyu_qq_models import PreparedMessage, RecentStickerImportState, ReplyTarget


def main() -> int:
    failures: list[str] = []
    target = ReplyTarget(message_kind="private", user_id="42", group_id="")
    prepared = PreparedMessage(target=target, payload={"text": "hello"})
    state = RecentStickerImportState(target=target, event={}, payload={})

    if prepared.route != "chat" or prepared.local_reply != "":
        failures.append("prepared message defaults changed")
    if state.status != "pending" or state.response != {}:
        failures.append("recent sticker state defaults changed")
    if GatewayReplyTarget is not ReplyTarget or GatewayPreparedMessage is not PreparedMessage:
        failures.append("gateway model compatibility exports changed")

    if failures:
        print("QQ models smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ models smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
