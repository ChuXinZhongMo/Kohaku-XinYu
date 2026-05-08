from __future__ import annotations

import json
from pathlib import Path

from xinyu_qq_gateway import QQ_RECENT_STICKER_STATE_REL, GatewayConfig, NativeQQGateway, ReplyTarget


def main() -> int:
    failures: list[str] = []
    gateway = NativeQQGateway(GatewayConfig(require_whitelist=False, bridge_token=""))
    target = ReplyTarget(message_kind="private", user_id="42", group_id="")
    gateway._remember_recent_sticker_import(
        target=target,
        event={"message_id": "recent-sticker-smoke"},
        payload={
            "message_id": "recent-sticker-smoke",
            "file_id": "recent-smoke.webp",
            "metadata": {"message_id": "recent-sticker-smoke"},
        },
        status="completed",
        response={"accepted": True, "imported": True, "mood": "happy", "destination": "runtime-smoke"},
    )

    path = Path(__file__).resolve().parent / QQ_RECENT_STICKER_STATE_REL
    try:
        state = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"recent sticker state was not valid JSON: {type(exc).__name__}")
        state = {}

    expected = {
        "status": "completed",
        "message_id": "recent-sticker-smoke",
        "file_id": "recent-smoke.webp",
        "accepted": True,
        "imported": True,
        "mood": "happy",
        "destination": "runtime-smoke",
    }
    for key, wanted in expected.items():
        if state.get(key) != wanted:
            failures.append(f"recent sticker state {key} changed: {state.get(key)!r}")

    if failures:
        print("QQ recent sticker state smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ recent sticker state smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
