from __future__ import annotations

import json
import tempfile
from pathlib import Path

from xinyu_dialogue_observation_extract import build_candidates, load_dialogue_lines, main


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _snapshot_memory(root: Path) -> set[str]:
    memory = root / "memory"
    if not memory.exists():
        return set()
    return {str(path.relative_to(root)) for path in memory.rglob("*") if path.is_file()}


def run_smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-observation-") as tmp:
        root = Path(tmp)
        app_root = root / "app"
        app_root.mkdir(parents=True)
        raw = root / "raw"
        raw.mkdir()
        (raw / "sample.txt").write_text(
            "\n".join(
                [
                    "Jill: 你上次说过，累的时候不想听人讲大道理。",
                    "Dana: 那我就不讲了，我在这儿。",
                    "UI: 感谢反馈，我们会持续优化用户体验。",
                    "Guest: 对不起，刚才那句不是我想说的。",
                    "Lore: 帝国战争的传说将永远改变所有人的命运。",
                ]
            ),
            encoding="utf-8",
        )
        (raw / "sample.jsonl").write_text(
            json.dumps({"speaker": "A", "text": "别急，慢慢说，我记得你之前提过这件事。"}, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        before_memory = _snapshot_memory(root)
        lines = load_dialogue_lines([raw])
        candidates = build_candidates(lines)
        output = root / "out" / "candidates.jsonl"
        rc = main(["--input", str(raw), "--output", str(output)])
        after_memory = _snapshot_memory(root)
        rows = _read_jsonl(output)

        if rc != 0:
            failures.append("extractor main should return 0")
        if len(lines) < 5:
            failures.append("fixture lines were not loaded")
        if not candidates:
            failures.append("candidate builder should find useful dialogue")
        if not rows:
            failures.append("candidate output should not be empty")
        if before_memory != after_memory:
            failures.append("dialogue observation extractor must not write memory")
        if not any("remembered_detail" in row.get("signals", []) for row in rows):
            failures.append("remembered_detail signal missing")
        if not any("repair" in row.get("signals", []) for row in rows):
            failures.append("repair signal missing")
        if not any("local_source_observation_only" in row.get("boundary", "") for row in rows):
            failures.append("boundary marker missing")
        if any(row.get("suggested_use") != "manual_rule_card_review" for row in rows):
            failures.append("candidates should stay manual-review only")
        if any("stable_profile_write" in row for row in rows):
            failures.append("candidate rows should not request stable profile writes")

    return failures


def main_smoke() -> int:
    failures = run_smoke()
    if failures:
        print("xinyu_dialogue_observation_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_dialogue_observation_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_smoke())

