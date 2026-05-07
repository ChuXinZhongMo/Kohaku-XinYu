from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from xinyu_voice_learning import record_voice_correction, should_record_voice_correction


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []

    if not should_record_voice_correction("这句GPT味太重了，用词不像中文互联网。"):
        failures.append("style correction marker was not detected")
    if not should_record_voice_correction("每次出来都像隔着一层，像在念别人写的稿子。"):
        failures.append("layered/scripted voice correction marker was not detected")
    if should_record_voice_correction("我刚泡了碗面，有点咸。"):
        failures.append("ordinary daily chat should not trigger voice correction")

    with tempfile.TemporaryDirectory(prefix="xinyu-voice-learning-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/self"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "memory/self/voice_calibration_log.md", target / "voice_calibration_log.md")
        changed = record_voice_correction(
            temp_root,
            user_text="用词不像中文互联网，GPT味太重，真的红温。",
            reply="我理解你的反馈，会持续优化系统输出。",
            source="smoke",
            recorded_at="2026-04-26T17:20:00+08:00",
        )
        if not changed:
            failures.append("voice correction was not recorded")
        text = (target / "voice_calibration_log.md").read_text(encoding="utf-8")
        for marker in (
            "owner_correction: 用词不像中文互联网",
            "reply_product_word_hits:",
            "stable_profile_write: blocked",
            "中文私聊词感",
            "bad_example_omitted",
        ):
            if marker not in text:
                failures.append(f"recorded log missing marker: {marker}")
        if "我理解你的反馈，会持续优化系统输出" in text:
            failures.append("raw bad visible reply should not be injected into voice calibration log")
        changed_again = record_voice_correction(
            temp_root,
            user_text="用词不像中文互联网，GPT味太重，真的红温。",
            reply="我理解你的反馈，会持续优化系统输出。",
            source="smoke",
            recorded_at="2026-04-26T17:21:00+08:00",
        )
        if changed_again:
            failures.append("duplicate correction should not be recorded twice")
        review_path = target / "voice_profile_review_state.md"
        if not review_path.exists():
            failures.append("voice promotion review state was not generated")
        else:
            review = review_path.read_text(encoding="utf-8")
            for marker in (
                "review_status: pending_owner_review",
                "stable_profile_write: blocked_until_owner_accepts",
                "owner_review_status: pending",
            ):
                if marker not in review:
                    failures.append(f"promotion review missing marker: {marker}")

    if failures:
        print("Voice learning smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Voice learning smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
