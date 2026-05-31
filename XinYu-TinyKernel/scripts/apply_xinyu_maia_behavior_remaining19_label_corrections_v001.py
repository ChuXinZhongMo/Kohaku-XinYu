from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "server"))

from build_xinyu_maia_behavior_unseen_daily_benchmark_v001 import dumps_compact, mode_target
from schemas import normalize_inner_system


SOURCE_BENCHMARK = ROOT / "data" / "eval" / "xinyu_maia_behavior_unseen_daily_shadow_v001.jsonl"
REMAINING19_REVIEW = ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_remaining19_review_v001.jsonl"

OUT_BENCHMARK = ROOT / "data" / "eval" / "xinyu_maia_behavior_unseen_daily_shadow_v001a_label_corrected.jsonl"
OUT_APPLIED_REVIEW = (
    ROOT / "data" / "review" / "xinyu_maia_behavior_unseen_daily_remaining19_review_applied_v001.jsonl"
)
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_shadow_v001a_label_corrected_build.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_shadow_v001a_label_corrected.md"

OWNER_APPROVAL = "owner accepted remaining19 assistant recommendations in chat on 2026-05-29"


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


def payload_for_row(row: dict[str, Any]) -> dict[str, Any]:
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    if len(messages) < 2 or not isinstance(messages[1], dict):
        return {}
    try:
        parsed = json.loads(str(messages[1].get("content") or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def target_for_mode(mode: str, reason: str) -> dict[str, Any]:
    target = mode_target(mode, reason)
    if normalize_inner_system(target) is None:
        raise RuntimeError(f"invalid corrected target for mode={mode}")
    return target


def apply_correction(row: dict[str, Any], correction: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(row, ensure_ascii=False))
    old_expected = out.get("expected_behavior") if isinstance(out.get("expected_behavior"), dict) else {}
    old_mode = str(old_expected.get("mode") or "")
    new_mode = str(correction.get("assistant_recommendation", {}).get("final_mode") or "")
    if new_mode not in {"reply", "clarify", "wait"}:
        raise RuntimeError(f"{row.get('id')}: invalid correction mode {new_mode!r}")

    reason = "owner_approved_remaining19_label_correction_v001"
    target = target_for_mode(new_mode, reason)

    expected = dict(old_expected)
    expected["previous_mode"] = old_mode
    expected["mode"] = new_mode
    expected["label_status"] = "owner_approved_label_corrected_v001a"
    expected["label_reason"] = reason
    expected["correction_source_review_id"] = correction.get("id")
    expected["correction_owner_approval"] = OWNER_APPROVAL
    expected["emotion_lenses"] = list(target["emotion_state"].keys())
    expected["dominant_drives"] = list(target["dominant_drives"])
    expected["memory_candidate"] = False
    expected["tool_boundary"] = "no_tool"
    out["expected_behavior"] = expected

    messages = out.get("messages") if isinstance(out.get("messages"), list) else []
    if len(messages) != 3:
        raise RuntimeError(f"{row.get('id')}: expected three messages")
    payload = payload_for_row(out)
    payload["label_status"] = "owner_approved_label_corrected_v001a"
    payload["label_reason"] = reason
    payload["previous_expected_mode"] = old_mode
    payload["owner_approval"] = OWNER_APPROVAL
    messages[1]["content"] = dumps_compact(payload)
    messages[2]["content"] = dumps_compact(target)
    out["messages"] = messages

    tags = list(out.get("tags") or [])
    for tag in ("v001a_label_corrected", "owner_approved_label_correction"):
        if tag not in tags:
            tags.append(tag)
    out["tags"] = tags
    return out


def apply_review_row(row: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(row, ensure_ascii=False))
    final_mode = str(out.get("assistant_recommendation", {}).get("final_mode") or "")
    out["owner_review"] = {
        "status": "owner_approved",
        "final_mode": final_mode,
        "accept_assistant_recommendation": True,
        "include_in_gate_regression": False,
        "include_in_label_corrected_shadow": True,
        "notes": OWNER_APPROVAL,
    }
    tags = list(out.get("tags") or [])
    for tag in ("owner_approved", "applied_to_v001a_label_corrected"):
        if tag not in tags:
            tags.append(tag)
    out["tags"] = tags
    return out


def mode_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get("expected_behavior", {}).get("mode") or "") for row in rows).items()))


def markdown(rows: list[dict[str, Any]], applied: list[dict[str, Any]]) -> str:
    correction_by_case = {str(row.get("source_case_id")): row for row in applied}
    lines = [
        "# XinYu Maia unseen daily shadow v001a label-corrected",
        "",
        "Owner-approved remaining19 label corrections applied. This is still shadow/report-only, not training data.",
        "",
        "```text",
        f"row_count={len(rows)}",
        "mode_counts=" + json.dumps(mode_counts(rows), ensure_ascii=False, sort_keys=True),
        f"applied_corrections={len(applied)}",
        "training_targets_created=false",
        "public_dialogue_replies_used_as_targets=false",
        "```",
        "",
        "| id | mode | status | text |",
        "|---|---|---|---|",
    ]
    for row in rows:
        payload = payload_for_row(row)
        expected = row.get("expected_behavior", {})
        status = expected.get("label_status", "")
        if str(row.get("id")) in correction_by_case:
            status = "corrected:" + str(expected.get("previous_mode")) + "->" + str(expected.get("mode"))
        text = str(payload.get("u") or "").replace("|", "\\|")
        if len(text) > 42:
            text = text[:39].rstrip() + "..."
        lines.append(f"| {row.get('id')} | {expected.get('mode')} | {status} | {text} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    source_rows = read_jsonl(SOURCE_BENCHMARK)
    corrections = read_jsonl(REMAINING19_REVIEW)
    if len(source_rows) != 90:
        raise RuntimeError(f"expected 90 source rows, got {len(source_rows)}")
    if len(corrections) != 19:
        raise RuntimeError(f"expected 19 corrections, got {len(corrections)}")

    correction_by_case = {str(row.get("source_case_id")): row for row in corrections}
    out_rows: list[dict[str, Any]] = []
    for row in source_rows:
        case_id = str(row.get("id"))
        correction = correction_by_case.get(case_id)
        out_rows.append(apply_correction(row, correction) if correction else json.loads(json.dumps(row, ensure_ascii=False)))

    applied_review = [apply_review_row(row) for row in corrections]
    write_jsonl(OUT_BENCHMARK, out_rows)
    write_jsonl(OUT_APPLIED_REVIEW, applied_review)

    report = {
        "generated_at": "2026-05-29",
        "status": "label_corrected_shadow_benchmark_built_not_training",
        "source_benchmark": str(SOURCE_BENCHMARK.relative_to(ROOT)).replace("\\", "/"),
        "source_remaining19_review": str(REMAINING19_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "output_benchmark": str(OUT_BENCHMARK.relative_to(ROOT)).replace("\\", "/"),
        "applied_review": str(OUT_APPLIED_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "owner_approval": OWNER_APPROVAL,
        "row_count": len(out_rows),
        "applied_correction_count": len(applied_review),
        "source_mode_counts": mode_counts(source_rows),
        "corrected_mode_counts": mode_counts(out_rows),
        "correction_counts": dict(
            sorted(
                Counter(
                    f"{row.get('original_gate_result', {}).get('expected_mode')}->{row.get('assistant_recommendation', {}).get('final_mode')}"
                    for row in corrections
                ).items()
            )
        ),
        "training_targets_created": False,
        "public_dialogue_replies_used_as_targets": False,
        "assistant_visible_reply_used_as_target": False,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "This applies owner-approved label corrections only.",
            "No behavior gate rule is changed by this step.",
            "This benchmark is report-only and must not be used as training data.",
        ],
    }
    dump_json(OUT_REPORT, report)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown(out_rows, applied_review), encoding="utf-8")

    print(f"row_count={len(out_rows)}")
    print(f"applied_correction_count={len(applied_review)}")
    print("source_mode_counts=" + json.dumps(report["source_mode_counts"], ensure_ascii=False, sort_keys=True))
    print("corrected_mode_counts=" + json.dumps(report["corrected_mode_counts"], ensure_ascii=False, sort_keys=True))
    print("correction_counts=" + json.dumps(report["correction_counts"], ensure_ascii=False, sort_keys=True))
    print(f"output_benchmark={OUT_BENCHMARK.relative_to(ROOT)}")
    print(f"applied_review={OUT_APPLIED_REVIEW.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
