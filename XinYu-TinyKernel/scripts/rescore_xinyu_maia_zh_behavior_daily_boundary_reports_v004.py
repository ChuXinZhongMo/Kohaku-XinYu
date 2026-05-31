from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PROPOSALS = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_review_proposals_v004.jsonl"
REPORTS = {
    "v003_balanced_compact": ROOT
    / "eval"
    / "reports"
    / "xinyu_maia_zh_behavior_inner_eval_v003_balanced_compact_behavior_balanced56.json",
    "v004_boundary_repair": ROOT
    / "eval"
    / "reports"
    / "xinyu_maia_zh_behavior_inner_eval_v004_boundary_repair_behavior_balanced56.json",
}
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_daily_boundary_rescore_v004.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_daily_boundary_rescore_v004.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    proposal_rows = read_jsonl(PROPOSALS)
    revised_by_source = {
        str(row["source_id"]): {
            "review_id": row["review_id"],
            "user_text": row["user_text"],
            "revised_mode": row["assistant_proposed_mode"],
            "reason": row["assistant_proposal_reason_zh"],
        }
        for row in proposal_rows
        if str(row.get("source_kind")) == "v003_balanced_eval_reply_clarify_wait"
    }
    if len(revised_by_source) != 24:
        raise RuntimeError(f"expected 24 v003-balanced proposal mappings, got {len(revised_by_source)}")

    summaries: dict[str, Any] = {}
    detail_rows: list[dict[str, Any]] = []
    for name, report_path in REPORTS.items():
        report = read_json(report_path)
        selected = [row for row in report.get("results", []) if str(row.get("id")) in revised_by_source]
        if len(selected) != 24:
            raise RuntimeError(f"{name}: expected 24 daily boundary rows, got {len(selected)}")
        strict_json = sum(1 for row in selected if row.get("strict_json_ok"))
        schema = sum(1 for row in selected if row.get("schema_ok"))
        old_mode_match = sum(1 for row in selected if row.get("mode_match"))
        revised_match = 0
        revised_match_schema = 0
        by_revised_mode: dict[str, Counter[str]] = {}
        for row in selected:
            mapping = revised_by_source[str(row["id"])]
            revised_mode = str(mapping["revised_mode"])
            actual = str(row.get("actual_mode") or "")
            ok = actual == revised_mode
            revised_match += int(ok)
            revised_match_schema += int(ok and bool(row.get("schema_ok")))
            by_revised_mode.setdefault(revised_mode, Counter())
            by_revised_mode[revised_mode]["total"] += 1
            by_revised_mode[revised_mode]["match"] += int(ok)
            by_revised_mode[revised_mode]["schema_match"] += int(ok and bool(row.get("schema_ok")))
            detail_rows.append(
                {
                    "report": name,
                    "id": row.get("id"),
                    "review_id": mapping["review_id"],
                    "user_text": mapping["user_text"],
                    "old_expected_mode": row.get("expected_mode"),
                    "revised_expected_mode": revised_mode,
                    "actual_mode": actual,
                    "strict_json_ok": row.get("strict_json_ok"),
                    "schema_ok": row.get("schema_ok"),
                    "old_mode_match": row.get("mode_match"),
                    "revised_mode_match": ok,
                }
            )
        summaries[name] = {
            "source_report": str(report_path.relative_to(ROOT)).replace("\\", "/"),
            "daily_boundary_rows": len(selected),
            "strict_json_ok": strict_json,
            "schema_ok": schema,
            "old_mode_match": old_mode_match,
            "revised_mode_match": revised_match,
            "revised_mode_match_with_schema": revised_match_schema,
            "by_revised_mode": {
                mode: dict(counter)
                for mode, counter in sorted(by_revised_mode.items())
            },
        }

    out = {
        "generated_at": "2026-05-29",
        "proposal_source": str(PROPOSALS.relative_to(ROOT)).replace("\\", "/"),
        "daily_boundary_mapping_count": len(revised_by_source),
        "summaries": summaries,
        "details": detail_rows,
        "notes": [
            "This rescoring uses owner-delegated v004 proposal modes for the 24 daily rows that came from the old balanced56 eval.",
            "It does not change model outputs or training data.",
            "Use this only to understand old-label vs revised-label behavior.",
        ],
    }
    dump_json(OUT_REPORT, out)

    lines = [
        "# XinYu Maia 中文日常边界重算 v004",
        "",
        "用 v004 delegated 标签重算旧 balanced56 里的 24 条日常 reply/clarify/wait 行。",
        "",
        "| report | strict_json | schema | old_match | revised_match | revised_match_with_schema |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, summary in summaries.items():
        lines.append(
            f"| {name} | {summary['strict_json_ok']}/24 | {summary['schema_ok']}/24 | "
            f"{summary['old_mode_match']}/24 | {summary['revised_mode_match']}/24 | "
            f"{summary['revised_mode_match_with_schema']}/24 |"
        )
    lines.extend(
        [
            "",
            "## By Revised Mode",
            "",
            "| report | mode | match | schema_match | total |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for name, summary in summaries.items():
        for mode, counts in summary["by_revised_mode"].items():
            lines.append(
                f"| {name} | {mode} | {counts.get('match', 0)} | "
                f"{counts.get('schema_match', 0)} | {counts.get('total', 0)} |"
            )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(out["summaries"], ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
