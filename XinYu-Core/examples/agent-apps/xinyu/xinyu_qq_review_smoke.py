from __future__ import annotations

import os
import tempfile
from pathlib import Path

from xinyu_local_scope import ensure_local_scope
from xinyu_qq_review import (
    classify_pair,
    pair_turns,
    parse_transcript,
    write_review_outputs,
)


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["XINYU_LOCAL_SCOPE_DIR"] = str(Path(temp_dir) / "scope")
        scope = ensure_local_scope(Path(os.environ["XINYU_LOCAL_SCOPE_DIR"]))
        inbox = scope / "Inbox"
        review_dir = scope / "Workspace" / "QQ-Review"
        transcript = inbox / "fixture.md"
        transcript.write_text(
            "\n".join(
                [
                    "我: 你刚刚那句话AI味太重了，别解释一堆。",
                    "心玉: 嗯，我理解你的感受，你的反馈很重要，我会持续优化我的输出。",
                    "",
                    "我: 在吗？只能短一点回。",
                    "心玉: 在。",
                ]
            )
            + "\n",
            encoding="utf-8-sig",
        )

        messages = parse_transcript(transcript)
        pairs = pair_turns(messages)
        if len(messages) != 4:
            failures.append(f"expected 4 messages, got {len(messages)}")
        if len(pairs) != 2:
            failures.append(f"expected 2 pairs, got {len(pairs)}")

        items = [classify_pair(index, user, assistant) for index, (user, assistant) in enumerate(pairs, 1)]
        first = items[0]
        second = items[1]
        if first.overall not in {"high_risk", "needs_review"}:
            failures.append(f"first pair should need review, got {first.overall}")
        for required_label in ("owner_style_correction", "customer_service_tone", "product_or_system_words"):
            if required_label not in first.labels:
                failures.append(f"first pair missing label: {required_label}")
        if "候选写入 voice_calibration_log" not in first.recommended_actions:
            failures.append("first pair missing voice calibration action")
        if second.overall != "good_example":
            failures.append(f"second pair should be good_example, got {second.overall}")

        markdown_path, jsonl_path = write_review_outputs(items, source=transcript, review_dir=review_dir)
        markdown = markdown_path.read_text(encoding="utf-8-sig")
        jsonl = jsonl_path.read_text(encoding="utf-8")
        if "owner_confirm" not in markdown or "add_to_voice_calibration" not in markdown:
            failures.append("markdown review missing owner confirmation controls")
        if '"owner_decision": "pending"' not in jsonl:
            failures.append("jsonl review missing pending owner decision")

    if failures:
        print("QQ review smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("QQ review smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
