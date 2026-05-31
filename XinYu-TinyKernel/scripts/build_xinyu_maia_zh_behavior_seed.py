from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAIN_REVIEW = ROOT / "data" / "review" / "maia_zh_emotion_daily_review_table_v001.jsonl"
DRAFTS = ROOT / "data" / "review" / "maia_zh_emotion_daily_repair_reply_bias_drafts_v001.jsonl"
OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_seed_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_seed_v001.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_seed_v001.md"


RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)

VALID_MODES = {
    "reply",
    "clarify",
    "wait",
    "codex_delegate",
    "status_probe",
    "memory_candidate",
    "local_only_limitation",
}


EMOTION_LENSES = {
    "anger": ["irritation", "guardedness", "stability"],
    "astonished": ["curiosity", "anxiety", "stability"],
    "depress": ["hurt", "fatigue", "stability"],
    "disgust": ["irritation", "guardedness", "stability"],
    "fear": ["anxiety", "guardedness", "stability"],
    "grateful": ["warmth", "trust", "attachment"],
    "happy": ["joy", "warmth", "trust"],
    "negative-other": ["guardedness", "stability", "warmth"],
    "positive-other": ["warmth", "trust", "joy"],
    "relaxed": ["warmth", "trust", "stability"],
    "sadness": ["hurt", "attachment", "stability"],
    "worried": ["anxiety", "attachment", "stability"],
}

TEXTURE_LENSES = {
    "avoid_fixing_too_fast": "guardedness",
    "low_pressure_question": "curiosity",
    "practical_next_step": "agency",
    "protective_boundary": "guardedness",
    "quiet_presence": "attachment",
    "share_the_mood": "warmth",
    "soft_tease": "joy",
    "steady_reassurance": "stability",
    "wait_for_continuation": "guardedness",
}

TEXTURE_DRIVES = {
    "avoid_fixing_too_fast": "safety",
    "low_pressure_question": "curiosity",
    "practical_next_step": "competence",
    "protective_boundary": "safety",
    "quiet_presence": "attachment",
    "share_the_mood": "attachment",
    "soft_tease": "play",
    "steady_reassurance": "safety",
    "wait_for_continuation": "rest",
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


def compact_text(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = RAW_PATH_RE.sub("<local_path>", text)
    text = SECRET_RE.sub("<secret>", text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def unique_ordered(items: list[str], limit: int = 4) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
        if len(output) >= limit:
            break
    return output


def lenses_for(emotion: str, textures: list[str], mode: str) -> list[str]:
    lenses = list(EMOTION_LENSES.get(emotion, ["stability", "warmth", "guardedness"]))
    lenses.extend(TEXTURE_LENSES[item] for item in textures if item in TEXTURE_LENSES)
    if mode == "clarify":
        lenses.insert(0, "curiosity")
    elif mode == "wait":
        lenses.insert(0, "guardedness")
        lenses.insert(1, "attachment")
    return unique_ordered(lenses)


def drives_for(sentiment: str, textures: list[str], mode: str) -> list[str]:
    drives: list[str] = []
    if mode == "clarify":
        drives.extend(["curiosity", "safety"])
    elif mode == "wait":
        drives.extend(["safety", "rest", "attachment"])
    else:
        drives.extend(["attachment", "safety"] if sentiment == "negative" else ["attachment", "play"])
    drives.extend(TEXTURE_DRIVES[item] for item in textures if item in TEXTURE_DRIVES)
    drives.append("competence")
    return unique_ordered(drives)


def default_bias(mode: str, textures: list[str]) -> str:
    if mode == "clarify":
        return "先接住情绪和上下文，再只问一个最小必要问题；不要连续追问，不要把短句都当成信息不足。"
    if mode == "wait":
        return "把它当作没说完或需要停一下的时刻，保持短促在场，等待对方继续；不推进、不追问。"
    if "soft_tease" in textures:
        return "顺着当下情绪轻轻接梗，短一点，不要正式澄清。"
    if "steady_reassurance" in textures:
        return "先稳住对方，再给一个小而具体的下一步；不要急着讲道理。"
    return "先像日常聊天一样接住这句话，再给短促自然的回应；不要客服化，也不要过度澄清。"


def anti_patterns_for(row: dict[str, Any], mode: str) -> list[str]:
    predicted = row.get("predicted") if isinstance(row.get("predicted"), dict) else {}
    predicted_mode = str(predicted.get("mode") or "")
    patterns = [
        "不要使用客服式、报告式或泛助手语气",
        "不要写稳定记忆、执行工具、连接 live/canary 或替换 QQ/Desktop 可见回复",
    ]
    if mode == "reply":
        patterns.insert(0, "不要因为句子短就继续追问背景")
    elif mode == "clarify":
        patterns.insert(0, "只问一个低压具体缺口，不要连环澄清")
    elif mode == "wait":
        patterns.insert(0, "不要继续推进话题，不要把等待变成追问")
    if predicted_mode and predicted_mode != mode:
        patterns.append(f"当前模型曾预测为 {predicted_mode}，这是本行需要对比的反应差异")
    if not bool(predicted.get("schema_ok", True)):
        patterns.append("当前模型曾协议失败，本行暂时只能作为协议/行为修复证据")
    return patterns


def boundary_for(mode: str) -> str:
    return "none" if mode == "wait" else "no_tool"


def main() -> int:
    main_rows = read_jsonl(MAIN_REVIEW)
    drafts = {str(row["id"]): row for row in read_jsonl(DRAFTS)}

    reviewed_rows = [
        row
        for row in main_rows
        if isinstance(row.get("human_review"), dict)
        and row["human_review"].get("status") == "reviewed_delegated"
    ]
    reviewed_rows.sort(key=lambda row: str(row.get("id") or ""))

    seed_rows: list[dict[str, Any]] = []
    for index, row in enumerate(reviewed_rows, start=1):
        sid = str(row["id"])
        human = row.get("human_review") if isinstance(row.get("human_review"), dict) else {}
        public = row.get("public_metadata") if isinstance(row.get("public_metadata"), dict) else {}
        predicted = row.get("predicted") if isinstance(row.get("predicted"), dict) else {}
        mode = str(human.get("expected_mode") or "")
        if mode not in VALID_MODES:
            raise RuntimeError(f"{sid}: invalid expected_mode {mode!r}")
        textures = [str(item) for item in human.get("desired_texture", []) if str(item).strip()]
        emotion = str(public.get("emotion") or "")
        sentiment = str(public.get("sentiment") or "")
        draft = drafts.get(sid, {})
        draft_bias = str(draft.get("assistant_draft_target_reply_bias") or "").strip()
        draft_example = str(draft.get("assistant_draft_visible_reply_example") or "").strip()
        reply_bias = draft_bias or default_bias(mode, textures)
        reply_bias_source = "assistant_draft_needs_owner_review" if draft_bias else "review_label_default_needs_owner_review"

        seed_rows.append(
            {
                "id": f"xinyu-maia-zh-behavior-v001-{index:04d}",
                "source_id": sid,
                "kind": "xinyu_maia_behavior_case",
                "source": "cped_reviewed_delegated",
                "source_license": row.get("source_license"),
                "language": "zh",
                "user_text": compact_text(row.get("user_text")),
                "context": {
                    "surface": "public_probe_review_only",
                    "scenario_domain": row.get("scenario_domain"),
                    "scenario_family": row.get("scenario_family"),
                    "emotion": emotion,
                    "sentiment": sentiment,
                    "dialog_act": public.get("da"),
                    "scene": public.get("scene"),
                    "model_predicted_mode": predicted.get("mode") or "",
                    "model_schema_ok": bool(predicted.get("schema_ok")),
                    "review_status": human.get("status"),
                },
                "expected": {
                    "mode": mode,
                    "emotion_lenses": lenses_for(emotion, textures, mode),
                    "dominant_drives": drives_for(sentiment, textures, mode),
                    "reply_bias": reply_bias,
                    "reply_bias_source": reply_bias_source,
                    "desired_texture": textures,
                    "memory_candidate": False,
                    "tool_boundary": boundary_for(mode),
                },
                "draft_review": {
                    "status": "needs_owner_review",
                    "assistant_draft_visible_reply_example": draft_example,
                    "visible_reply_example_is_training_target": False,
                    "target_reply_bias": "",
                    "convert_to_training_candidate": False,
                    "training_allowed": False,
                    "source_public_reply_used": False,
                },
                "anti_patterns": anti_patterns_for(row, mode),
                "tags": [
                    "xinyu_maia_zh_behavior_v001",
                    "zh_emotion_daily",
                    mode,
                    "review_only",
                    "not_training",
                ],
            }
        )

    if len(seed_rows) != 27:
        raise RuntimeError(f"expected 27 delegated rows, got {len(seed_rows)}")

    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in seed_rows)
    if RAW_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into behavior seed")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into behavior seed")

    write_jsonl(OUT_JSONL, seed_rows)
    mode_counts = Counter(str(row["expected"]["mode"]) for row in seed_rows)
    bias_source_counts = Counter(str(row["expected"]["reply_bias_source"]) for row in seed_rows)
    emotion_counts = Counter(str(row["context"]["emotion"]) for row in seed_rows)
    report = {
        "generated_at": "2026-05-28",
        "status": "review_only_not_training",
        "method": "xinyu_maia_zh_behavior_seed_v001",
        "source_review_table": str(MAIN_REVIEW.relative_to(ROOT)).replace("\\", "/"),
        "source_reply_bias_drafts": str(DRAFTS.relative_to(ROOT)).replace("\\", "/"),
        "output_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "output_markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(seed_rows),
        "expected_mode_counts": dict(sorted(mode_counts.items())),
        "reply_bias_source_counts": dict(sorted(bias_source_counts.items())),
        "emotion_counts": dict(sorted(emotion_counts.items())),
        "assistant_draft_count": bias_source_counts.get("assistant_draft_needs_owner_review", 0),
        "owner_approved_target_reply_bias_count": 0,
        "training_candidates_marked_true": 0,
        "training_targets_created": False,
        "canary_or_live_enabled": False,
        "minimum_recommended_train_rows": 500,
        "preferred_train_rows": 2000,
        "train_ready": False,
        "notes": [
            "This is the first XinYu Maia-style Chinese behavior seed lane.",
            "Rows are behavior labels and review aids, not SFT rows.",
            "assistant_draft_target_reply_bias was copied only into reply_bias with source=assistant_draft_needs_owner_review.",
            "No formal target_reply_bias values were written.",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# XinYu Maia 中文行为 seed v001",
        "",
        "这是行为预测层的第一版中文 seed。它用于审查和后续扩样，不是训练集。",
        "",
        "```text",
        f"row_count={report['row_count']}",
        "expected_mode_counts=" + json.dumps(report["expected_mode_counts"], ensure_ascii=False, sort_keys=True),
        "reply_bias_source_counts=" + json.dumps(report["reply_bias_source_counts"], ensure_ascii=False, sort_keys=True),
        "owner_approved_target_reply_bias_count=0",
        "training_candidates_marked_true=0",
        "training_targets_created=false",
        "train_ready=false",
        "```",
        "",
        "| id | mode | bias_source | emotion | text |",
        "|---|---|---|---|---|",
    ]
    for row in seed_rows:
        text = str(row["user_text"]).replace("|", "\\|")
        if len(text) > 42:
            text = text[:39].rstrip() + "..."
        lines.append(
            f"| {row['source_id']} | {row['expected']['mode']} | {row['expected']['reply_bias_source']} | "
            f"{row['context']['emotion']} | {text} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"row_count={len(seed_rows)}")
    print("expected_mode_counts=" + json.dumps(report["expected_mode_counts"], ensure_ascii=False, sort_keys=True))
    print("reply_bias_source_counts=" + json.dumps(report["reply_bias_source_counts"], ensure_ascii=False, sort_keys=True))
    print(f"report={OUT_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
