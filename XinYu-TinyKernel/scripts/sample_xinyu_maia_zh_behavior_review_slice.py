from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_pool_v001.jsonl"
OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_review_slice_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_candidate_review_slice_v001.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_candidate_review_slice_v001.md"


TARGET_MODE_COUNTS = {"reply": 60, "clarify": 24, "wait": 12}
EMOTION_ORDER = [
    "anger",
    "astonished",
    "depress",
    "disgust",
    "fear",
    "grateful",
    "happy",
    "negative-other",
    "positive-other",
    "relaxed",
    "sadness",
    "worried",
]


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


def select_mode_rows(rows: list[dict[str, Any]], mode: str, needed: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        emotion = str((row.get("context") or {}).get("emotion") or "")
        buckets[emotion].append(row)
    selected: list[dict[str, Any]] = []
    index = 0
    while len(selected) < needed:
        progressed = False
        for emotion in EMOTION_ORDER:
            bucket = buckets.get(emotion, [])
            if index < len(bucket):
                selected.append(bucket[index])
                progressed = True
                if len(selected) >= needed:
                    break
        if not progressed:
            break
        index += 1
    if len(selected) != needed:
        raise RuntimeError(f"not enough {mode} rows: needed={needed}, got={len(selected)}")
    return selected


def main() -> int:
    pool_rows = read_jsonl(POOL)
    candidates = [
        row
        for row in pool_rows
        if row.get("review_level") == "assistant_suggested_needs_owner_review"
        and (row.get("draft_review") or {}).get("training_allowed") is not True
    ]
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_mode[str((row.get("expected") or {}).get("mode") or "")].append(row)

    selected: list[dict[str, Any]] = []
    for mode, needed in TARGET_MODE_COUNTS.items():
        selected.extend(select_mode_rows(by_mode[mode], mode, needed))

    selected.sort(key=lambda row: (str((row.get("context") or {}).get("emotion") or ""), str(row.get("id") or "")))
    slice_rows: list[dict[str, Any]] = []
    for index, row in enumerate(selected, start=1):
        review = {
            "status": "owner_review_needed",
            "accept_mode": "",
            "accept_reply_bias": "",
            "alive_feeling_score_1_to_5": None,
            "too_much_clarify": None,
            "too_cold": None,
            "too_assistant_like": None,
            "owner_notes": "",
            "target_reply_bias": "",
            "convert_to_training_candidate": False,
        }
        slice_rows.append(
            {
                "slice_id": f"xinyu-maia-zh-behavior-review-slice-v001-{index:03d}",
                "candidate_id": row.get("id"),
                "source_id": row.get("source_id"),
                "user_text": row.get("user_text"),
                "context": row.get("context"),
                "expected_suggestion": row.get("expected"),
                "anti_patterns": row.get("anti_patterns"),
                "owner_review": review,
                "training_allowed": False,
            }
        )

    write_jsonl(OUT_JSONL, slice_rows)
    mode_counts = Counter(str(row["expected_suggestion"]["mode"]) for row in slice_rows)
    emotion_counts = Counter(str((row.get("context") or {}).get("emotion") or "") for row in slice_rows)
    report = {
        "generated_at": "2026-05-28",
        "status": "owner_review_slice_not_training",
        "source_pool": str(POOL.relative_to(ROOT)).replace("\\", "/"),
        "output_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "output_markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(slice_rows),
        "target_mode_counts": TARGET_MODE_COUNTS,
        "mode_counts": dict(sorted(mode_counts.items())),
        "emotion_counts": dict(sorted(emotion_counts.items())),
        "training_allowed": False,
        "training_targets_created": False,
        "target_reply_bias_written": 0,
        "notes": [
            "Sampled only assistant-suggested candidate pool rows, not the 27 reviewed seed rows.",
            "This is a review worksheet and does not promote rows to training.",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# XinYu Maia 中文行为候选审查切片 v001",
        "",
        "96 条从 500 条候选池中抽出的审查样本。这里不是训练集；只有你确认/改写后才可能转训练候选。",
        "",
        "```text",
        f"row_count={report['row_count']}",
        "mode_counts=" + json.dumps(report["mode_counts"], ensure_ascii=False, sort_keys=True),
        "target_reply_bias_written=0",
        "training_targets_created=false",
        "```",
        "",
    ]
    for row in slice_rows:
        expected = row["expected_suggestion"]
        context = row["context"] or {}
        lines.extend(
            [
                f"## {row['slice_id']} / {row['candidate_id']}",
                "",
                f"- 原句：{row['user_text']}",
                f"- 建议模式：{expected['mode']}",
                f"- 情绪/场景：{context.get('emotion')} / {context.get('sentiment')} / {context.get('dialog_act')} / {context.get('scene')}",
                f"- 建议回复倾向：{expected['reply_bias']}",
                f"- 避免：{'；'.join(row.get('anti_patterns') or [])}",
                "",
                "```text",
                "accept_mode=",
                "accept_reply_bias=",
                "alive=",
                "too_much_clarify=",
                "too_cold=",
                "too_assistant_like=",
                "owner_notes=",
                "target_reply_bias=",
                "training_candidate=no",
                "```",
                "",
            ]
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"row_count={len(slice_rows)}")
    print("mode_counts=" + json.dumps(report["mode_counts"], ensure_ascii=False, sort_keys=True))
    print(f"report={OUT_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
