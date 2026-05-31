from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from behavior_gate import evaluate_gate, label_conflicts, read_jsonl, without_conflicting_labels, write_jsonl


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", action="append", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--use-review-metadata", action="store_true")
    parser.add_argument("--exclude-label-conflicts", action="store_true")
    parser.add_argument("--clean-cases-out", default="")
    args = parser.parse_args()

    paths = [Path(item) for item in args.cases]
    rows = []
    for path in paths:
        rows.extend(read_jsonl(path))

    conflicts = label_conflicts(rows)
    evaluated_rows = without_conflicting_labels(rows) if args.exclude_label_conflicts else rows
    report = evaluate_gate(evaluated_rows, use_review_metadata=bool(args.use_review_metadata))
    report["cases"] = [str(path) for path in paths]
    report["excluded_label_conflicts"] = bool(args.exclude_label_conflicts)
    report["input_case_count"] = len(rows)
    report["excluded_case_count"] = len(rows) - len(evaluated_rows)
    report["label_conflicts"] = conflicts

    if args.clean_cases_out:
        write_jsonl(Path(args.clean_cases_out), evaluated_rows)
        report["clean_cases_out"] = args.clean_cases_out

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"input_case_count={report['input_case_count']}")
    print(f"case_count={report['case_count']}")
    print(f"mode_match_count={report['mode_match_count']}")
    print(f"use_review_metadata={report['use_review_metadata']}")
    print(f"excluded_label_conflicts={report['excluded_label_conflicts']}")
    print(f"excluded_case_count={report['excluded_case_count']}")
    print(f"label_conflict_count={report['label_conflicts']['conflict_count']}")
    for mode, value in report["by_expected"].items():
        actual_counts = json.dumps(value["actual_counts"], ensure_ascii=False, sort_keys=True)
        print(f"{mode}: match={value['match']}/{value['total']} actual={actual_counts}")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
