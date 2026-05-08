from __future__ import annotations

from xinyu_qq_gateway import NativeQQGateway
from xinyu_qq_sticker_semantics import infer_received_sticker_semantics


def main() -> int:
    failures: list[str] = []

    laugh = infer_received_sticker_semantics("哈哈 笑死")
    if laugh != {"mood": "laugh", "meaning": "大笑、觉得好笑、跟着一起乐", "confidence": "medium"}:
        failures.append(f"laugh sticker semantics changed: {laugh!r}")

    confused = infer_received_sticker_semantics("WHAT?")
    if confused.get("mood") != "confused" or confused.get("confidence") != "medium":
        failures.append(f"English sticker marker semantics changed: {confused!r}")

    unclear = infer_received_sticker_semantics("unmapped sticker summary")
    if unclear != {"mood": "unclear", "meaning": "QQ 只给了表情摘要，具体语气不确定", "confidence": "low"}:
        failures.append(f"unclear sticker semantics changed: {unclear!r}")

    gateway_result = NativeQQGateway._infer_received_sticker_semantics("抱抱")
    if gateway_result.get("mood") != "comfort":
        failures.append("gateway sticker semantics wrapper no longer delegates")

    if failures:
        print("XinYu QQ sticker semantics smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ sticker semantics smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
