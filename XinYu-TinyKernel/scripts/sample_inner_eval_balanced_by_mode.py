from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def expected_mode(row: dict[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 3:
        return ""
    assistant = messages[-1]
    if not isinstance(assistant, dict):
        return ""
    try:
        target = json.loads(str(assistant.get("content") or "{}"))
    except json.JSONDecodeError:
        return ""
    action = target.get("action_tendency") if isinstance(target, dict) else None
    return str((action or {}).get("mode") or "")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--per-mode", type=int, default=8)
    args = parser.parse_args()

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(Path(args.input)):
        mode = expected_mode(row)
        if mode:
            buckets[mode].append(row)

    modes = ["reply", "clarify", "wait", "codex_delegate", "status_probe", "memory_candidate", "local_only_limitation"]
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for mode in modes:
        rows = buckets.get(mode, [])[: args.per_mode]
        selected.extend(rows)
        counts[mode] = len(rows)

    write_jsonl(Path(args.output), selected)
    print(f"rows={len(selected)}")
    print("mode_counts=" + json.dumps(counts, ensure_ascii=False, sort_keys=True))
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
