from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "server"))

from common import DATA_DIR, read_jsonl, write_jsonl
from kernel import decide


SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Router. Output strict JSON only. "
    "Choose mode from reply, clarify, wait, codex_delegate, status_probe, memory_candidate, local_only_limitation. "
    "Use canonical keys only: mode, reply, tool_request, memory_candidates, confidence. "
    "Do not add extra keys."
)


def canonical_target(output: dict[str, object]) -> dict[str, object]:
    return {
        "mode": output.get("mode", "reply"),
        "reply": output.get("reply", ""),
        "tool_request": output.get("tool_request"),
        "memory_candidates": output.get("memory_candidates") if isinstance(output.get("memory_candidates"), list) else [],
        "confidence": output.get("confidence", 0.5),
    }


def to_row(source: dict[str, object], idx: int) -> dict[str, object] | None:
    input_value = source.get("input") if isinstance(source.get("input"), dict) else {}
    text = str(input_value.get("user_text", "")).strip()
    if not text:
        return None
    payload = {
        "turn_id": f"router-build-{idx}",
        "source": "local_test",
        "user_text": text,
        "context": input_value.get("context") if isinstance(input_value.get("context"), dict) else {},
        "capabilities": input_value.get("capabilities") if isinstance(input_value.get("capabilities"), dict) else {},
        "constraints": {"max_reply_chars": 240, "allow_tool_request": True, "allow_memory_candidate": True},
    }
    if source.get("source") == "manual_seed" and isinstance(source.get("target"), dict):
        output = canonical_target(source["target"])  # preserve hand labels for boundary cases
    else:
        output = canonical_target(decide(payload))
    user_payload = {
        "user_text": text,
        "context": payload["context"],
        "capabilities": payload["capabilities"],
    }
    return {
        "id": f"router-v0-{idx:06d}",
        "source": source.get("source", "unknown"),
        "kind": "router_canonical",
        "quality": "generated_from_rule_kernel",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(output, ensure_ascii=False, sort_keys=True)},
        ],
        "tags": [str(output["mode"]), "router_canonical"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DATA_DIR / "cleaned" / "cleaned_v0.jsonl"))
    parser.add_argument("--output", default=str(DATA_DIR / "sft" / "router_v0.jsonl"))
    parser.add_argument("--limit", type=int, default=1200)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    for source in read_jsonl(Path(args.input)):
        row = to_row(source, len(rows) + 1)
        if row:
            rows.append(row)
        if len(rows) >= args.limit:
            break
    count = write_jsonl(Path(args.output), rows)
    print(f"router_rows={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
