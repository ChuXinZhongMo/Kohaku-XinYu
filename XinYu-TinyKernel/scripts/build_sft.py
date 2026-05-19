from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import DATA_DIR, read_jsonl, write_jsonl


SYSTEM_PROMPT = (
    "You are XinYu TinyKernel. Output strict JSON only. "
    "Choose one mode from reply, clarify, wait, codex_delegate, status_probe, memory_candidate, local_only_limitation. "
    "Do not expose internal file names, local paths, secrets, pseudo tool syntax, or report-style mechanics. "
    "Tool requests are suggestions only; never claim tools were executed."
)


def to_sft_row(row: dict[str, Any], idx: int) -> dict[str, Any] | None:
    input_value = row.get("input") if isinstance(row.get("input"), dict) else {}
    target = row.get("target") if isinstance(row.get("target"), dict) else {}
    user_text = str(input_value.get("user_text", "")).strip()
    mode = str(target.get("mode", "")).strip()
    if not user_text or mode not in {
        "reply",
        "clarify",
        "wait",
        "codex_delegate",
        "status_probe",
        "memory_candidate",
        "local_only_limitation",
    }:
        return None
    assistant_payload = {
        "mode": mode,
        "reply": str(target.get("reply", "")),
        "tool_request": target.get("tool_request"),
        "memory_candidates": target.get("memory_candidates") if isinstance(target.get("memory_candidates"), list) else [],
        "style": target.get("style") if isinstance(target.get("style"), dict) else {},
        "confidence": float(target.get("confidence") or 0.5),
    }
    user_payload = {
        "user_text": user_text,
        "context": input_value.get("context") if isinstance(input_value.get("context"), dict) else {},
        "capabilities": input_value.get("capabilities") if isinstance(input_value.get("capabilities"), dict) else {},
    }
    return {
        "id": f"tk-v0-{idx:06d}",
        "source": row.get("source", "unknown"),
        "kind": row.get("kind", "unknown"),
        "quality": "approved_for_v0",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(assistant_payload, ensure_ascii=False, sort_keys=True)},
        ],
        "tags": [mode, str(row.get("kind", "unknown"))],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DATA_DIR / "cleaned" / "cleaned_v0.jsonl"))
    parser.add_argument("--output", default=str(DATA_DIR / "sft" / "xinyu_tinykernel_v0.jsonl"))
    parser.add_argument("--limit", type=int, default=800)
    parser.add_argument("--max-reply", type=int, default=430)
    parser.add_argument("--max-memory", type=int, default=160)
    parser.add_argument("--max-other", type=int, default=80)
    args = parser.parse_args()

    converted_rows: list[dict[str, Any]] = []
    for row in read_jsonl(Path(args.input)):
        converted = to_sft_row(row, len(converted_rows) + 1)
        if converted:
            converted_rows.append(converted)
    priority = {
        "codex_delegate": 0,
        "status_probe": 1,
        "local_only_limitation": 2,
        "wait": 3,
        "memory_candidate": 4,
        "clarify": 5,
        "reply": 6,
    }
    converted_rows.sort(
        key=lambda row: (
            priority.get(row["tags"][0], 99),
            str(row.get("source", "")),
            str(row.get("id", "")),
        )
    )
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for row in converted_rows:
        mode = str(row["tags"][0])
        cap = args.max_reply if mode == "reply" else args.max_memory if mode == "memory_candidate" else args.max_other
        if counts.get(mode, 0) >= cap:
            continue
        selected.append(row)
        counts[mode] = counts.get(mode, 0) + 1
        if len(selected) >= args.limit:
            break
    out_rows = selected
    for idx, row in enumerate(out_rows, start=1):
        row["id"] = f"tk-v0-{idx:06d}"
    count = write_jsonl(Path(args.output), out_rows)
    print(f"wrote {count} SFT rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
