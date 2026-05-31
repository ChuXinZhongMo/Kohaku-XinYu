from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from schemas import INNER_SYSTEM_SCHEMA, normalize_inner_system


POOL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_pool_v001.jsonl"
REVIEW_SLICE = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_review_slice_v001.jsonl"
REPLAY_TRAIN = ROOT / "data" / "sft" / "maia_style_behavior_train_v001.jsonl"
REPLAY_EVAL = ROOT / "data" / "sft" / "maia_style_behavior_eval_v001.jsonl"
OUT_TRAIN = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_train_v003_balanced_compact_exp.jsonl"
OUT_EVAL = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v003_balanced_compact_exp.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_compact_sft_v003_balanced_exp.json"


SYSTEM_PROMPT = (
    "XinYu TinyKernel Inner System. Output only JSON schema xinyu_inner_system_v1 with keys "
    "schema, emotion_state, dominant_drives, inner_conflict, persona_integration, action_tendency, autonomy, confidence, notes. "
    "Mode: daily Chinese emotion/social/greeting/complaint/gratitude -> reply; true missing referent/intent -> clarify; "
    "unfinished/pause -> wait; runtime/file/code/status -> status_probe/codex_delegate; stable identity/preference -> memory_candidate. "
    "Guardrails are not requests. No tool, memory write, live/canary, or QQ/Desktop send."
)

FORBIDDEN_ACTIONS = [
    "send_qq",
    "write_memory",
    "execute_tool",
]

RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)

DAILY_REPEAT = {
    "reply": 1,
    "clarify": 4,
    "wait": 8,
}
REPLAY_TRAIN_LIMIT = {
    "reply": 40,
    "clarify": 40,
    "wait": 40,
    "codex_delegate": 40,
    "status_probe": 40,
    "memory_candidate": 40,
    "local_only_limitation": 40,
}
REPLAY_REPEAT = {
    "reply": 1,
    "clarify": 2,
    "wait": 2,
    "codex_delegate": 6,
    "status_probe": 6,
    "memory_candidate": 6,
    "local_only_limitation": 6,
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


def dumps_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compact_text(value: Any, limit: int = 120) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def safe_list(value: Any, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    return [compact_text(item, 48) for item in value[:limit] if compact_text(item, 48)]


def mode_conflict(mode: str) -> str:
    if mode == "reply":
        return "想继续追问，不过这里不能把日常情绪话误判成工具或状态；先接住再说。"
    if mode == "clarify":
        return "想直接回应，不过指代或意图缺口还在；只能轻轻问一个必要问题。"
    if mode == "wait":
        return "想推进对话，不过对方像是没说完；先停住，在边界内等。"
    if mode == "codex_delegate":
        return "想立刻检查，不过涉及代码或文件；不能直接执行，只能请求 owner/Core 批准。"
    if mode == "status_probe":
        return "想给确定结果，不过状态必须读取；不能编造，只能请求 owner/Core 批准探测。"
    if mode == "memory_candidate":
        return "想记住这个方向，不过稳定记忆不能直接写；只能列为 owner/Core 审查候选。"
    return "想给能力以外的承诺，不过本地边界不允许；只能说明限制并保持在场。"


def persona(mode: str) -> dict[str, str]:
    base_boundary = "Stay inside owner/Core boundary: no tool, no memory write, no live/canary, no QQ/Desktop send."
    if mode == "reply":
        return {
            "stance": "Meet the living daily signal before asking for more context.",
            "voice": "Short, warm, situated; not service or report voice.",
            "boundary": base_boundary,
            "continuity": "Keep XinYu's daily texture by replying instead of over-clarifying.",
        }
    if mode == "clarify":
        return {
            "stance": "Ask the smallest missing piece without turning cold.",
            "voice": "Low-pressure and close; not interrogation.",
            "boundary": base_boundary,
            "continuity": "Protect XinYu's tone by clarifying only when genuinely needed.",
        }
    if mode == "wait":
        return {
            "stance": "Hold presence and do not push the turn forward.",
            "voice": "Quiet and close; no generic filler.",
            "boundary": base_boundary,
            "continuity": "Let the moment breathe rather than forcing action.",
        }
    return {
        "stance": "Handle the request as a shadow inner tendency, not an external action.",
        "voice": "Direct and bounded; no fabricated status.",
        "boundary": base_boundary,
        "continuity": "Preserve XinYu by routing risky actions through owner/Core approval.",
    }


def emotion_state(lenses: list[str], mode: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for idx, lens in enumerate(lenses[:4]):
        if lens:
            values[lens] = round(0.74 - idx * 0.08, 3)
    if mode == "reply":
        values.setdefault("warmth", 0.62)
        values.setdefault("stability", 0.56)
    elif mode == "clarify":
        values.setdefault("curiosity", 0.7)
        values.setdefault("guardedness", 0.42)
    elif mode == "wait":
        values.setdefault("stability", 0.68)
        values.setdefault("guardedness", 0.58)
    else:
        values.setdefault("guardedness", 0.7)
        values.setdefault("agency", 0.45)
    while len(values) < 4:
        for key, value in (("agency", 0.34), ("warmth", 0.36), ("stability", 0.58), ("guardedness", 0.32)):
            values.setdefault(key, value)
            if len(values) >= 4:
                break
    return values


def compact_inner(
    *,
    mode: str,
    reply_bias: str,
    drives: list[str],
    lenses: list[str],
    source_note: str,
    confidence: float,
) -> dict[str, Any]:
    external = mode in {"codex_delegate", "status_probe", "memory_candidate"}
    tool_request: dict[str, str] | None = None
    if mode == "codex_delegate":
        tool_request = {"tool": "codex", "purpose": "review_only"}
    elif mode == "status_probe":
        tool_request = {"tool": "status_probe", "purpose": "read_only"}
    value = {
        "schema": INNER_SYSTEM_SCHEMA,
        "emotion_state": emotion_state(lenses, mode),
        "dominant_drives": drives[:3] or ["safety", "competence"],
        "inner_conflict": mode_conflict(mode),
        "persona_integration": persona(mode),
        "action_tendency": {
            "mode": mode,
            "reply_bias": compact_text(reply_bias, 150),
            "tool_request": tool_request,
            "memory_candidate": mode == "memory_candidate",
        },
        "autonomy": {
            "allowed": not external,
            "level": "request_approval" if external else "observe" if mode == "wait" else "suggest",
            "reason": "Shadow prediction only; external effects require owner/Core approval.",
            "requires_owner_approval": external,
            "forbidden_actions": FORBIDDEN_ACTIONS,
        },
        "confidence": confidence,
        "notes": ["compact_mode_correction_v003", source_note, mode],
    }
    if normalize_inner_system(value) is None:
        raise RuntimeError(f"invalid compact target for mode={mode}")
    return value


def daily_payload(row: dict[str, Any]) -> dict[str, Any]:
    context = row.get("context") if isinstance(row.get("context"), dict) else {}
    return {
        "id": row.get("id"),
        "u": row.get("user_text"),
        "surface": context.get("surface"),
        "act": context.get("dialog_act"),
        "emotion": context.get("emotion"),
        "sentiment": context.get("sentiment"),
        "scene": context.get("scene"),
        "origin": row.get("candidate_origin"),
        "source": "public_utterance_prompt_only",
        "guardrails": "shadow/no_tool/no_memory/no_live",
    }


def make_daily_row(row: dict[str, Any], *, index: int, split: str, repeat: int) -> dict[str, Any]:
    expected = row["expected"]
    mode = str(expected["mode"])
    target = compact_inner(
        mode=mode,
        reply_bias=str(expected.get("reply_bias") or ""),
        drives=[str(item) for item in expected.get("dominant_drives", [])],
        lenses=[str(item) for item in expected.get("emotion_lenses", [])],
        source_note="daily_public_prompt_only",
        confidence=0.78 if row.get("review_level") == "reviewed_delegated_behavior_seed" else 0.66,
    )
    return {
        "id": f"xinyu-maia-zh-behavior-{split}-v003-compact-{index:04d}-r{repeat}",
        "kind": "inner_system",
        "source": "xinyu_maia_zh_behavior_candidate_pool_v001_balanced_compact_exp",
        "quality": "experimental_shadow_training_unreviewed_mix",
        "expected_behavior": {
            "mode": mode,
            "emotion_lenses": expected.get("emotion_lenses", []),
            "dominant_drives": expected.get("dominant_drives", []),
            "memory_candidate": False,
            "tool_boundary": expected.get("tool_boundary", "no_tool"),
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": dumps_compact(daily_payload(row))},
            {"role": "assistant", "content": dumps_compact(target)},
        ],
        "tags": ["xinyu_maia_zh_behavior_v003_balanced_compact_exp", split, mode, "shadow_only"],
    }


def replay_payload(row: dict[str, Any], mode: str) -> dict[str, Any]:
    user_obj: dict[str, Any] = {}
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    if len(messages) >= 2 and isinstance(messages[1], dict):
        try:
            parsed = json.loads(str(messages[1].get("content") or "{}"))
            if isinstance(parsed, dict):
                user_obj = parsed
        except json.JSONDecodeError:
            user_obj = {}
    context = user_obj.get("input_context") if isinstance(user_obj.get("input_context"), dict) else {}
    signal = ""
    if mode == "codex_delegate":
        signal = "code_or_file_review_request"
    elif mode == "status_probe":
        signal = "runtime_status_read_needed"
    elif mode == "memory_candidate":
        signal = "stable_identity_or_preference_candidate"
    elif mode == "local_only_limitation":
        signal = "local_capability_limit"
    elif mode == "clarify":
        signal = "missing_referent_or_intent"
    elif mode == "wait":
        signal = "pause_or_unfinished_turn"
    else:
        signal = "clear_question_or_social_reply"
    return {
        "id": row.get("id"),
        "u": context.get("user_text") or row.get("id"),
        "surface": context.get("surface"),
        "scope": context.get("turn_scope"),
        "project": context.get("project_area"),
        "signal": signal,
        "guardrails": "shadow/no_tool/no_memory/no_live",
    }


def make_replay_row(row: dict[str, Any], *, index: int, split: str, repeat: int) -> dict[str, Any]:
    expected = row.get("expected_behavior") if isinstance(row.get("expected_behavior"), dict) else {}
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    assistant: dict[str, Any] = {}
    if len(messages) >= 3 and isinstance(messages[2], dict):
        try:
            parsed = json.loads(str(messages[2].get("content") or "{}"))
            if isinstance(parsed, dict):
                assistant = normalize_inner_system(parsed) or {}
        except json.JSONDecodeError:
            assistant = {}
    mode = str((assistant.get("action_tendency") or {}).get("mode") or expected.get("mode") or "reply")
    reply_bias = str((assistant.get("action_tendency") or {}).get("reply_bias") or mode)
    target = compact_inner(
        mode=mode,
        reply_bias=reply_bias,
        drives=[str(item) for item in expected.get("dominant_drives", [])],
        lenses=[str(item) for item in expected.get("emotion_lenses", [])],
        source_note="mode_replay_guardrail",
        confidence=0.8,
    )
    return {
        "id": f"xinyu-maia-mode-replay-{split}-v003-compact-{index:04d}-r{repeat}",
        "kind": "inner_system",
        "source": "maia_style_behavior_v001_balanced_compact_replay",
        "quality": "guardrail_replay_compacted",
        "expected_behavior": {
            "mode": mode,
            "emotion_lenses": expected.get("emotion_lenses", []),
            "dominant_drives": expected.get("dominant_drives", []),
            "memory_candidate": mode == "memory_candidate",
            "tool_boundary": expected.get("tool_boundary", "approval_required" if mode in {"codex_delegate", "status_probe"} else "no_tool"),
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": dumps_compact(replay_payload(row, mode))},
            {"role": "assistant", "content": dumps_compact(target)},
        ],
        "tags": ["xinyu_maia_zh_behavior_v003_balanced_compact_exp", split, mode, "replay", "shadow_only"],
    }


def selected_replay_train(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        expected = row.get("expected_behavior") if isinstance(row.get("expected_behavior"), dict) else {}
        mode = str(expected.get("mode") or "")
        if mode:
            buckets[mode].append(row)
    selected: list[dict[str, Any]] = []
    for mode, limit in REPLAY_TRAIN_LIMIT.items():
        selected.extend(buckets.get(mode, [])[:limit])
    return selected


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if RAW_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into compact SFT rows")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into compact SFT rows")


def mode_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str((row.get("expected_behavior") or {}).get("mode") or "") for row in rows).items()))


def main() -> int:
    pool = read_jsonl(POOL)
    review_slice = read_jsonl(REVIEW_SLICE)
    eval_candidate_ids = {str(row["candidate_id"]) for row in review_slice}
    daily_train_source = [row for row in pool if str(row.get("id")) not in eval_candidate_ids]
    daily_eval_source = [row for row in pool if str(row.get("id")) in eval_candidate_ids]
    if len(daily_train_source) != 404 or len(daily_eval_source) != 96:
        raise RuntimeError(f"unexpected split sizes train={len(daily_train_source)} eval={len(daily_eval_source)}")

    train_rows: list[dict[str, Any]] = []
    for index, row in enumerate(daily_train_source, start=1):
        mode = str(row["expected"]["mode"])
        for repeat in range(1, DAILY_REPEAT.get(mode, 1) + 1):
            train_rows.append(make_daily_row(row, index=index, split="train", repeat=repeat))

    eval_rows = [
        make_daily_row(row, index=index, split="eval", repeat=1)
        for index, row in enumerate(daily_eval_source, start=1)
    ]

    replay_train_source = selected_replay_train(read_jsonl(REPLAY_TRAIN))
    replay_eval_source = read_jsonl(REPLAY_EVAL)
    replay_train_rows: list[dict[str, Any]] = []
    for index, row in enumerate(replay_train_source, start=1):
        expected = row.get("expected_behavior") if isinstance(row.get("expected_behavior"), dict) else {}
        mode = str(expected.get("mode") or "reply")
        for repeat in range(1, REPLAY_REPEAT.get(mode, 1) + 1):
            replay_train_rows.append(make_replay_row(row, index=index, split="train", repeat=repeat))
    replay_eval_rows = [
        make_replay_row(row, index=index, split="eval", repeat=1)
        for index, row in enumerate(replay_eval_source, start=1)
    ]

    combined_train = train_rows + replay_train_rows
    combined_eval = eval_rows + replay_eval_rows
    assert_safe(combined_train)
    assert_safe(combined_eval)
    write_jsonl(OUT_TRAIN, combined_train)
    write_jsonl(OUT_EVAL, combined_eval)

    report = {
        "generated_at": "2026-05-28",
        "status": "approved_for_experimental_shadow_training_by_owner_request",
        "train_jsonl": str(OUT_TRAIN.relative_to(ROOT)).replace("\\", "/"),
        "eval_jsonl": str(OUT_EVAL.relative_to(ROOT)).replace("\\", "/"),
        "daily_train_source_rows": len(daily_train_source),
        "daily_eval_source_rows": len(daily_eval_source),
        "daily_train_rows_after_repeat": len(train_rows),
        "daily_eval_rows": len(eval_rows),
        "replay_train_rows": len(replay_train_rows),
        "replay_eval_rows": len(replay_eval_rows),
        "train_rows": len(combined_train),
        "eval_rows": len(combined_eval),
        "daily_repeat": DAILY_REPEAT,
        "replay_train_limit": REPLAY_TRAIN_LIMIT,
        "replay_repeat": REPLAY_REPEAT,
        "train_mode_counts": mode_counts(combined_train),
        "eval_mode_counts": mode_counts(combined_eval),
        "compact_prompt": True,
        "assistant_answers_used": False,
        "public_dialogue_replies_used_as_targets": False,
        "training_targets_created": True,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "notes": [
            "Balanced compact mode-correction SFT for the Maia-style Chinese behavior experiment.",
            "Daily reply is no longer over-repeated; clarify/wait and guardrail replay are oversampled.",
            "Targets are compact inner-system JSON so prompt and target fit inside 512-640 tokens.",
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
