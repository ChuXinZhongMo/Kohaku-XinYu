from __future__ import annotations

from xinyu_bridge_recent_sticker_reply import (
    current_sticker_question_reply,
    is_recent_sticker_question,
    recent_sticker_question_reply,
)
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    if not is_recent_sticker_question("刚才那个表情是什么"):
        failures.append("recent sticker exact question marker changed")
    if is_recent_sticker_question("刚才天气怎么样"):
        failures.append("non-sticker recent question should not match")

    current = current_sticker_question_reply(
        "我刚发了什么",
        {
            "metadata": {
                "recent_sticker_question": True,
                "sticker_import_completed": True,
                "sticker_mood_label": "困惑",
                "sticker_confidence": "low",
                "qq_image_context": {"meaning": "在试探"},
            }
        },
    )
    if current != "你刚发的是偏困惑的表情包。看起来是在试探。不过这个判断不太稳。":
        failures.append(f"current sticker reply changed: {current}")

    unavailable = current_sticker_question_reply(
        "刚发的是什么",
        {"metadata": {"recent_sticker_unavailable": True}},
    )
    if "没抓到具体画面" not in unavailable:
        failures.append("recent sticker unavailable reply changed")

    from_tail = recent_sticker_question_reply(
        "刚那个表情是什么",
        [
            {
                "role": "user",
                "content": "ignored",
            },
            {
                "role": "assistant",
                "content": "【收到的表情记录】分类=开心；语义=在打招呼；置信度=high",
            },
        ],
    )
    if from_tail != "你刚发的是偏开心的表情包。看起来是在打招呼。":
        failures.append(f"recent sticker tail reply changed: {from_tail}")

    if (
        XinYuBridgeRuntime._is_recent_sticker_question("刚才那个表情是什么") is not True
        or XinYuBridgeRuntime._current_sticker_question_reply(
            "我刚发了什么",
            {"metadata": {"recent_sticker_question": True, "sticker_import_completed": True}},
        )
        != "你刚发的是一张表情包。"
        or XinYuBridgeRuntime._recent_sticker_question_reply("刚那个表情是什么", []) != ""
    ):
        failures.append("core bridge recent sticker static aliases changed")

    if failures:
        print("XinYu bridge recent sticker reply smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge recent sticker reply smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
