from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from kernel import decide


def read_cases(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(ROOT / "eval" / "eval_cases.jsonl"))
    parser.add_argument("--report", default=str(ROOT / "eval" / "reports" / "rule_eval_latest.json"))
    args = parser.parse_args()

    cases = read_cases(Path(args.cases))
    results: list[dict[str, object]] = []
    failures: list[str] = []
    for case in cases:
        payload = {
            "turn_id": case.get("id", ""),
            "source": "local_test",
            "user_text": case.get("user_text", ""),
            "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
            "capabilities": case.get("capabilities", {}),
            "constraints": {"max_reply_chars": 240, "allow_tool_request": True, "allow_memory_candidate": True},
        }
        output = decide(payload)
        expected = case.get("expected_mode")
        ok = output.get("mode") == expected
        if not ok:
            failures.append(f"{case.get('id')}: expected {expected}, got {output.get('mode')}")
        results.append({"id": case.get("id"), "expected": expected, "actual": output.get("mode"), "ok": ok, "output": output})

    report = {"case_count": len(cases), "ok_count": sum(1 for item in results if item["ok"]), "failures": failures, "results": results}
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
    print("eval_ok=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
