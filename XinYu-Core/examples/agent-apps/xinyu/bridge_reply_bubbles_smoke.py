from __future__ import annotations

from xinyu_bridge_reply_bubbles import (
    looks_like_false_single_bubble_limitation,
    numeric_bubble_units_from_text,
    owner_requested_reply_bubble_units,
)
from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []

    if numeric_bubble_units_from_text("1, 2, 3, 4") != ["1", "2", "3", "4"]:
        failures.append("numeric bubble sequence parsing changed")
    if numeric_bubble_units_from_text("1, 3, 4") != []:
        failures.append("non-contiguous numeric bubble sequence should not pass")

    ranged = owner_requested_reply_bubble_units(
        user_text="从 3 到 1，一个数字一条",
        reply="ok",
        dialogue_tail=[],
    )
    if ranged != ["3", "2", "1"]:
        failures.append(f"reverse numeric bubble range changed: {ranged}")

    from_tail = owner_requested_reply_bubble_units(
        user_text="每个数字单独发出来",
        reply="我做不到",
        dialogue_tail=[{"role": "assistant", "content": "1 2 3"}],
    )
    if from_tail != ["1", "2", "3"]:
        failures.append(f"numeric bubble fallback to assistant tail changed: {from_tail}")

    if not looks_like_false_single_bubble_limitation("每个数字单独发", "一次只能发一条"):
        failures.append("false single bubble limitation detection changed")
    if looks_like_false_single_bubble_limitation("自然一点", "我会自然一点"):
        failures.append("ordinary reply should not be treated as false single bubble limitation")

    if (
        XinYuBridgeRuntime._numeric_bubble_units_from_text("1 2") != numeric_bubble_units_from_text("1 2")
        or XinYuBridgeRuntime._owner_requested_reply_bubble_units(
            user_text="每个数字单独发出来",
            reply="1 2",
            dialogue_tail=[],
        )
        != ["1", "2"]
        or XinYuBridgeRuntime._looks_like_false_single_bubble_limitation("每个数字单独发", "只能发一条")
        is not True
    ):
        failures.append("core bridge reply bubble static aliases changed")

    if failures:
        print("XinYu bridge reply bubbles smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu bridge reply bubbles smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
