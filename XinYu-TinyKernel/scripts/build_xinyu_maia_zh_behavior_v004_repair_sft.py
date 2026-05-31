from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_xinyu_maia_zh_behavior_compact_sft import SYSTEM_PROMPT, compact_inner, dumps_compact


BASE_TRAIN = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_train_v003_balanced_compact_exp.jsonl"
BASE_EVAL = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v003_balanced_compact_exp.jsonl"
REPAIR = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_boundary_repair_candidates_reviewed_v004.jsonl"

OUT_TRAIN = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_train_v004_boundary_repair_exp.jsonl"
OUT_EVAL = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v004_boundary_repair_exp.jsonl"
OUT_HOLDOUT = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v004_boundary_holdout12.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_sft_v004_boundary_repair_exp.json"

RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)

REPAIR_REPEAT = {
    "reply": 5,
    "clarify": 12,
    "wait": 16,
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


def repair_payload(row: dict[str, Any]) -> dict[str, Any]:
    context = row.get("context") if isinstance(row.get("context"), dict) else {}
    return {
        "id": row.get("review_id"),
        "u": row.get("user_text"),
        "surface": context.get("surface") or "public_probe_candidate_review_only",
        "act": context.get("dialog_act"),
        "emotion": context.get("emotion"),
        "sentiment": context.get("sentiment"),
        "scene": context.get("scene"),
        "origin": "delegated_review_v004_boundary_repair",
        "source": "public_utterance_prompt_only",
        "guardrails": "shadow/no_tool/no_memory/no_live",
    }


def make_repair_row(row: dict[str, Any], *, index: int, split: str, repeat: int) -> dict[str, Any]:
    expected = row.get("expected") if isinstance(row.get("expected"), dict) else {}
    mode = str(expected.get("mode") or "reply")
    target = compact_inner(
        mode=mode,
        reply_bias=str(expected.get("reply_bias") or mode),
        drives=[str(item) for item in expected.get("dominant_drives", [])],
        lenses=[str(item) for item in expected.get("emotion_lenses", [])],
        source_note=f"delegated_boundary_review_v004_{split}",
        confidence=0.84,
    )
    return {
        "id": f"xinyu-maia-zh-behavior-{split}-v004-boundary-repair-{index:04d}-r{repeat}",
        "kind": "inner_system",
        "source": "xinyu_maia_zh_behavior_boundary_repair_candidates_reviewed_v004",
        "quality": "owner_delegated_reviewed_boundary_repair",
        "source_review_id": row.get("review_id"),
        "expected_behavior": {
            "mode": mode,
            "emotion_lenses": expected.get("emotion_lenses", []),
            "dominant_drives": expected.get("dominant_drives", []),
            "memory_candidate": False,
            "tool_boundary": "no_tool",
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": dumps_compact(repair_payload(row))},
            {"role": "assistant", "content": dumps_compact(target)},
        ],
        "tags": [
            "xinyu_maia_zh_behavior_v004_boundary_repair_exp",
            split,
            mode,
            "delegated_review",
            "shadow_only",
        ],
    }


def mode_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str((row.get("expected_behavior") or {}).get("mode") or "") for row in rows).items()))


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if RAW_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into v004 repair SFT rows")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into v004 repair SFT rows")


def main() -> int:
    base_train = read_jsonl(BASE_TRAIN)
    base_eval = read_jsonl(BASE_EVAL)
    repairs = read_jsonl(REPAIR)
    train_source = [row for row in repairs if row.get("training_allowed") is True]
    holdout_source = [row for row in repairs if row.get("holdout_for_eval") is True]
    if len(repairs) != 60 or len(train_source) != 48 or len(holdout_source) != 12:
        raise RuntimeError(
            f"unexpected repair split rows repair={len(repairs)} train={len(train_source)} holdout={len(holdout_source)}"
        )

    repair_train_rows: list[dict[str, Any]] = []
    for index, row in enumerate(train_source, start=1):
        mode = str((row.get("expected") or {}).get("mode") or "reply")
        for repeat in range(1, REPAIR_REPEAT.get(mode, 4) + 1):
            repair_train_rows.append(make_repair_row(row, index=index, split="train", repeat=repeat))

    holdout_rows = [
        make_repair_row(row, index=index, split="holdout", repeat=1)
        for index, row in enumerate(holdout_source, start=1)
    ]

    combined_train = base_train + repair_train_rows
    combined_eval = base_eval + holdout_rows
    assert_safe(combined_train)
    assert_safe(combined_eval)
    write_jsonl(OUT_TRAIN, combined_train)
    write_jsonl(OUT_EVAL, combined_eval)
    write_jsonl(OUT_HOLDOUT, holdout_rows)

    report = {
        "generated_at": "2026-05-28",
        "status": "approved_for_experimental_shadow_training_by_owner_request",
        "base_train": str(BASE_TRAIN.relative_to(ROOT)).replace("\\", "/"),
        "base_eval": str(BASE_EVAL.relative_to(ROOT)).replace("\\", "/"),
        "repair_candidates": str(REPAIR.relative_to(ROOT)).replace("\\", "/"),
        "train_jsonl": str(OUT_TRAIN.relative_to(ROOT)).replace("\\", "/"),
        "eval_jsonl": str(OUT_EVAL.relative_to(ROOT)).replace("\\", "/"),
        "holdout_eval_jsonl": str(OUT_HOLDOUT.relative_to(ROOT)).replace("\\", "/"),
        "base_train_rows": len(base_train),
        "base_eval_rows": len(base_eval),
        "repair_source_rows": len(repairs),
        "repair_train_source_rows": len(train_source),
        "repair_holdout_source_rows": len(holdout_source),
        "repair_train_rows_after_repeat": len(repair_train_rows),
        "holdout_rows": len(holdout_rows),
        "train_rows": len(combined_train),
        "eval_rows": len(combined_eval),
        "repair_repeat": REPAIR_REPEAT,
        "repair_train_mode_counts": mode_counts(repair_train_rows),
        "holdout_mode_counts": mode_counts(holdout_rows),
        "train_mode_counts": mode_counts(combined_train),
        "eval_mode_counts": mode_counts(combined_eval),
        "assistant_answers_used": False,
        "public_dialogue_replies_used_as_targets": False,
        "visible_reply_target_used": False,
        "training_targets_created": True,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "v004 adds owner-delegated reply/clarify/wait boundary repair rows to the v003 compact baseline.",
            "12 delegated rows are held out from repair training for a small boundary eval.",
            "Targets are inner-system JSON action tendencies, not public dialogue replies.",
        ],
    }
    dump_json(OUT_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
