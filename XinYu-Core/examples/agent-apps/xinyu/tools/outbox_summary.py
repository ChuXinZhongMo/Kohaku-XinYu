#!/usr/bin/env python3
"""Print a compact QQ outbox summary as JSON (for stack health scripts)."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"error": "usage: outbox_summary.py <qq_outbox_queue.json>"}))
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(json.dumps({"error": "missing", "path": str(path)}))
        return 1
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = data.get("items") or data.get("queue") or []
    if not isinstance(items, list):
        items = []
    counts: dict[str, int] = {}
    pe: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        source = str(item.get("source") or "")
        if "private_ecosystem" in source or meta.get("share_kind") == "browse_observation":
            pe.append(
                {
                    "status": status,
                    "id": str(item.get("id") or "")[:72],
                    "updated_at": str(item.get("updated_at") or ""),
                    "adapter_message_id": str(item.get("adapter_message_id") or ""),
                }
            )
    print(json.dumps({"total": len(items), "counts": counts, "pe": pe[-5:]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
