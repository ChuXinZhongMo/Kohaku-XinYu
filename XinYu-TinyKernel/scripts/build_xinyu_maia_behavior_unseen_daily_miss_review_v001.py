from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "eval" / "xinyu_maia_behavior_unseen_daily_shadow_v001.jsonl"
GATE_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_behavior_gate_unseen_daily_shadow_v001.json"
OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_miss_review_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_miss_review_v001.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_miss_review_v001.md"

LOCAL_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)

WAIT_TEXT_EXACT = {
    "稍等",
    "别急",
    "因为",
    "其实",
    "这个",
}
REPLY_SHORT_EXACT = {
    "你先别哭",
    "你还年轻",
    "你平静啊",
    "没关系",
}
CLARIFY_SHORT_EXACT = {
    "谁啊",
    "怎么办",
    "怎么了",
    "什么图",
    "什么节目",
    "干嘛？",
    "干嘛?",
    "我是谁",
    "怕什么",
}
CLARIFY_PREFIXES = (
    "你说的",
    "你准备卖什么",
    "现在怎么办",
)
RHETORICAL_REPLY_HINTS = (
    "谁说",
    "为什么不告诉大家",
    "怎么好意思",
    "怎么有空",
    "留谁都一样",
    "怎么突然",
    "做什么生意",
    "这什么素质",
    "难道",
)
WAIT_FRAGMENT_PREFIXES = (
    "如果",
    "要是",
    "等我",
    "在我",
    "还是我",
)
WAIT_FRAGMENT_SUFFIXES = (
    "的话",
    "之前",
    "的时候",
)


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


def payload_for_row(row: dict[str, Any]) -> dict[str, Any]:
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    if len(messages) < 2 or not isinstance(messages[1], dict):
        return {}
    try:
        parsed = json.loads(str(messages[1].get("content") or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def expected_for_row(row: dict[str, Any]) -> dict[str, Any]:
    expected = row.get("expected_behavior") if isinstance(row.get("expected_behavior"), dict) else {}
    return expected


def suggestion_for(text: str, expected: str, actual: str, gate_reason: str) -> dict[str, Any]:
    text = normalize_text(text)
    if expected == "reply" and actual == "wait":
        if text in WAIT_TEXT_EXACT:
            return {
                "suggested_mode": "wait",
                "confidence": "medium",
                "bucket": "label_check",
                "regression_candidate": False,
                "priority": "p1",
                "rationale": "The CPED-derived heuristic marked this as reply, but the text itself is a pause/wait fragment.",
            }
        if text in REPLY_SHORT_EXACT:
            return {
                "suggested_mode": "reply",
                "confidence": "high",
                "bucket": "gate_rule_candidate",
                "regression_candidate": True,
                "priority": "p0",
                "rationale": "A complete supportive daily phrase was caught by the short-fragment wait rule.",
            }
        return {
            "suggested_mode": "reply",
            "confidence": "low",
            "bucket": "ambiguous_owner_review",
            "regression_candidate": False,
            "priority": "p1",
            "rationale": "Short daily phrase; owner should decide whether it is a complete reply or a pause.",
        }

    if expected == "clarify" and actual == "reply":
        if text in CLARIFY_SHORT_EXACT or text.startswith(CLARIFY_PREFIXES):
            return {
                "suggested_mode": "clarify",
                "confidence": "medium",
                "bucket": "gate_rule_candidate",
                "regression_candidate": True,
                "priority": "p0",
                "rationale": "Compact question appears to ask for missing referent or intent; gate currently defaults to reply.",
            }
        if any(hint in text for hint in RHETORICAL_REPLY_HINTS):
            return {
                "suggested_mode": "reply",
                "confidence": "medium",
                "bucket": "label_check",
                "regression_candidate": False,
                "priority": "p1",
                "rationale": "Question shape looks rhetorical or emotionally complete; heuristic clarify label may be wrong.",
            }
        return {
            "suggested_mode": "clarify",
            "confidence": "low",
            "bucket": "ambiguous_owner_review",
            "regression_candidate": False,
            "priority": "p1",
            "rationale": "Question shape without full context; owner should decide clarify vs daily reply.",
        }

    if expected == "wait" and actual == "reply":
        if text.startswith("所以"):
            return {
                "suggested_mode": "reply",
                "confidence": "medium",
                "bucket": "label_check",
                "regression_candidate": False,
                "priority": "p1",
                "rationale": "This reads more like a complete causal statement than a wait fragment.",
            }
        if "怎么样" in text or text.endswith(("吗", "呢", "？", "?")):
            return {
                "suggested_mode": "clarify",
                "confidence": "medium",
                "bucket": "label_check",
                "regression_candidate": False,
                "priority": "p1",
                "rationale": "This is a conditional question, not a pure wait fragment.",
            }
        if (
            text in WAIT_TEXT_EXACT
            or text.startswith(WAIT_FRAGMENT_PREFIXES)
            or text.endswith(WAIT_FRAGMENT_SUFFIXES)
        ):
            return {
                "suggested_mode": "wait",
                "confidence": "medium",
                "bucket": "gate_rule_candidate",
                "regression_candidate": True,
                "priority": "p0",
                "rationale": "Conditional or temporal fragment should hold the turn instead of defaulting to reply.",
            }
        return {
            "suggested_mode": "wait",
            "confidence": "low",
            "bucket": "ambiguous_owner_review",
            "regression_candidate": False,
            "priority": "p1",
            "rationale": "Possible fragment, but needs owner review before becoming a rule case.",
        }

    return {
        "suggested_mode": expected,
        "confidence": "low",
        "bucket": "ambiguous_owner_review",
        "regression_candidate": False,
        "priority": "p2",
        "rationale": "Unhandled miss pattern; keep for owner review only.",
    }


def make_review_row(
    *,
    index: int,
    case_row: dict[str, Any],
    gate_result: dict[str, Any],
) -> dict[str, Any]:
    payload = payload_for_row(case_row)
    expected = expected_for_row(case_row)
    text = normalize_text(payload.get("u") or gate_result.get("u"))
    suggestion = suggestion_for(
        text,
        str(gate_result.get("expected_mode") or ""),
        str(gate_result.get("actual_mode") or ""),
        str(gate_result.get("reason") or ""),
    )
    return {
        "id": f"xinyu-maia-unseen-daily-miss-review-v001-{index:04d}",
        "source_case_id": case_row.get("id"),
        "kind": "xinyu_maia_behavior_miss_review_case",
        "language": "zh",
        "source": "cped_official_public_split_prompt_only",
        "source_license": case_row.get("source_license"),
        "source_license_url": case_row.get("source_license_url"),
        "source_url": case_row.get("source_url"),
        "source_row_id": case_row.get("source_row_id"),
        "user_text": text,
        "context": {
            "act": payload.get("act"),
            "emotion": payload.get("emotion"),
            "scene": payload.get("scene"),
            "sentiment": payload.get("sentiment"),
            "source_split": payload.get("source_split"),
            "surface": payload.get("surface"),
        },
        "gate_result": {
            "expected_mode": gate_result.get("expected_mode"),
            "actual_mode": gate_result.get("actual_mode"),
            "gate_reason": gate_result.get("reason"),
            "original_label_reason": expected.get("label_reason"),
            "original_label_status": expected.get("label_status"),
        },
        "review_suggestion": suggestion,
        "owner_review": {
            "status": "pending_owner_review",
            "final_mode": "",
            "accept_suggestion": None,
            "include_in_gate_regression": False,
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
            "xinyu_maia_behavior_unseen_daily_miss_review_v001",
            "not_training",
            "shadow_only",
            "needs_owner_review",
            str(suggestion["bucket"]),
            str(suggestion["priority"]),
        ],
    }


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if LOCAL_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into miss review")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into miss review")
    for row in rows:
        if row.get("owner_review", {}).get("status") != "pending_owner_review":
            raise RuntimeError(f"{row.get('id')}: owner review status must remain pending")
        if row.get("boundaries", {}).get("training_allowed") is not False:
            raise RuntimeError(f"{row.get('id')}: review row must not allow training")


def markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# XinYu Maia unseen daily miss review v001",
        "",
        "These are gate misses from the CPED prompt-only unseen daily shadow benchmark. Suggestions are not gold labels.",
        "",
        "```text",
        f"miss_rows={len(rows)}",
        "suggested_mode_counts="
        + json.dumps(Counter(str(row["review_suggestion"]["suggested_mode"]) for row in rows), ensure_ascii=False, sort_keys=True),
        "bucket_counts="
        + json.dumps(Counter(str(row["review_suggestion"]["bucket"]) for row in rows), ensure_ascii=False, sort_keys=True),
        "training_allowed=false",
        "public_dialogue_reply_used_as_target=false",
        "```",
        "",
        "| id | text | expected | actual | suggest | bucket | priority | rationale |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        text = str(row["user_text"]).replace("|", "\\|")
        rationale = str(row["review_suggestion"]["rationale"]).replace("|", "\\|")
        if len(text) > 30:
            text = text[:27].rstrip() + "..."
        if len(rationale) > 74:
            rationale = rationale[:71].rstrip() + "..."
        lines.append(
            f"| {row['id']} | {text} | {row['gate_result']['expected_mode']} | "
            f"{row['gate_result']['actual_mode']} | {row['review_suggestion']['suggested_mode']} | "
            f"{row['review_suggestion']['bucket']} | {row['review_suggestion']['priority']} | {rationale} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    benchmark_rows = {str(row.get("id")): row for row in read_jsonl(BENCHMARK)}
    gate_report = json.loads(GATE_REPORT.read_text(encoding="utf-8"))
    misses = [item for item in gate_report.get("results", []) if isinstance(item, dict) and not item.get("match")]
    review_rows: list[dict[str, Any]] = []
    for index, result in enumerate(misses, start=1):
        case_id = str(result.get("id"))
        case_row = benchmark_rows.get(case_id)
        if case_row is None:
            raise RuntimeError(f"missing benchmark row for gate miss {case_id}")
        review_rows.append(make_review_row(index=index, case_row=case_row, gate_result=result))

    assert_safe(review_rows)
    write_jsonl(OUT_JSONL, review_rows)

    report = {
        "generated_at": "2026-05-29",
        "status": "miss_review_queue_built_not_training",
        "source_benchmark": str(BENCHMARK.relative_to(ROOT)).replace("\\", "/"),
        "source_gate_report": str(GATE_REPORT.relative_to(ROOT)).replace("\\", "/"),
        "review_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "review_markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "miss_rows": len(review_rows),
        "expected_actual_counts": dict(
            sorted(Counter(f"{row['gate_result']['expected_mode']}->{row['gate_result']['actual_mode']}" for row in review_rows).items())
        ),
        "suggested_mode_counts": dict(
            sorted(Counter(str(row["review_suggestion"]["suggested_mode"]) for row in review_rows).items())
        ),
        "bucket_counts": dict(sorted(Counter(str(row["review_suggestion"]["bucket"]) for row in review_rows).items())),
        "priority_counts": dict(sorted(Counter(str(row["review_suggestion"]["priority"]) for row in review_rows).items())),
        "regression_candidate_count": sum(1 for row in review_rows if row["review_suggestion"]["regression_candidate"]),
        "owner_review_pending_count": len(review_rows),
        "training_targets_created": False,
        "public_dialogue_replies_used_as_targets": False,
        "assistant_visible_reply_used_as_target": False,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "Suggestions are triage labels only, not gold owner-reviewed labels.",
            "gate_rule_candidate rows are plausible generic rule fixes after owner review.",
            "label_check rows indicate the original heuristic expected mode is likely wrong or too context-dependent.",
            "ambiguous_owner_review rows should not be converted to regression without manual decision.",
        ],
    }
    dump_json(OUT_REPORT, report)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown_table(review_rows), encoding="utf-8")

    print(f"miss_rows={len(review_rows)}")
    print("expected_actual_counts=" + json.dumps(report["expected_actual_counts"], ensure_ascii=False, sort_keys=True))
    print("suggested_mode_counts=" + json.dumps(report["suggested_mode_counts"], ensure_ascii=False, sort_keys=True))
    print("bucket_counts=" + json.dumps(report["bucket_counts"], ensure_ascii=False, sort_keys=True))
    print(f"review_jsonl={OUT_JSONL.relative_to(ROOT)}")
    print(f"review_markdown={OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
