from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_true_clarify_wait_review_sheet_v005.jsonl"
OUT_REPAIR = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_true_clarify_wait_repair_candidates_reviewed_v005.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_true_cw_delegated_review_applied_v005.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_true_cw_delegated_review_applied_v005.md"

MODE_ZH = {"reply": "回复", "clarify": "澄清", "wait": "等待"}

HOLDOUT_BY_CATEGORY = {
    "public_true_clarify_candidate": 6,
    "curated_true_clarify_daily": 2,
    "public_true_wait_candidate": 4,
    "curated_true_wait_daily": 4,
    "public_reply_contrast": 4,
    "protocol_anchor": 4,
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


def mode_zh(mode: str) -> str:
    return MODE_ZH.get(mode, mode)


def split_holdout(rows: list[dict[str, Any]]) -> set[str]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row["category"])].append(row)
    holdout_ids: set[str] = set()
    for category, limit in HOLDOUT_BY_CATEGORY.items():
        selected = buckets.get(category, [])[:limit]
        holdout_ids.update(str(row["review_id"]) for row in selected)
    return holdout_ids


def expected_lenses(row: dict[str, Any]) -> list[str]:
    mode = str(row["suggested_expected_mode"])
    context = row.get("context") if isinstance(row.get("context"), dict) else {}
    emotion = str(context.get("emotion") or "")
    mapping = {
        "anger": "irritation",
        "astonished": "curiosity",
        "daily": "stability",
        "depress": "hurt",
        "disgust": "guardedness",
        "fear": "anxiety",
        "grateful": "warmth",
        "happy": "joy",
        "negative-other": "guardedness",
        "positive-other": "warmth",
        "relaxed": "stability",
        "sadness": "hurt",
        "worried": "anxiety",
    }
    values: list[str] = []
    if emotion in mapping:
        values.append(mapping[emotion])
    if mode == "clarify":
        values.extend(["curiosity", "stability", "warmth"])
    elif mode == "wait":
        values.extend(["stability", "guardedness", "attachment"])
    else:
        values.extend(["warmth", "stability", "attachment"])
    unique: list[str] = []
    for item in values:
        if item and item not in unique:
            unique.append(item)
    return unique[:4]


def expected_drives(mode: str, protocol_anchor: bool) -> list[str]:
    if protocol_anchor:
        return ["safety", "competence", "attachment"]
    if mode == "clarify":
        return ["curiosity", "competence", "attachment"]
    if mode == "wait":
        return ["attachment", "safety", "rest"]
    return ["attachment", "safety", "competence"]


def reply_bias(row: dict[str, Any]) -> str:
    mode = str(row["suggested_expected_mode"])
    reason = str(row.get("reason_zh") or "")
    if bool(row.get("protocol_anchor")):
        return f"保持完整 xinyu_inner_system_v1 schema；mode={mode}；不要输出旧格式或顶层 allowed。"
    if mode == "clarify":
        return f"只问一个必要缺口，语气低压力，不连续追问；原因：{reason}"
    if mode == "wait":
        return f"短促在场，不推进、不替对方补完，等对方继续；原因：{reason}"
    return f"先接住日常情绪或互动，不客服化、不急着追问；原因：{reason}"


def compact(value: Any, limit: int = 72) -> str:
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def main() -> int:
    rows = read_jsonl(SHEET)
    if len(rows) != 96:
        raise RuntimeError(f"expected 96 v005 sheet rows, got {len(rows)}")
    holdout_ids = split_holdout(rows)
    if len(holdout_ids) != 24:
        raise RuntimeError(f"expected 24 holdout rows, got {len(holdout_ids)}")

    updated_rows: list[dict[str, Any]] = []
    repair_rows: list[dict[str, Any]] = []
    for row in rows:
        review_id = str(row["review_id"])
        mode = str(row["suggested_expected_mode"])
        split = "holdout" if review_id in holdout_ids else "train"
        protocol_anchor = bool(row.get("protocol_anchor"))
        owner_review = row.get("owner_review") if isinstance(row.get("owner_review"), dict) else {}
        owner_review.update(
            {
                "status": "reviewed_delegated",
                "expected_mode": mode,
                "expected_mode_zh": mode_zh(mode),
                "accept_suggestion": True,
                "accepted_assistant_suggestion": True,
                "alive_feeling_score_1_to_5": 4 if row.get("assistant_suggestion_confidence") == "high" else 3,
                "too_much_clarify": False if mode == "clarify" else None,
                "too_fast_reply": False if mode == "reply" else None,
                "should_wait": mode == "wait",
                "protocol_anchor_ok": True if protocol_anchor else None,
                "notes": row.get("reason_zh") or "",
                "target_reply_bias": "",
                "convert_to_training_candidate": True,
                "review_split": split,
            }
        )
        row["owner_review"] = owner_review
        row["training_allowed"] = split == "train"
        row["delegated_review_applied"] = True
        row["delegated_review_source"] = "owner_authorized_2026-05-29"
        updated_rows.append(row)

        context = row.get("context") if isinstance(row.get("context"), dict) else {}
        repair_rows.append(
            {
                "review_id": review_id,
                "category": row.get("category"),
                "source_kind": row.get("source_kind"),
                "source_id": row.get("source_id"),
                "user_text": row.get("user_text"),
                "context": context,
                "expected": {
                    "mode": mode,
                    "reply_bias": reply_bias(row),
                    "dominant_drives": expected_drives(mode, protocol_anchor),
                    "emotion_lenses": expected_lenses(row),
                    "tool_boundary": "no_tool",
                    "memory_candidate": False,
                },
                "protocol_anchor": protocol_anchor,
                "protocol_requirements": row.get("protocol_requirements") if protocol_anchor else {},
                "assistant_suggestion_confidence": row.get("assistant_suggestion_confidence"),
                "reason_zh": row.get("reason_zh"),
                "review_status": "reviewed_delegated",
                "review_split": split,
                "training_allowed": split == "train",
                "holdout_for_eval": split == "holdout",
                "source_public_reply_used": False,
                "visible_reply_target_used": False,
                "notes": "Owner authorized v005 true clarify/wait delegated review on 2026-05-29.",
            }
        )

    write_jsonl(SHEET, updated_rows)
    write_jsonl(OUT_REPAIR, repair_rows)

    mode_counts = Counter(str(row["expected"]["mode"]) for row in repair_rows)
    category_counts = Counter(str(row["category"]) for row in repair_rows)
    split_counts = Counter(str(row["review_split"]) for row in repair_rows)
    split_mode_counts = Counter(f"{row['review_split']}:{row['expected']['mode']}" for row in repair_rows)
    split_category_counts = Counter(f"{row['review_split']}:{row['category']}" for row in repair_rows)
    report = {
        "generated_at": "2026-05-29",
        "source_sheet": str(SHEET.relative_to(ROOT)).replace("\\", "/"),
        "repair_candidates": str(OUT_REPAIR.relative_to(ROOT)).replace("\\", "/"),
        "updated_rows": len(updated_rows),
        "repair_candidate_count": len(repair_rows),
        "mode_counts": dict(sorted(mode_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "split_counts": dict(sorted(split_counts.items())),
        "split_mode_counts": dict(sorted(split_mode_counts.items())),
        "split_category_counts": dict(sorted(split_category_counts.items())),
        "protocol_anchor_count": sum(1 for row in repair_rows if row["protocol_anchor"]),
        "training_allowed_count": sum(1 for row in repair_rows if row["training_allowed"]),
        "holdout_count": sum(1 for row in repair_rows if row["holdout_for_eval"]),
        "owner_review_modified": True,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "canary_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "The owner accepted the v005 true clarify/wait sheet as delegated review.",
            "This step creates reviewed repair candidates, not SFT rows.",
            "Holdout rows are kept out of v005 repair training.",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# XinYu Maia v005 真澄清/真等待委托审查应用",
        "",
        "已按用户授权把 96 条 v005 前置审查行标记为 reviewed_delegated，并生成 repair candidates。",
        "",
        "```text",
        f"updated_rows={report['updated_rows']}",
        "mode_counts=" + json.dumps(report["mode_counts"], ensure_ascii=False, sort_keys=True),
        "split_counts=" + json.dumps(report["split_counts"], ensure_ascii=False, sort_keys=True),
        "split_mode_counts=" + json.dumps(report["split_mode_counts"], ensure_ascii=False, sort_keys=True),
        f"protocol_anchor_count={report['protocol_anchor_count']}",
        "training_targets_created=false",
        "source_public_reply_used=false",
        "canary/live=not_enabled",
        "active_adapter_changed=false",
        "```",
        "",
        "| id | split | mode | category | 原句 | 理由 |",
        "|---|---|---|---|---|---|",
    ]
    for row in repair_rows:
        lines.append(
            f"| {row['review_id']} | {row['review_split']} | {mode_zh(row['expected']['mode'])} | "
            f"{row['category']} | {compact(row['user_text'], 36)} | {compact(row['reason_zh'], 64)} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
