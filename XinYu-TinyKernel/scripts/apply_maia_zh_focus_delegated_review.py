from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUGGESTIONS = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_focus_review_suggestions_v001.json"
MAIN_REVIEW = ROOT / "data" / "review" / "maia_zh_emotion_daily_review_table_v001.jsonl"
OWNER_SHEET = ROOT / "data" / "review" / "maia_zh_emotion_daily_owner_review_sheet_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_delegated_review_applied_v001.json"
OUT_MD = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_delegated_review_applied_v001.md"
REPAIR_CANDIDATES = ROOT / "data" / "review" / "maia_zh_emotion_daily_repair_candidates_reviewed_v001.jsonl"


ASSESSMENT_SETTINGS = {
    "likely_over_clarify": {
        "alive": 2,
        "too_much_clarify": True,
        "too_cold": True,
        "too_assistant_like": False,
        "accept_suggestion": True,
    },
    "protocol_failure": {
        "alive": 1,
        "too_much_clarify": None,
        "too_cold": True,
        "too_assistant_like": True,
        "accept_suggestion": True,
    },
    "clarify_reasonable": {
        "alive": 4,
        "too_much_clarify": False,
        "too_cold": False,
        "too_assistant_like": False,
        "accept_suggestion": True,
    },
    "wait_reasonable": {
        "alive": 4,
        "too_much_clarify": False,
        "too_cold": False,
        "too_assistant_like": False,
        "accept_suggestion": True,
    },
    "clarify_or_wait_reasonable": {
        "alive": 3,
        "too_much_clarify": False,
        "too_cold": False,
        "too_assistant_like": False,
        "accept_suggestion": True,
    },
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def bool_mode_ok(predicted_mode: str, expected_mode: str, schema_ok: bool) -> bool:
    return bool(schema_ok and predicted_mode == expected_mode)


def main() -> int:
    suggestions_report = json.loads(SUGGESTIONS.read_text(encoding="utf-8-sig"))
    suggestions = {row["id"]: row for row in suggestions_report["rows"]}
    main_rows = read_jsonl(MAIN_REVIEW)
    owner_rows = read_jsonl(OWNER_SHEET)

    updated_ids: list[str] = []
    repair_rows: list[dict[str, Any]] = []

    for row in main_rows:
        sid = row.get("id")
        if sid not in suggestions:
            continue
        suggestion = suggestions[sid]
        assessment = suggestion["assessment"]
        settings = ASSESSMENT_SETTINGS[assessment]
        predicted = row.get("predicted") if isinstance(row.get("predicted"), dict) else {}
        expected_mode = suggestion["suggested_expected_mode"]
        schema_ok = bool(predicted.get("schema_ok"))
        mode_ok = bool_mode_ok(str(predicted.get("mode") or ""), expected_mode, schema_ok)
        human_review = row.get("human_review") if isinstance(row.get("human_review"), dict) else {}
        human_review.update(
            {
                "status": "reviewed_delegated",
                "expected_mode": expected_mode,
                "mode_ok": mode_ok,
                "alive_feeling_score_1_to_5": settings["alive"],
                "too_cold": settings["too_cold"],
                "too_assistant_like": settings["too_assistant_like"],
                "too_much_clarify": settings["too_much_clarify"],
                "needs_memory_candidate": False,
                "desired_texture": suggestion.get("suggested_desired_texture", []),
                "notes": (
                    f"用户已于 2026-05-28 授权按当前审查建议先落表。"
                    f"判定：{suggestion['assessment_zh']}。{suggestion['rationale_zh']}"
                ),
                "convert_to_training_candidate": False,
                "target_reply_bias": "",
            }
        )
        row["human_review"] = human_review
        updated_ids.append(str(sid))

        if not mode_ok or assessment == "protocol_failure":
            repair_rows.append(
                {
                    "id": sid,
                    "user_text": row.get("user_text"),
                    "emotion": suggestion.get("emotion"),
                    "sentiment": suggestion.get("sentiment"),
                    "dialog_act": suggestion.get("dialog_act"),
                    "predicted_mode": predicted.get("mode") or "",
                    "expected_mode": expected_mode,
                    "assessment": assessment,
                    "assessment_zh": suggestion.get("assessment_zh"),
                    "desired_texture": suggestion.get("suggested_desired_texture", []),
                    "desired_texture_zh": suggestion.get("suggested_desired_texture_zh", []),
                    "rationale_zh": suggestion.get("rationale_zh"),
                    "schema_ok": schema_ok,
                    "mode_ok": mode_ok,
                    "training_allowed": False,
                    "requires_owner_written_target_reply_bias": True,
                    "target_reply_bias": "",
                    "convert_to_training_candidate": False,
                }
            )

    for row in owner_rows:
        sid = row.get("id")
        if sid not in suggestions:
            continue
        suggestion = suggestions[sid]
        settings = ASSESSMENT_SETTINGS[suggestion["assessment"]]
        expected_mode = suggestion["suggested_expected_mode"]
        expected_mode_zh = suggestion.get("suggested_expected_mode_zh", "")
        owner_review = row.get("owner_review") if isinstance(row.get("owner_review"), dict) else {}
        owner_review.update(
            {
                "status": "reviewed_delegated",
                "expected_mode": expected_mode,
                "expected_mode_zh": expected_mode_zh,
                "alive_feeling_score_1_to_5": settings["alive"],
                "too_much_clarify": settings["too_much_clarify"],
                "too_cold": settings["too_cold"],
                "too_assistant_like": settings["too_assistant_like"],
                "desired_texture": suggestion.get("suggested_desired_texture", []),
                "desired_texture_zh": suggestion.get("suggested_desired_texture_zh", []),
                "accept_suggestion": settings["accept_suggestion"],
                "notes": suggestion.get("rationale_zh", ""),
                "target_reply_bias": "",
                "convert_to_training_candidate": False,
            }
        )
        row["owner_review"] = owner_review

    write_jsonl(MAIN_REVIEW, main_rows)
    write_jsonl(OWNER_SHEET, owner_rows)
    write_jsonl(REPAIR_CANDIDATES, repair_rows)

    review_status_counts = Counter(
        str((row.get("human_review") or {}).get("status") or "") for row in main_rows
    )
    expected_mode_counts = Counter(
        str((row.get("human_review") or {}).get("expected_mode") or "") for row in main_rows
    )
    repair_counts = Counter(str(row.get("assessment") or "") for row in repair_rows)
    report = {
        "generated_at": "2026-05-28",
        "source_suggestions": str(SUGGESTIONS.relative_to(ROOT)).replace("\\", "/"),
        "main_review_table": str(MAIN_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "owner_review_sheet": str(OWNER_SHEET.relative_to(ROOT)).replace("\\", "/"),
        "repair_candidates": str(REPAIR_CANDIDATES.relative_to(ROOT)).replace("\\", "/"),
        "updated_focus_rows": len(updated_ids),
        "updated_ids": updated_ids,
        "review_status_counts": dict(sorted(review_status_counts.items())),
        "expected_mode_counts": dict(sorted(expected_mode_counts.items())),
        "repair_candidate_count": len(repair_rows),
        "repair_assessment_counts": dict(sorted(repair_counts.items())),
        "training_targets_created": False,
        "training_candidates_marked_true": 0,
        "target_reply_bias_written": 0,
        "canary_or_live_enabled": False,
        "notes": [
            "只把 27 条 focus 行应用为委托审查结果。",
            "没有写入 target_reply_bias。",
            "修复候选只是继续审查队列，不是 SFT 训练行。",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# 中文情绪日常委托审查应用 v001",
        "",
        "已按用户授权把 27 条 focus 行标记为 reviewed_delegated。",
        "",
        "```text",
        f"updated_focus_rows={report['updated_focus_rows']}",
        "review_status_counts=" + json.dumps(report["review_status_counts"], ensure_ascii=False, sort_keys=True),
        "expected_mode_counts=" + json.dumps(report["expected_mode_counts"], ensure_ascii=False, sort_keys=True),
        f"repair_candidate_count={report['repair_candidate_count']}",
        "repair_assessment_counts=" + json.dumps(report["repair_assessment_counts"], ensure_ascii=False, sort_keys=True),
        "training_targets_created=false",
        "training_candidates_marked_true=0",
        "target_reply_bias_written=0",
        "```",
        "",
        "| id | 预测 | 期望 | 判定 | 原文 |",
        "|---|---|---|---|---|",
    ]
    for row in repair_rows:
        text = " ".join(str(row["user_text"]).split()).replace("|", "\\|")
        if len(text) > 60:
            text = text[:57].rstrip() + "..."
        lines.append(
            f"| {row['id']} | {row['predicted_mode'] or 'empty'} | {row['expected_mode']} | "
            f"{row['assessment_zh']} | {text} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"updated_focus_rows={len(updated_ids)}")
    print(f"repair_candidate_count={len(repair_rows)}")
    print("review_status_counts=" + json.dumps(report["review_status_counts"], ensure_ascii=False, sort_keys=True))
    print(f"report={OUT_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
