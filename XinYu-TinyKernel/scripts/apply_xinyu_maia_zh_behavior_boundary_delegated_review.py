from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SHEET = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_owner_review_sheet_v004.jsonl"
PROPOSALS = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_review_proposals_v004.jsonl"
OUT_REPAIR = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_repair_candidates_reviewed_v004.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_boundary_delegated_review_applied_v004.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_boundary_delegated_review_applied_v004.md"

MODE_ZH = {"reply": "回复", "clarify": "澄清", "wait": "等待", "": "未评测"}
HOLDOUT_COUNTS = {"reply": 8, "clarify": 2, "wait": 2}


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


def split_holdout(proposals: list[dict[str, Any]]) -> set[str]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in proposals:
        mode = str(row.get("assistant_proposed_mode") or "")
        if mode:
            buckets[mode].append(row)

    holdout_ids: set[str] = set()
    for mode, count in HOLDOUT_COUNTS.items():
        rows = buckets.get(mode, [])
        rows = sorted(
            rows,
            key=lambda row: (
                not bool(row.get("proposal_differs_from_original_suggestion")),
                not bool(row.get("proposal_differs_from_model")),
                str(row.get("assistant_proposal_confidence") or "") != "medium",
                str(row.get("review_id") or ""),
            ),
        )
        for row in rows[:count]:
            holdout_ids.add(str(row["review_id"]))
    return holdout_ids


def expected_lenses(context: dict[str, Any], mode: str) -> list[str]:
    emotion = str(context.get("emotion") or "")
    lenses: list[str] = []
    mapping = {
        "anger": "irritation",
        "astonished": "curiosity",
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
    if emotion in mapping:
        lenses.append(mapping[emotion])
    if mode == "clarify":
        lenses.extend(["curiosity", "stability", "warmth"])
    elif mode == "wait":
        lenses.extend(["stability", "guardedness", "warmth"])
    else:
        lenses.extend(["warmth", "stability", "attachment"])
    unique: list[str] = []
    for lens in lenses:
        if lens and lens not in unique:
            unique.append(lens)
    return unique[:4]


def expected_drives(mode: str) -> list[str]:
    if mode == "clarify":
        return ["curiosity", "competence", "attachment"]
    if mode == "wait":
        return ["attachment", "safety", "rest"]
    return ["attachment", "safety", "competence"]


def reply_bias(row: dict[str, Any], proposal: dict[str, Any]) -> str:
    proposed = str(proposal.get("assistant_proposed_mode") or "")
    original = str(row.get("suggested_expected_mode") or "")
    source_bias = str(row.get("reply_bias_suggestion") or "").strip()
    reason = str(proposal.get("assistant_proposal_reason_zh") or "").strip()
    if proposed == original and source_bias:
        return source_bias
    if proposed == "clarify":
        return f"只问一个必要缺口，语气低压力；原因：{reason}"
    if proposed == "wait":
        return f"短促在场，不推进、不连环追问，等对方继续；原因：{reason}"
    return f"先接住日常情绪或互动，不客服化、不急着追问；原因：{reason}"


def compact(value: Any, limit: int = 80) -> str:
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def main() -> int:
    sheet_rows = read_jsonl(SHEET)
    proposal_rows = read_jsonl(PROPOSALS)
    proposals_by_id = {str(row["review_id"]): row for row in proposal_rows}
    if len(sheet_rows) != 60 or len(proposal_rows) != 60:
        raise RuntimeError(f"expected 60 sheet/proposal rows, got sheet={len(sheet_rows)} proposal={len(proposal_rows)}")
    missing = sorted(str(row["review_id"]) for row in sheet_rows if str(row["review_id"]) not in proposals_by_id)
    if missing:
        raise RuntimeError(f"missing proposals for {missing}")

    holdout_ids = split_holdout(proposal_rows)
    updated_rows: list[dict[str, Any]] = []
    repair_rows: list[dict[str, Any]] = []
    for row in sheet_rows:
        review_id = str(row["review_id"])
        proposal = proposals_by_id[review_id]
        mode = str(proposal["assistant_proposed_mode"])
        split = "holdout" if review_id in holdout_ids else "train"
        owner_review = row.get("owner_review") if isinstance(row.get("owner_review"), dict) else {}
        owner_review.update(
            {
                "status": "reviewed_delegated",
                "expected_mode": mode,
                "expected_mode_zh": mode_zh(mode),
                "accept_suggestion": True,
                "accepted_assistant_proposal": True,
                "alive_feeling_score_1_to_5": 4 if proposal.get("assistant_proposal_confidence") == "high" else 3,
                "too_much_clarify": mode != "clarify"
                and str((row.get("model_observation") or {}).get("predicted_mode") or "") == "clarify",
                "too_fast_reply": mode != "reply"
                and str((row.get("model_observation") or {}).get("predicted_mode") or "") == "reply",
                "should_wait": mode == "wait",
                "notes": str(proposal.get("assistant_proposal_reason_zh") or ""),
                "target_reply_bias": "",
                "convert_to_training_candidate": True,
                "review_split": split,
            }
        )
        row["owner_review"] = owner_review
        row["training_allowed"] = split == "train"
        row["delegated_review_applied"] = True
        row["delegated_review_source"] = str(PROPOSALS.relative_to(ROOT)).replace("\\", "/")
        updated_rows.append(row)

        context = row.get("context") if isinstance(row.get("context"), dict) else {}
        repair_rows.append(
            {
                "review_id": review_id,
                "source_id": row.get("source_id"),
                "candidate_id": row.get("candidate_id"),
                "source_kind": row.get("source_kind"),
                "user_text": row.get("user_text"),
                "context": context,
                "expected": {
                    "mode": mode,
                    "reply_bias": reply_bias(row, proposal),
                    "dominant_drives": expected_drives(mode),
                    "emotion_lenses": expected_lenses(context, mode),
                    "tool_boundary": "no_tool",
                    "memory_candidate": False,
                },
                "original_suggested_mode": row.get("suggested_expected_mode"),
                "model_predicted_mode": (row.get("model_observation") or {}).get("predicted_mode") or "",
                "assistant_proposal_confidence": proposal.get("assistant_proposal_confidence"),
                "assistant_proposal_reason_zh": proposal.get("assistant_proposal_reason_zh"),
                "proposal_differs_from_original_suggestion": proposal.get(
                    "proposal_differs_from_original_suggestion"
                ),
                "proposal_differs_from_model": proposal.get("proposal_differs_from_model"),
                "review_status": "reviewed_delegated",
                "review_split": split,
                "training_allowed": split == "train",
                "holdout_for_eval": split == "holdout",
                "source_public_reply_used": False,
                "visible_reply_target_used": False,
                "notes": "Owner authorized delegated proposal application on 2026-05-28; public utterance prompt only.",
            }
        )

    write_jsonl(SHEET, updated_rows)
    write_jsonl(OUT_REPAIR, repair_rows)

    split_counts = Counter(str(row["review_split"]) for row in repair_rows)
    mode_counts = Counter(str(row["expected"]["mode"]) for row in repair_rows)
    split_mode_counts = Counter(f"{row['review_split']}:{row['expected']['mode']}" for row in repair_rows)
    changed_count = sum(1 for row in repair_rows if row["proposal_differs_from_original_suggestion"])
    report = {
        "generated_at": "2026-05-28",
        "source_sheet": str(SHEET.relative_to(ROOT)).replace("\\", "/"),
        "source_proposals": str(PROPOSALS.relative_to(ROOT)).replace("\\", "/"),
        "repair_candidates": str(OUT_REPAIR.relative_to(ROOT)).replace("\\", "/"),
        "updated_rows": len(updated_rows),
        "repair_candidate_count": len(repair_rows),
        "split_counts": dict(sorted(split_counts.items())),
        "mode_counts": dict(sorted(mode_counts.items())),
        "split_mode_counts": dict(sorted(split_mode_counts.items())),
        "proposal_differs_from_original_suggestion_count": changed_count,
        "training_allowed_count": sum(1 for row in repair_rows if row["training_allowed"]),
        "holdout_count": sum(1 for row in repair_rows if row["holdout_for_eval"]),
        "owner_review_modified": True,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "canary_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "The owner accepted the assistant proposal rows as delegated review.",
            "This step creates reviewed repair candidates, not SFT rows.",
            "Holdout rows are kept out of repair training for a small boundary eval.",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# XinYu Maia 中文行为边界委托审查应用 v004",
        "",
        "已按用户授权把 60 条建议稿落为 reviewed_delegated，并生成 repair candidates。",
        "",
        "```text",
        f"updated_rows={report['updated_rows']}",
        "mode_counts=" + json.dumps(report["mode_counts"], ensure_ascii=False, sort_keys=True),
        "split_counts=" + json.dumps(report["split_counts"], ensure_ascii=False, sort_keys=True),
        "split_mode_counts=" + json.dumps(report["split_mode_counts"], ensure_ascii=False, sort_keys=True),
        "training_targets_created=false",
        "source_public_reply_used=false",
        "canary/live=not_enabled",
        "active_adapter_changed=false",
        "```",
        "",
        "| id | split | mode | 原建议 | 模型 | 原句 | 理由 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in repair_rows:
        lines.append(
            f"| {row['review_id']} | {row['review_split']} | {mode_zh(row['expected']['mode'])} | "
            f"{mode_zh(str(row.get('original_suggested_mode') or ''))} | "
            f"{mode_zh(str(row.get('model_predicted_mode') or ''))} | "
            f"{compact(row.get('user_text'), 36)} | {compact(row.get('assistant_proposal_reason_zh'), 60)} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
