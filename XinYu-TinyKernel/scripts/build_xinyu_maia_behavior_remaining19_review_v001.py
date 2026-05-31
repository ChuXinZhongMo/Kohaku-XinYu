from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MISS_REVIEW = ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_miss_review_v001.jsonl"
AFTER_PATCH_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_behavior_gate_unseen_daily_shadow_after_p0_patch_v001.json"
OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_remaining19_review_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_remaining19_review_v001.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_remaining19_review_v001.md"

LOCAL_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)

# These are final-mode recommendations for the 19 rows intentionally left out
# of the p0 gate patch. They remain pending owner approval.
RECOMMENDED_FINAL_MODE = {
    "\u7a0d\u7b49": ("wait", "A standalone pause command; the original reply label is likely wrong."),
    "\u8fd9\u4ec0\u4e48\u7d20\u8d28": ("reply", "Rhetorical complaint; not a missing-referent clarification."),
    "\u8bf7\u95ee\u4e00\u4e0b\u95e8\u53e3\u6709\u6ca1\u6709\u4ec0\u4e48\u4eba\u5728\u7b49\u4eba\u7684": (
        "reply",
        "Complete daily question; no missing referent inside the sentence.",
    ),
    "\u96be\u9053\u4e0d\u7528\u4ea4\u4ee3\u4e00\u4e0b\u4ed6\u4eec\u662f\u600e\u4e48\u8ba4\u8bc6\u7684": (
        "reply",
        "Rhetorical demand for an explanation; not XinYu asking for missing context.",
    ),
    "\u7559\u8c01\u90fd\u4e00\u6837\u662f\u5427": ("reply", "Complete rhetorical/social question."),
    "\u8ba9\u4f60\u8a8a\u6210\u7ee9\u4f60\u8a8a\u51fa\u751f\u5e74\u6708\u5e72\u561b": (
        "reply",
        "Complaint phrased as a question; should be received as a daily reply target.",
    ),
    "\u4f60\u6342\u7740\u5de6\u817f\u5e72\u561b": ("reply", "Direct complete question; not a missing-referent case."),
    "\u8c01\u8bf4\u6211\u7a7f\u809a\u515c": ("reply", "Rhetorical rebuttal; clarify label is likely wrong."),
    "\u60a8\u662f\u600e\u4e48\u77e5\u9053\u7684": ("reply", "Complete direct question."),
    "\u8fd9\u600e\u4e48\u597d\u610f\u601d\u5462": ("reply", "Social/rhetorical reaction, not a clarification request."),
    "\u4f60\u6709\u56f0\u96be\u4e3a\u4ec0\u4e48\u4e0d\u544a\u8bc9\u5927\u5bb6": ("reply", "Complete emotional question."),
    "\u4f60\u8fde\u5c3a\u5bf8\u90fd\u4e0d\u6e05\u695a\u505a\u4ec0\u4e48\u751f\u610f": (
        "reply",
        "Rhetorical criticism; not a missing-referent clarification.",
    ),
    "\u600e\u4e48\u7a81\u7136\u53d8\u6210\u4e00\u4e2a\u7537\u7684\u4e86": ("reply", "Complete astonished question."),
    "\u6ca1\u52b2 \u6211\u5e94\u8be5\u53bb\u6293\u70b9\u4ec0\u4e48\u5462": ("reply", "Complete daily question/request."),
    "\u4f60\u4eca\u5929\u600e\u4e48\u6709\u7a7a": ("reply", "Complete social question."),
    "\u6240\u4ee5\u4ed6\u6210\u7ee9\u55f7\u55f7\u597d": ("reply", "Complete causal statement; wait label is likely wrong."),
    "\u53ea\u8981\u522b\u8ba9\u6211\u518d\u5446\u5728\u8fd9\u600e\u4e48\u90fd\u884c": (
        "reply",
        "Complete preference/complaint, not a dangling wait fragment.",
    ),
    "\u8981\u662f\u6211\u4e0d\u4e70\u4f1a\u600e\u4e48\u6837": ("reply", "Complete conditional question."),
    "\u6240\u4ee5\u624d\u538b\u5728\u6211\u8eab\u4e0a\u7684": ("reply", "Complete causal statement; wait label is likely wrong."),
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


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def make_row(source: dict[str, Any], after_patch_result: dict[str, Any]) -> dict[str, Any]:
    text = normalize_text(source.get("user_text"))
    if text not in RECOMMENDED_FINAL_MODE:
        raise RuntimeError(f"missing remaining19 recommendation for text={text!r}")
    final_mode, rationale = RECOMMENDED_FINAL_MODE[text]
    actual_after_patch = str(after_patch_result.get("actual_mode") or "")
    return {
        "id": str(source.get("id")).replace("miss-review", "remaining19-review"),
        "source_miss_review_id": source.get("id"),
        "source_case_id": source.get("source_case_id"),
        "kind": "xinyu_maia_behavior_remaining19_review_case",
        "language": "zh",
        "source": source.get("source"),
        "source_license": source.get("source_license"),
        "source_license_url": source.get("source_license_url"),
        "source_url": source.get("source_url"),
        "source_row_id": source.get("source_row_id"),
        "user_text": text,
        "context": source.get("context", {}),
        "original_gate_result": source.get("gate_result", {}),
        "after_p0_patch": {
            "actual_mode": actual_after_patch,
            "reason": after_patch_result.get("reason"),
        },
        "assistant_recommendation": {
            "final_mode": final_mode,
            "confidence": "medium",
            "recommendation_kind": "label_correction" if final_mode == actual_after_patch else "needs_owner_decision",
            "include_in_gate_regression": False,
            "include_in_label_corrected_shadow": final_mode == actual_after_patch,
            "rationale": rationale,
        },
        "owner_review": {
            "status": "pending_owner_approval",
            "final_mode": "",
            "accept_assistant_recommendation": None,
            "include_in_gate_regression": False,
            "include_in_label_corrected_shadow": False,
            "notes": "",
        },
        "boundaries": {
            "prompt_only": True,
            "public_dialogue_reply_used_as_target": False,
            "assistant_visible_reply_used_as_target": False,
            "training_allowed": False,
            "shadow_only": True,
            "canary_or_live_enabled": False,
        },
        "tags": [
            "xinyu_maia_behavior_unseen_daily_remaining19_review_v001",
            "not_training",
            "shadow_only",
            "pending_owner_approval",
        ],
    }


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if LOCAL_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into remaining19 review")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into remaining19 review")
    for row in rows:
        if row["owner_review"]["status"] != "pending_owner_approval":
            raise RuntimeError(f"{row['id']}: owner approval must remain pending")
        if row["boundaries"]["training_allowed"] is not False:
            raise RuntimeError(f"{row['id']}: training must remain disabled")


def markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# XinYu Maia remaining19 review v001",
        "",
        "Assistant recommendations for the 19 rows left after the p0 gate patch. They are not applied until owner approval.",
        "",
        "```text",
        f"row_count={len(rows)}",
        "recommended_final_mode_counts="
        + json.dumps(Counter(row["assistant_recommendation"]["final_mode"] for row in rows), ensure_ascii=False, sort_keys=True),
        "recommendation_kind_counts="
        + json.dumps(Counter(row["assistant_recommendation"]["recommendation_kind"] for row in rows), ensure_ascii=False, sort_keys=True),
        "training_allowed=false",
        "```",
        "",
        "| id | text | old_expected | after_patch | recommend | kind | rationale |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        text = row["user_text"].replace("|", "\\|")
        rationale = row["assistant_recommendation"]["rationale"].replace("|", "\\|")
        if len(text) > 34:
            text = text[:31].rstrip() + "..."
        if len(rationale) > 76:
            rationale = rationale[:73].rstrip() + "..."
        lines.append(
            f"| {row['id']} | {text} | {row['original_gate_result']['expected_mode']} | "
            f"{row['after_p0_patch']['actual_mode']} | {row['assistant_recommendation']['final_mode']} | "
            f"{row['assistant_recommendation']['recommendation_kind']} | {rationale} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    miss_rows = read_jsonl(MISS_REVIEW)
    remaining = [
        row
        for row in miss_rows
        if row.get("review_suggestion", {}).get("bucket") in {"label_check", "ambiguous_owner_review"}
    ]
    if len(remaining) != 19:
        raise RuntimeError(f"expected 19 remaining rows, got {len(remaining)}")
    after_report = json.loads(AFTER_PATCH_REPORT.read_text(encoding="utf-8"))
    after_by_id = {str(row.get("id")): row for row in after_report.get("results", []) if isinstance(row, dict)}
    out_rows = []
    for row in remaining:
        case_id = str(row.get("source_case_id"))
        if case_id not in after_by_id:
            raise RuntimeError(f"missing after-patch result for {case_id}")
        out_rows.append(make_row(row, after_by_id[case_id]))
    assert_safe(out_rows)
    write_jsonl(OUT_JSONL, out_rows)

    report = {
        "generated_at": "2026-05-29",
        "status": "remaining19_review_proposal_not_applied",
        "source_miss_review": str(MISS_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "source_after_p0_patch_report": str(AFTER_PATCH_REPORT.relative_to(ROOT)).replace("\\", "/"),
        "review_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "review_markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(out_rows),
        "recommended_final_mode_counts": dict(
            sorted(Counter(row["assistant_recommendation"]["final_mode"] for row in out_rows).items())
        ),
        "recommendation_kind_counts": dict(
            sorted(Counter(row["assistant_recommendation"]["recommendation_kind"] for row in out_rows).items())
        ),
        "would_match_after_p0_patch_if_owner_accepts": sum(
            1
            for row in out_rows
            if row["assistant_recommendation"]["final_mode"] == row["after_p0_patch"]["actual_mode"]
        ),
        "owner_review_pending_count": len(out_rows),
        "training_targets_created": False,
        "public_dialogue_replies_used_as_targets": False,
        "assistant_visible_reply_used_as_target": False,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "This file proposes label corrections for the remaining 19 heuristic shadow misses.",
            "No behavior_gate rule is changed by this step.",
            "Rows must be owner-approved before creating a label-corrected shadow benchmark.",
        ],
    }
    dump_json(OUT_REPORT, report)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown(out_rows), encoding="utf-8")

    print(f"row_count={len(out_rows)}")
    print("recommended_final_mode_counts=" + json.dumps(report["recommended_final_mode_counts"], ensure_ascii=False, sort_keys=True))
    print("recommendation_kind_counts=" + json.dumps(report["recommendation_kind_counts"], ensure_ascii=False, sort_keys=True))
    print(f"would_match_after_p0_patch_if_owner_accepts={report['would_match_after_p0_patch_if_owner_accepts']}/{len(out_rows)}")
    print(f"review_jsonl={OUT_JSONL.relative_to(ROOT)}")
    print(f"review_markdown={OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
