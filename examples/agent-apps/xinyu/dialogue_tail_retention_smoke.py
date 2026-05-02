from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from xinyu_dialogue_working_memory import compact_tail_for_prompt, load_dialogue_tail, save_dialogue_tail


def main() -> int:
    argparse.ArgumentParser(description="Validate extended XinYu dialogue tail retention.").parse_args()
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-tail-") as tmp:
        root = Path(tmp)
        private_tail = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": f"private line {index}"}
            for index in range(80)
        ]
        group_tail = [{"role": "user", "content": "group-only shared keyword"}]
        if not save_dialogue_tail(root, "qq:private:owner", private_tail):
            failures.append("private tail did not save")
        if not save_dialogue_tail(root, "qq:group:7:owner", group_tail):
            failures.append("group tail did not save")

        loaded = load_dialogue_tail(root, "qq:private:owner", max_entries=64, include_timestamps=True)
        if len(loaded) != 64:
            failures.append(f"expected 64 loaded tail entries, got {len(loaded)}")
        if loaded and "recorded_at" not in loaded[0]:
            failures.append("loaded tail did not include timestamps")
        if loaded and loaded[0]["content"] != "private line 16":
            failures.append("loaded tail did not keep the newest 64 entries")
        if load_dialogue_tail(root, "qq:group:7:owner", max_entries=4)[0]["content"] != "group-only shared keyword":
            failures.append("group tail was not scoped separately")

        long_tail = [{"role": "user", "content": "x" * 1000}]
        compact = compact_tail_for_prompt(long_tail, max_entries=1, entry_chars=80, total_chars=120)
        if not compact or len(compact[0]["content"]) > 80:
            failures.append("prompt compaction did not truncate a long entry")
        if not save_dialogue_tail(root, "qq:private:disabled", private_tail, max_entries=0):
            failures.append("disabled tail save failed")
        if load_dialogue_tail(root, "qq:private:disabled", max_entries=4):
            failures.append("disabled tail save should not persist old entries")

    if failures:
        print("dialogue_tail_retention_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("dialogue_tail_retention_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
