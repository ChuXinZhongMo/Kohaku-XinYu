from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

from xinyu_qq_gateway import GatewayConfig, NativeQQGateway
from xinyu_visible_reply_guard import dedupe_visible_reply


def main() -> int:
    failures: list[str] = []
    one = (
        "\u8fd8\u6ca1\u597d\u3002"
        "\u521a\u624d\u67e5\u4e86\u4e00\u4e0b\u62a5\u544a\u6587\u4ef6\uff0c"
        "\u6ca1\u627e\u5230\u3002"
        "\u6211\u518d\u770b\u770b\u6709\u6ca1\u6709\u522b\u7684\u72b6\u6001\u3002"
    )
    duplicated = one + one
    result = dedupe_visible_reply(duplicated)
    if result.text != one:
        failures.append("repeated sentence block was not collapsed")
    if not result.changed or "visible_reply_duplicate_sentence_removed" not in result.notes:
        failures.append("sentence dedupe note was not recorded")

    short_repetition = "\u55ef\u3002\u55ef\u3002"
    if dedupe_visible_reply(short_repetition).text != short_repetition:
        failures.append("short expressive repetition was over-deduped")

    paragraph = "A long visible paragraph with enough content."
    paragraph_result = dedupe_visible_reply(f"{paragraph}\n\n{paragraph}")
    if paragraph_result.text != paragraph:
        failures.append("repeated paragraph was not collapsed")

    writer_leak = "[/context_writer]\nanalysis\n[/emotion_writer]\n\u55ef... \u6709\u4e00\u70b9\u3002"
    writer_result = dedupe_visible_reply(writer_leak)
    if writer_result.text != "\u55ef... \u6709\u4e00\u70b9\u3002":
        failures.append("writer block leakage was not stripped")
    if "visible_writer_block_removed" not in writer_result.notes:
        failures.append("writer block strip note was not recorded")

    unclosed_writer = "[relationship_writer]\n\u55ef... \u6709\u4e00\u70b9\u3002"
    if dedupe_visible_reply(unclosed_writer).text != "\u55ef... \u6709\u4e00\u70b9\u3002":
        failures.append("visible tail after unclosed writer tag was not recovered")

    gateway = NativeQQGateway(GatewayConfig(send_replies=False))
    if gateway._visible_reply(duplicated) != one:
        failures.append("gateway visible send boundary did not dedupe")

    if failures:
        print("visible_reply_dedupe_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("visible_reply_dedupe_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
