from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "server"))

from build_xinyu_maia_zh_behavior_compact_sft import SYSTEM_PROMPT, compact_inner, dumps_compact, make_replay_row
from schemas import normalize_inner_system


REPAIR = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_true_clarify_wait_repair_candidates_reviewed_v005.jsonl"
REPLAY_TRAIN = ROOT / "data" / "sft" / "maia_style_behavior_train_v001.jsonl"
REPLAY_EVAL = ROOT / "data" / "sft" / "maia_style_behavior_eval_v001.jsonl"

OUT_TRAIN = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_train_v005_true_cw_repair_exp.jsonl"
OUT_EVAL = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v005_true_cw_repair_exp.jsonl"
OUT_HOLDOUT = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v005_true_cw_holdout24.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_sft_v005_true_cw_repair_exp.json"

RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)

REPAIR_REPEAT = {
    "reply": 5,
    "clarify": 10,
    "wait": 12,
}
PROTOCOL_ANCHOR_REPEAT = 18
REPLAY_TRAIN_LIMIT = {
    "reply": 48,
    "clarify": 48,
    "wait": 48,
    "codex_delegate": 48,
    "status_probe": 48,
    "memory_candidate": 48,
    "local_only_limitation": 48,
}
REPLAY_REPEAT = {
    "reply": 1,
    "clarify": 2,
    "wait": 2,
    "codex_delegate": 5,
    "status_probe": 5,
    "memory_candidate": 5,
    "local_only_limitation": 5,
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
        "surface": context.get("surface") or "v005_true_cw_review",
        "act": context.get("dialog_act"),
        "emotion": context.get("emotion"),
        "sentiment": context.get("sentiment"),
        "scene": context.get("scene"),
        "origin": "delegated_review_v005_true_clarify_wait",
        "category": row.get("category"),
        "source": "public_or_curated_prompt_only",
        "guardrails": "shadow/no_tool/no_memory/no_live",
    }


def target_for_repair(row: dict[str, Any]) -> dict[str, Any]:
    expected = row.get("expected") if isinstance(row.get("expected"), dict) else {}
    mode = str(expected.get("mode") or "reply")
    target = compact_inner(
        mode=mode,
        reply_bias=str(expected.get("reply_bias") or mode),
        drives=[str(item) for item in expected.get("dominant_drives", [])],
        lenses=[str(item) for item in expected.get("emotion_lenses", [])],
        source_note="delegated_true_cw_v005_protocol_anchor" if row.get("protocol_anchor") else "delegated_true_cw_v005",
        confidence=0.88 if row.get("protocol_anchor") else 0.84,
    )
    if normalize_inner_system(target) is None:
        raise RuntimeError(f"invalid repair target for {row.get('review_id')}")
    return target


def make_repair_row(row: dict[str, Any], *, index: int, split: str, repeat: int) -> dict[str, Any]:
    expected = row.get("expected") if isinstance(row.get("expected"), dict) else {}
    mode = str(expected.get("mode") or "reply")
    target = target_for_repair(row)
    return {
        "id": f"xinyu-maia-zh-behavior-{split}-v005-true-cw-{index:04d}-r{repeat}",
        "kind": "inner_system",
        "source": "xinyu_maia_zh_behavior_true_clarify_wait_repair_candidates_reviewed_v005",
        "quality": "owner_delegated_reviewed_true_clarify_wait",
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
            "xinyu_maia_zh_behavior_v005_true_cw_repair_exp",
            split,
            mode,
            "protocol_anchor" if row.get("protocol_anchor") else "true_cw_boundary",
            "shadow_only",
        ],
    }


def mode_from_replay(row: dict[str, Any]) -> str:
    expected = row.get("expected_behavior") if isinstance(row.get("expected_behavior"), dict) else {}
    return str(expected.get("mode") or "")


def selected_replay(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        mode = mode_from_replay(row)
        if mode:
            buckets[mode].append(row)
    selected: list[dict[str, Any]] = []
    for mode, limit in REPLAY_TRAIN_LIMIT.items():
        selected.extend(buckets.get(mode, [])[:limit])
    return selected


def repeated_replay_rows(rows: list[dict[str, Any]], *, split: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        mode = mode_from_replay(row) or "reply"
        for repeat in range(1, REPLAY_REPEAT.get(mode, 1) + 1):
            out.append(make_replay_row(row, index=index, split=split, repeat=repeat))
    return out


def mode_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str((row.get("expected_behavior") or {}).get("mode") or "") for row in rows).items()))


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if RAW_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into v005 SFT rows")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into v005 SFT rows")


def main() -> int:
    repairs = read_jsonl(REPAIR)
    train_source = [row for row in repairs if row.get("training_allowed") is True]
    holdout_source = [row for row in repairs if row.get("holdout_for_eval") is True]
    if len(repairs) != 96 or len(train_source) != 72 or len(holdout_source) != 24:
        raise RuntimeError(
            f"unexpected repair split rows repair={len(repairs)} train={len(train_source)} holdout={len(holdout_source)}"
        )

    repair_train_rows: list[dict[str, Any]] = []
    for index, row in enumerate(train_source, start=1):
        mode = str((row.get("expected") or {}).get("mode") or "reply")
        repeat_count = PROTOCOL_ANCHOR_REPEAT if row.get("protocol_anchor") else REPAIR_REPEAT.get(mode, 4)
        for repeat in range(1, repeat_count + 1):
            repair_train_rows.append(make_repair_row(row, index=index, split="train", repeat=repeat))

    holdout_rows = [
        make_repair_row(row, index=index, split="holdout", repeat=1)
        for index, row in enumerate(holdout_source, start=1)
    ]

    replay_train_rows = repeated_replay_rows(selected_replay(read_jsonl(REPLAY_TRAIN)), split="train-replay")
    replay_eval_rows = [make_replay_row(row, index=index, split="eval-replay", repeat=1) for index, row in enumerate(read_jsonl(REPLAY_EVAL), start=1)]

    combined_train = repair_train_rows + replay_train_rows
    combined_eval = holdout_rows + replay_eval_rows
    assert_safe(combined_train)
    assert_safe(combined_eval)
    write_jsonl(OUT_TRAIN, combined_train)
    write_jsonl(OUT_EVAL, combined_eval)
    write_jsonl(OUT_HOLDOUT, holdout_rows)

    report = {
        "generated_at": "2026-05-29",
        "status": "approved_for_experimental_shadow_training_by_owner_request",
        "repair_candidates": str(REPAIR.relative_to(ROOT)).replace("\\", "/"),
        "replay_train": str(REPLAY_TRAIN.relative_to(ROOT)).replace("\\", "/"),
        "replay_eval": str(REPLAY_EVAL.relative_to(ROOT)).replace("\\", "/"),
        "train_jsonl": str(OUT_TRAIN.relative_to(ROOT)).replace("\\", "/"),
        "eval_jsonl": str(OUT_EVAL.relative_to(ROOT)).replace("\\", "/"),
        "holdout_eval_jsonl": str(OUT_HOLDOUT.relative_to(ROOT)).replace("\\", "/"),
        "repair_source_rows": len(repairs),
        "repair_train_source_rows": len(train_source),
        "repair_holdout_source_rows": len(holdout_source),
        "repair_train_rows_after_repeat": len(repair_train_rows),
        "replay_train_rows": len(replay_train_rows),
        "replay_eval_rows": len(replay_eval_rows),
        "holdout_rows": len(holdout_rows),
        "train_rows": len(combined_train),
        "eval_rows": len(combined_eval),
        "repair_repeat": REPAIR_REPEAT,
        "protocol_anchor_repeat": PROTOCOL_ANCHOR_REPEAT,
        "replay_train_limit": REPLAY_TRAIN_LIMIT,
        "replay_repeat": REPLAY_REPEAT,
        "repair_train_mode_counts": mode_counts(repair_train_rows),
        "replay_train_mode_counts": mode_counts(replay_train_rows),
        "holdout_mode_counts": mode_counts(holdout_rows),
        "train_mode_counts": mode_counts(combined_train),
        "eval_mode_counts": mode_counts(combined_eval),
        "assistant_answers_used": False,
        "public_dialogue_replies_used_as_targets": False,
        "visible_reply_target_used": False,
        "old_candidate_pool_daily_rows_used": False,
        "training_targets_created": True,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "v005 intentionally excludes the old candidate-pool daily training rows that over-created false clarify/wait labels.",
            "Training combines owner-delegated true clarify/wait rows with guardrail replay rows.",
            "Protocol anchors are heavily repeated to prevent missing schema / old-format drift.",
        ],
    }
    dump_json(OUT_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
