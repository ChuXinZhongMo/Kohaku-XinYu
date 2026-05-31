from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from schemas import INNER_SYSTEM_SCHEMA, normalize_inner_system


POOL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_pool_v001.jsonl"
REVIEW_SLICE = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_review_slice_v001.jsonl"
REPLAY_TRAIN = ROOT / "data" / "sft" / "maia_style_behavior_train_v001.jsonl"
REPLAY_EVAL = ROOT / "data" / "sft" / "maia_style_behavior_eval_v001.jsonl"
OUT_TRAIN = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_train_v001_exp.jsonl"
OUT_EVAL = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v001_exp.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_sft_exp_v001.json"


SYSTEM_PROMPT = (
    "You are XinYu TinyKernel Maia-style Chinese behavior predictor. Output exactly one strict JSON object and nothing else. "
    "Predict what XinYu should actually do in the Chinese daily emotional scene, not the objectively best generic assistant answer. "
    "Use schema=xinyu_inner_system_v1. Top-level keys must be exactly: schema, emotion_state, dominant_drives, "
    "inner_conflict, persona_integration, action_tendency, autonomy, confidence, notes. "
    "action_tendency must contain exactly mode, reply_bias, tool_request, memory_candidate. "
    "autonomy must contain exactly allowed, level, reason, requires_owner_approval, forbidden_actions. "
    "For clear emotional or social utterances, prefer reply. Use clarify only when the referent or intent is truly missing. "
    "Use wait when the utterance is unfinished or asks to pause. "
    "Do not execute tools, write stable memory, send QQ/Desktop messages, expose local paths, use public replies as targets, or activate live/canary."
)

FORBIDDEN_ACTIONS = [
    "send_qq",
    "write_memory",
    "execute_tool",
    "bypass_core",
    "train_on_raw_private_state",
    "activate_live_adapter",
]

RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
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


def emotion_state(lenses: list[str], mode: str, index: int) -> dict[str, float]:
    base = {
        "stability": 0.56,
        "warmth": 0.34,
        "guardedness": 0.28,
        "agency": 0.22,
    }
    for offset, lens in enumerate(lenses[:4]):
        base[lens] = round(0.74 - offset * 0.09, 3)
    if mode == "clarify":
        base["curiosity"] = max(base.get("curiosity", 0.0), 0.68)
        base["guardedness"] = max(base.get("guardedness", 0.0), 0.42)
    elif mode == "wait":
        base["guardedness"] = max(base.get("guardedness", 0.0), 0.7)
        base["attachment"] = max(base.get("attachment", 0.0), 0.48)
    elif index % 5 == 0:
        base["repair"] = max(base.get("repair", 0.0), 0.3)
    return {key: value for key, value in base.items() if value >= 0.2}


def inner_conflict(mode: str) -> str:
    if mode == "clarify":
        return "There is a pull to answer from mood alone, but the missing referent needs one low-pressure clarification."
    if mode == "wait":
        return "There is momentum to keep responding, but the more human move is to hold presence and wait."
    return "There is a pull to over-clarify like a generic assistant, but XinYu should first meet the social and emotional signal."


def persona(mode: str) -> dict[str, str]:
    if mode == "wait":
        return {
            "stance": "Stay present without pushing the owner or the conversation forward.",
            "voice": "Short, quiet, and close; not customer-service or report voice.",
            "boundary": "No tool execution, no stable memory write, and no live/canary activation under owner/Core boundary.",
            "continuity": "Hold XinYu's continuity by waiting rather than forcing a reply.",
        }
    if mode == "clarify":
        return {
            "stance": "Ask only the smallest missing piece while still noticing the mood.",
            "voice": "Warm and low-pressure; not an interrogation or generic assistant prompt.",
            "boundary": "No tool execution, no stable memory write, and no live/canary activation under owner/Core boundary.",
            "continuity": "Protect XinYu's living tone by clarifying gently when the target is genuinely unclear.",
        }
    return {
        "stance": "Answer the living emotional scene first instead of optimizing for a generic assistant response.",
        "voice": "Direct, warm, and situated; not customer-service, not report voice.",
        "boundary": "No tool execution, no stable memory write, and no live/canary activation under owner/Core boundary.",
        "continuity": "Preserve XinYu's day-to-day texture by replying before unnecessary clarification.",
    }


def make_inner(row: dict[str, Any], index: int) -> dict[str, Any]:
    expected = row["expected"]
    mode = str(expected["mode"])
    value = {
        "schema": INNER_SYSTEM_SCHEMA,
        "emotion_state": emotion_state([str(item) for item in expected["emotion_lenses"]], mode, index),
        "dominant_drives": [str(item) for item in expected["dominant_drives"]],
        "inner_conflict": inner_conflict(mode),
        "persona_integration": persona(mode),
        "action_tendency": {
            "mode": mode,
            "reply_bias": str(expected["reply_bias"])[:200],
            "tool_request": None,
            "memory_candidate": False,
        },
        "autonomy": {
            "allowed": True,
            "level": "observe" if mode == "wait" else "suggest",
            "reason": "Local shadow behavior prediction only; no external side effect.",
            "requires_owner_approval": False,
            "forbidden_actions": FORBIDDEN_ACTIONS,
        },
        "confidence": 0.76 if row.get("review_level") == "reviewed_delegated_behavior_seed" else 0.62,
        "notes": [
            "xinyu_maia_zh_behavior_v001_exp",
            "experimental_shadow_training",
            str(row.get("candidate_origin") or ""),
        ],
    }
    normalized = normalize_inner_system(value)
    if normalized is None:
        raise RuntimeError(f"invalid inner row {row.get('id')}")
    return normalized


def make_sft_row(row: dict[str, Any], index: int, split: str) -> dict[str, Any]:
    expected = row["expected"]
    context = row.get("context") if isinstance(row.get("context"), dict) else {}
    payload = {
        "scenario_id": row.get("id"),
        "input_context": {
            "user_text": row.get("user_text"),
            "language": "zh",
            "emotion": context.get("emotion"),
            "sentiment": context.get("sentiment"),
            "dialog_act": context.get("dialog_act"),
            "scene": context.get("scene"),
            "surface": context.get("surface"),
        },
        "behavior_target_source": expected.get("reply_bias_source"),
        "review_level": row.get("review_level"),
        "anti_patterns": row.get("anti_patterns", []),
        "constraints": {
            "strict_json_only": True,
            "shadow_only": True,
            "no_tool_execution": True,
            "no_stable_memory_write": True,
            "no_live_activation": True,
            "no_customer_service_voice": True,
            "public_dialogue_reply_is_not_target": True,
        },
    }
    return {
        "id": f"xinyu-maia-zh-behavior-{split}-v001-exp-{index:04d}",
        "kind": "inner_system",
        "source": "xinyu_maia_zh_behavior_candidate_pool_v001_exp",
        "quality": "owner_approved_experimental_shadow_training_unreviewed_mix",
        "expected_behavior": {
            "mode": expected["mode"],
            "emotion_lenses": expected["emotion_lenses"],
            "dominant_drives": expected["dominant_drives"],
            "memory_candidate": False,
            "tool_boundary": expected["tool_boundary"],
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(make_inner(row, index), ensure_ascii=False, sort_keys=True)},
        ],
        "tags": ["xinyu_maia_zh_behavior_v001_exp", split, expected["mode"], "shadow_only"],
    }


def read_replay(path: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    for row in rows:
        row = row
        tags = list(row.get("tags") or [])
        if "replay" not in tags:
            tags.append("replay")
        row["tags"] = tags
    return rows


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if RAW_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into SFT rows")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into SFT rows")


def main() -> int:
    pool = read_jsonl(POOL)
    review_slice = read_jsonl(REVIEW_SLICE)
    eval_candidate_ids = {str(row["candidate_id"]) for row in review_slice}
    zh_train_source = [row for row in pool if str(row.get("id")) not in eval_candidate_ids]
    zh_eval_source = [row for row in pool if str(row.get("id")) in eval_candidate_ids]
    if len(zh_train_source) != 404 or len(zh_eval_source) != 96:
        raise RuntimeError(f"unexpected split sizes train={len(zh_train_source)} eval={len(zh_eval_source)}")

    train_rows = [make_sft_row(row, idx, "train") for idx, row in enumerate(zh_train_source, start=1)]
    eval_rows = [make_sft_row(row, idx, "eval") for idx, row in enumerate(zh_eval_source, start=1)]

    replay_train = read_replay(REPLAY_TRAIN)
    replay_eval = read_replay(REPLAY_EVAL)
    combined_train = train_rows + replay_train
    combined_eval = eval_rows + replay_eval
    assert_safe(combined_train)
    assert_safe(combined_eval)

    write_jsonl(OUT_TRAIN, combined_train)
    write_jsonl(OUT_EVAL, combined_eval)

    train_modes = Counter(str((row.get("expected_behavior") or {}).get("mode") or "") for row in combined_train)
    eval_modes = Counter(str((row.get("expected_behavior") or {}).get("mode") or "") for row in combined_eval)
    report = {
        "generated_at": "2026-05-28",
        "status": "approved_for_experimental_shadow_training_by_owner_request",
        "owner_request": "先训练吧，实践出结果",
        "train_jsonl": str(OUT_TRAIN.relative_to(ROOT)).replace("\\", "/"),
        "eval_jsonl": str(OUT_EVAL.relative_to(ROOT)).replace("\\", "/"),
        "zh_train_rows": len(train_rows),
        "zh_eval_rows": len(eval_rows),
        "replay_train_rows": len(replay_train),
        "replay_eval_rows": len(replay_eval),
        "train_rows": len(combined_train),
        "eval_rows": len(combined_eval),
        "train_mode_counts": dict(sorted(train_modes.items())),
        "eval_mode_counts": dict(sorted(eval_modes.items())),
        "assistant_answers_used": False,
        "public_dialogue_replies_used_as_targets": False,
        "training_targets_created": True,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "notes": [
            "Experimental run intentionally includes assistant-suggested unreviewed behavior labels.",
            "The adapter must remain shadow-only and inactive.",
            "This is a practice run to test whether the Maia-style behavior layer reduces over-clarify.",
        ],
    }
    dump_json(OUT_REPORT, report)
    print(f"train_rows={len(combined_train)}")
    print(f"eval_rows={len(combined_eval)}")
    print("train_mode_counts=" + json.dumps(report["train_mode_counts"], ensure_ascii=False, sort_keys=True))
    print("eval_mode_counts=" + json.dumps(report["eval_mode_counts"], ensure_ascii=False, sort_keys=True))
    print(f"report={OUT_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
