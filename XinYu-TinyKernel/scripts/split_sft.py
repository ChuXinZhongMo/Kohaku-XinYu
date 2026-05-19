from __future__ import annotations

import argparse
import random
from pathlib import Path

from common import DATA_DIR, read_jsonl, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DATA_DIR / "sft" / "xinyu_tinykernel_v0.jsonl"))
    parser.add_argument("--train", default=str(DATA_DIR / "sft" / "train_v0.jsonl"))
    parser.add_argument("--eval", default=str(DATA_DIR / "sft" / "eval_v0.jsonl"))
    parser.add_argument("--eval-ratio", type=float, default=0.12)
    parser.add_argument("--seed", type=int, default=20260513)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    buckets: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        tags = row.get("tags") if isinstance(row.get("tags"), list) else []
        mode = str(tags[0]) if tags else "unknown"
        buckets.setdefault(mode, []).append(row)

    rng = random.Random(args.seed)
    train_rows: list[dict[str, object]] = []
    eval_rows: list[dict[str, object]] = []
    for mode, bucket in buckets.items():
        rng.shuffle(bucket)
        eval_count = max(1, int(round(len(bucket) * args.eval_ratio))) if len(bucket) >= 4 else min(1, len(bucket))
        eval_rows.extend(bucket[:eval_count])
        train_rows.extend(bucket[eval_count:])

    train_rows.sort(key=lambda row: str(row.get("id", "")))
    eval_rows.sort(key=lambda row: str(row.get("id", "")))
    train_count = write_jsonl(Path(args.train), train_rows)
    eval_count = write_jsonl(Path(args.eval), eval_rows)
    print(f"train_rows={train_count}")
    print(f"eval_rows={eval_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

