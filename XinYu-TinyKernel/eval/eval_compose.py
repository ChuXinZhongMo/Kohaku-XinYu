from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from compose import compose_shadow


def read_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(ROOT / "eval" / "eval_cases.jsonl"))
    parser.add_argument("--report", default=str(ROOT / "eval" / "reports" / "compose_eval_v001.json"))
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for case in read_cases(Path(args.cases)):
        payload = {
            "turn_id": case.get("id", ""),
            "source": "local_test",
            "user_text": case.get("user_text", ""),
            "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
            "capabilities": case.get("capabilities", {}),
            "constraints": {"max_reply_chars": 240, "allow_tool_request": False, "allow_memory_candidate": False},
        }
        output = compose_shadow(payload)
        ok = bool(output.get("ok")) and output.get("shadow_only") is True and len(str(output.get("reply_candidate", ""))) <= 240
        if not ok:
            failures.append(str(case.get("id", "")))
        results.append({"id": case.get("id"), "ok": ok, "output": output})
    report = {
        "case_count": len(results),
        "ok_count": sum(1 for item in results if item["ok"]),
        "failures": failures,
        "results": results,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"case_count={report['case_count']}")
    print(f"ok_count={report['ok_count']}")
    print(f"report={report_path}")
    if failures:
        for failure in failures:
            print("FAIL " + failure)
        return 1
    print("compose_eval_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
