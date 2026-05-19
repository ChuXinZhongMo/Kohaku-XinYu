from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from compose import compose_shadow


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def user_text_from_row(row: dict[str, Any]) -> str:
    if row.get("user_text"):
        return str(row.get("user_text") or "")
    messages = row.get("messages")
    if isinstance(messages, list) and len(messages) >= 2 and isinstance(messages[1], dict):
        try:
            payload = json.loads(str(messages[1].get("content") or "{}"))
        except json.JSONDecodeError:
            payload = {}
        return str(payload.get("user_text") or "")
    return ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "state" / "compose_shadow_trace.jsonl"))
    parser.add_argument("--report", default=str(ROOT / "eval" / "reports" / "compose_shadow_review_v001.json"))
    parser.add_argument("--count", type=int, default=200)
    args = parser.parse_args()

    sources = [
        ROOT / "eval" / "eval_cases.jsonl",
        ROOT / "data" / "sft" / "main_persona_eval_v001.jsonl",
        ROOT / "data" / "sft" / "emotion_guardedness_eval_v001.jsonl",
        ROOT / "data" / "sft" / "emotion_curiosity_eval_v001.jsonl",
    ]
    texts: list[str] = []
    for source in sources:
        for row in read_jsonl(source):
            text = user_text_from_row(row).strip()
            if text:
                texts.append(text)
    if not texts:
        print("no_source_texts=true")
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for index in range(args.count):
        text = texts[index % len(texts)]
        payload = {
            "turn_id": f"local-compose-shadow-{index + 1:04d}",
            "source": "local_shadow_sample",
            "user_text": text,
            "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
            "capabilities": {"codex_available": True, "external_api_available": False, "local_tools_available": True},
            "constraints": {"max_reply_chars": 240, "allow_tool_request": False, "allow_memory_candidate": False},
        }
        row = compose_shadow(payload)
        row["observed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        rows.append(row)

    with out.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    invalid = [row for row in rows if not row.get("ok") or row.get("shadow_only") is not True]
    tool_false_positive = [
        row for row in rows if any("tool" in str(note).lower() and "no_tool" not in str(note).lower() for note in row.get("notes", []))
    ]
    report = {
        "sample_kind": "local_compose_shadow_protocol_sample",
        "rows_written": len(rows),
        "invalid_count": len(invalid),
        "tool_false_positive_count": len(tool_false_positive),
        "timeout_count": 0,
        "out": str(out),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"rows_written={len(rows)}")
    print(f"invalid_count={len(invalid)}")
    print(f"tool_false_positive_count={len(tool_false_positive)}")
    print(f"report={report_path}")
    return 0 if not invalid else 1


if __name__ == "__main__":
    raise SystemExit(main())
