from __future__ import annotations

import xinyu_qq_rich_context as rich_context
from xinyu_qq_gateway import NativeQQGateway


def main() -> int:
    failures: list[str] = []

    if not rich_context.is_rich_context_segment("mface"):
        failures.append("mface should be a rich context segment")
    if rich_context.is_rich_context_segment("text"):
        failures.append("text should not be a rich context segment")
    if not rich_context.is_sticker_segment("dice"):
        failures.append("dice should be a sticker segment")

    sticker = rich_context.summarize_segment("mface", {"summary": "哈哈"})
    if sticker.get("kind") != "sticker" or sticker.get("mood") != "laugh":
        failures.append(f"sticker segment summary changed: {sticker!r}")
    image = rich_context.summarize_segment("image", {"name": "photo.jpg"})
    if image != {"kind": "image", "segment_type": "image", "name": "photo.jpg", "summary": "photo.jpg"}:
        failures.append(f"image segment summary changed: {image!r}")
    image_sticker = rich_context.summarize_segment("image", {"summary": "动画表情"})
    if image_sticker.get("kind") != "sticker" or image_sticker.get("segment_type") != "image":
        failures.append(f"image sticker segment summary changed: {image_sticker!r}")
    forward = rich_context.summarize_segment("forward", {"resid": "forward-1"})
    if forward != {"kind": "forward", "id": "forward-1", "summary": "forward-1"}:
        failures.append(f"forward segment summary changed: {forward!r}")

    gateway = object.__new__(NativeQQGateway)
    if NativeQQGateway._summarize_segment(gateway, "mface", {"summary": "哈哈"}).get("mood") != "laugh":
        failures.append("gateway rich context wrapper no longer delegates")

    if failures:
        print("XinYu QQ rich context smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ rich context smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
