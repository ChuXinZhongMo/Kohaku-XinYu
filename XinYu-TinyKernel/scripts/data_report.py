from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from common import DATA_DIR, read_jsonl


def assistant_payload(row: dict[str, object]) -> dict[str, object]:
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    if len(messages) < 3 or not isinstance(messages[2], dict):
        return {}
    try:
        value = json.loads(str(messages[2].get("content", "{}")))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def report_for(path: Path) -> dict[str, object]:
    rows = read_jsonl(path)
    modes: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    reply_lengths: list[int] = []
    tool_count = 0
    memory_count = 0
    for row in rows:
        tags = row.get("tags") if isinstance(row.get("tags"), list) else []
        if tags:
            modes[str(tags[0])] += 1
        sources[str(row.get("source", "unknown"))] += 1
        kinds[str(row.get("kind", "unknown"))] += 1
        payload = assistant_payload(row)
        reply_lengths.append(len(str(payload.get("reply", ""))))
        if payload.get("tool_request"):
            tool_count += 1
        if isinstance(payload.get("memory_candidates"), list) and payload.get("memory_candidates"):
            memory_count += 1
    avg_reply_len = round(sum(reply_lengths) / len(reply_lengths), 2) if reply_lengths else 0
    return {
        "path": str(path),
        "rows": len(rows),
        "modes": dict(sorted(modes.items())),
        "sources": dict(sorted(sources.items())),
        "kinds": dict(sorted(kinds.items())),
        "tool_request_rows": tool_count,
        "memory_candidate_rows": memory_count,
        "avg_reply_chars": avg_reply_len,
        "max_reply_chars": max(reply_lengths) if reply_lengths else 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sft", default=str(DATA_DIR / "sft" / "xinyu_tinykernel_v0.jsonl"))
    parser.add_argument("--train", default=str(DATA_DIR / "sft" / "train_v0.jsonl"))
    parser.add_argument("--eval", default=str(DATA_DIR / "sft" / "eval_v0.jsonl"))
    parser.add_argument("--out", default=str(DATA_DIR / "raw_index" / "data_quality_report.json"))
    args = parser.parse_args()

    report = {
        "sft": report_for(Path(args.sft)),
        "train": report_for(Path(args.train)) if Path(args.train).exists() else None,
        "eval": report_for(Path(args.eval)) if Path(args.eval).exists() else None,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(json.dumps(report["sft"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
