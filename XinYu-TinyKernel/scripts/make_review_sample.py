from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from common import DATA_DIR, read_jsonl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DATA_DIR / "sft" / "xinyu_tinykernel_v0.jsonl"))
    parser.add_argument("--out", default=str(DATA_DIR / "raw_index" / "review_sample_v0.json"))
    parser.add_argument("--per-mode", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260513)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    buckets: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        tags = row.get("tags") if isinstance(row.get("tags"), list) else []
        mode = str(tags[0]) if tags else "unknown"
        buckets.setdefault(mode, []).append(row)
    rng = random.Random(args.seed)
    sample: dict[str, list[dict[str, object]]] = {}
    for mode, bucket in sorted(buckets.items()):
        rng.shuffle(bucket)
        simplified: list[dict[str, object]] = []
        for row in bucket[: args.per_mode]:
            messages = row.get("messages") if isinstance(row.get("messages"), list) else []
            user_payload = {}
            assistant_payload = {}
            if len(messages) >= 3 and isinstance(messages[1], dict) and isinstance(messages[2], dict):
                try:
                    user_payload = json.loads(str(messages[1].get("content", "{}")))
                    assistant_payload = json.loads(str(messages[2].get("content", "{}")))
                except json.JSONDecodeError:
                    pass
            simplified.append(
                {
                    "id": row.get("id"),
                    "source": row.get("source"),
                    "kind": row.get("kind"),
                    "user_text": user_payload.get("user_text", ""),
                    "assistant_target": assistant_payload,
                    "review": {"approved": None, "notes": ""},
                }
            )
        sample[mode] = simplified
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sample, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

