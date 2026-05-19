from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from xinyu_core_bridge import XinYuBridgeRuntime


def main() -> int:
    failures: list[str] = []
    tail = [{"role": "assistant", "content": "1 2 3 4 5 6 7 8 9 10"}]
    units = XinYuBridgeRuntime._owner_requested_reply_bubble_units(
        user_text="每个数字单独发出来这样数",
        reply="我一次只能发一条，没法拆成十句发出去。",
        dialogue_tail=tail,
    )
    if units != [str(value) for value in range(1, 11)]:
        failures.append(f"explicit numeric split request was not converted to forced units: {units}")

    ranged_units = XinYuBridgeRuntime._owner_requested_reply_bubble_units(
        user_text="从1数到5，一个数字一条",
        reply="可以",
        dialogue_tail=[],
    )
    if ranged_units != ["1", "2", "3", "4", "5"]:
        failures.append(f"numeric range split request failed: {ranged_units}")

    if not XinYuBridgeRuntime._looks_like_false_single_bubble_limitation(
        "每个数字单独发出来这样数",
        "我一次只能发一条，没法拆成十句发出去。",
    ):
        failures.append("false single-message limitation was not detected")

    if XinYuBridgeRuntime._looks_like_false_single_bubble_limitation(
        "长句分段自然一点",
        "可以，我按自然停顿拆。",
    ):
        failures.append("ordinary rhythm request was incorrectly treated as false limitation")

    if failures:
        print("xinyu_reply_bubble_force_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("xinyu_reply_bubble_force_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
