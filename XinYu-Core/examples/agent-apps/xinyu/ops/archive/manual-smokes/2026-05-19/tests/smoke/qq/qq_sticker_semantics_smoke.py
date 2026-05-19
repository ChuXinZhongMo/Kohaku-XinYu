from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_qq_gateway import NativeQQGateway
from xinyu_qq_sticker_semantics import image_segment_looks_like_sticker, infer_received_sticker_semantics


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
    if NativeQQGateway._infer_received_sticker_semantics is not infer_received_sticker_semantics:
        failures.append("gateway sticker semantics helper is not a direct alias")
    if gateway_result.get("mood") != "comfort":
        failures.append("gateway sticker semantics wrapper no longer delegates")
    if not image_segment_looks_like_sticker({"summary": "动画表情", "name": ""}):
        failures.append("image sticker marker detection changed")
    if image_segment_looks_like_sticker({"summary": "ordinary photo", "name": "photo.jpg"}):
        failures.append("ordinary image should not be treated as sticker")
    if NativeQQGateway._image_segment_looks_like_sticker is not image_segment_looks_like_sticker:
        failures.append("gateway image sticker helper is not a direct alias")
    if not NativeQQGateway._image_segment_looks_like_sticker({"image_type": "mface"}):
        failures.append("gateway image sticker wrapper no longer delegates")

    if failures:
        print("XinYu QQ sticker semantics smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu QQ sticker semantics smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
