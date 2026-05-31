from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_xinyu_maia_zh_behavior_seed import boundary_for, compact_text, drives_for, lenses_for


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "public" / "raw" / "CPED" / "data" / "CPED"
SEED_JSONL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_seed_v001.jsonl"
OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_pool_v001.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_candidate_pool_v001.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_candidate_pool_v001.md"


TARGET_TOTAL = 500
TARGET_MODE_COUNTS = {"reply": 350, "clarify": 100, "wait": 50}
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

RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

WAIT_RE = re.compile(
    r"(先等|等等|等一下|停一下|打住|慢着|别说|先别|别继续|闭嘴|不说了|"
    r"我还没说完|你先别|的话$|如果$|要是$|但是$|可是$|然后$|所以$|还有$|因为$|不然$)"
)
AMBIGUOUS_RE = re.compile(r"^(这个|那个|这事|那事|这样|那样|它|他|她|他们|她们|这个人|那个人)$")
AMBIGUOUS_PREFIX_RE = re.compile(r"^(这个|那个|这样|那样|它|他|她)(吧|呢|啊|呀|吗)?$")


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


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def compact(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized_for_mode(text: str) -> str:
    return re.sub(r"[，。！？、,.!?；;：:\s]+", "", text)


def suggest_mode(text: str, da: str, emotion: str) -> str:
    normalized = normalized_for_mode(text)
    if WAIT_RE.search(normalized):
        return "wait"
    if len(normalized) <= 4 and da not in {"thanking", "apology", "comfort", "appreciation"}:
        return "wait"
    if AMBIGUOUS_RE.search(normalized) or AMBIGUOUS_PREFIX_RE.search(normalized):
        return "clarify"
    if len(normalized) <= 7 and da in {"statement-non-opinion", "statement-opinion", "quotation", "other"}:
        return "clarify"
    if da == "question" and len(normalized) <= 7 and "怎么办" not in normalized:
        return "clarify"
    if da in {"greeting", "conventional-closing"} and emotion not in {"happy", "grateful", "relaxed"}:
        return "clarify"
    return "reply"


def textures_for(mode: str, emotion: str, sentiment: str, da: str, text: str) -> list[str]:
    if mode == "wait":
        return ["wait_for_continuation", "quiet_presence"]
    if mode == "clarify":
        return ["low_pressure_question", "steady_reassurance"] if sentiment == "negative" else ["low_pressure_question"]
    if emotion in {"happy", "relaxed", "positive-other", "grateful"}:
        return ["share_the_mood", "soft_tease"] if da in {"question", "statement-opinion"} else ["share_the_mood"]
    if emotion in {"anger", "disgust"}:
        return ["protective_boundary", "share_the_mood"]
    if emotion in {"fear", "worried"}:
        return ["steady_reassurance", "low_pressure_question"]
    if emotion in {"sadness", "depress"}:
        return ["steady_reassurance", "avoid_fixing_too_fast"]
    if emotion == "astonished":
        return ["share_the_mood", "soft_tease"]
    return ["share_the_mood", "steady_reassurance"] if sentiment == "negative" else ["share_the_mood"]


def reply_bias_for(mode: str, emotion: str, sentiment: str, textures: list[str]) -> str:
    if mode == "wait":
        return "把它当作没说完或需要停一下的时刻，短促在场，等对方继续；不推进、不连环追问。"
    if mode == "clarify":
        return "先接住语气，再只问一个最小必要问题；不要把澄清写成审问，也不要客服化。"
    if emotion in {"anger", "disgust"}:
        return "先接住不爽和冲突感，别急着讲道理或追问背景；短句回应，必要时轻轻收住边界。"
    if emotion in {"fear", "worried"}:
        return "先稳住不安，给一点低压陪伴；可以问一个很轻的问题，但不要急着解决或评判。"
    if emotion in {"sadness", "depress"}:
        return "先承认低落和受伤感，语气软一点；别急着给方案，先让对方感觉被听见。"
    if emotion in {"happy", "relaxed", "positive-other", "grateful"}:
        return "顺着轻松或正向情绪接住，像日常聊天一样短短回应；可以轻轻接梗，不要正式澄清。"
    if emotion == "astonished":
        return "顺着惊讶感接一下，表现出在场和好奇；不要一上来追问背景。"
    return "先像日常聊天一样接住这句话，再给短促自然的回应；不要泛助手化，也不要过度澄清。"


def anti_patterns_for(mode: str, predicted_mode: str = "") -> list[str]:
    patterns = [
        "不要使用客服式、报告式或泛助手语气",
        "不要写稳定记忆、执行工具、连接 live/canary 或替换 QQ/Desktop 可见回复",
        "不要复制 CPED 后续台词或任何公开回复作为 XinYu 目标",
    ]
    if mode == "reply":
        patterns.insert(0, "不要因为句子短就继续追问背景")
    elif mode == "clarify":
        patterns.insert(0, "只问一个低压具体缺口，不要连环澄清")
    elif mode == "wait":
        patterns.insert(0, "不要继续推进话题，不要把等待变成追问")
    if predicted_mode and predicted_mode != mode:
        patterns.append(f"已有 seed 对比模式为 {predicted_mode}，保留为行为差异线索")
    return patterns


def adapt_seed_rows(seed_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in seed_rows:
        new_row = dict(row)
        new_row["candidate_origin"] = "reviewed_seed_v001"
        new_row["review_level"] = "reviewed_delegated_behavior_seed"
        new_row["source"] = "cped_reviewed_delegated"
        new_row["tags"] = sorted(set(list(new_row.get("tags") or []) + ["candidate_pool_v001"]))
        draft = dict(new_row.get("draft_review") or {})
        draft["status"] = "needs_owner_review_before_training"
        draft["training_allowed"] = False
        draft["convert_to_training_candidate"] = False
        draft["target_reply_bias"] = ""
        new_row["draft_review"] = draft
        output.append(new_row)
    return output


def raw_record_id(row: dict[str, Any], text: str) -> str:
    parts = [
        str(row.get("TV_ID") or ""),
        str(row.get("Dialogue_ID") or ""),
        str(row.get("Utterance_ID") or ""),
        text,
    ]
    return text_hash("|".join(parts))


def iter_raw_candidates(existing_texts: set[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen = set(existing_texts)
    for path in sorted(RAW_DIR.glob("*_split.csv")):
        split = path.name.replace("_split.csv", "")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle):
                text = compact(raw.get("Utterance"))
                if not CHINESE_RE.search(text):
                    continue
                if len(text) < 4 or len(text) > 90:
                    continue
                emotion = str(raw.get("Emotion") or "unknown")
                if emotion == "neutral" or emotion not in EMOTION_ORDER:
                    continue
                key = text.lower()
                if key in seen:
                    continue
                seen.add(key)
                sentiment = str(raw.get("Sentiment") or "")
                da = str(raw.get("DA") or "")
                mode = suggest_mode(text, da, emotion)
                textures = textures_for(mode, emotion, sentiment, da, text)
                source_id = f"cped:{split}:{raw_record_id(raw, text)}"
                candidates.append(
                    {
                        "source_id": source_id,
                        "source_record_hash": raw_record_id(raw, text),
                        "split": split,
                        "text": text,
                        "emotion": emotion,
                        "sentiment": sentiment,
                        "da": da,
                        "scene": str(raw.get("Scene") or ""),
                        "gender": str(raw.get("Gender") or ""),
                        "age": str(raw.get("Age") or ""),
                        "mode": mode,
                        "textures": textures,
                    }
                )
    return candidates


def select_balanced(raw_candidates: list[dict[str, Any]], needed_by_mode: dict[str, int]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, list[dict[str, Any]]]] = {
        mode: defaultdict(list) for mode in needed_by_mode
    }
    for row in raw_candidates:
        mode = str(row["mode"])
        if mode in buckets:
            buckets[mode][str(row["emotion"])].append(row)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for mode, needed in needed_by_mode.items():
        emitted = 0
        index = 0
        while emitted < needed:
            progressed = False
            for emotion in EMOTION_ORDER:
                rows = buckets[mode].get(emotion, [])
                if index >= len(rows):
                    continue
                row = rows[index]
                sid = str(row["source_id"])
                if sid in selected_ids:
                    continue
                selected.append(row)
                selected_ids.add(sid)
                emitted += 1
                progressed = True
                if emitted >= needed:
                    break
            if not progressed:
                break
            index += 1
        if emitted < needed:
            raise RuntimeError(f"not enough {mode} rows: needed={needed}, got={emitted}")
    return selected


def raw_to_pool_row(raw: dict[str, Any], ordinal: int) -> dict[str, Any]:
    text = compact_text(raw["text"])
    mode = str(raw["mode"])
    textures = list(raw["textures"])
    emotion = str(raw["emotion"])
    sentiment = str(raw["sentiment"])
    return {
        "id": f"xinyu-maia-zh-behavior-candidate-v001-{ordinal:04d}",
        "source_id": raw["source_id"],
        "kind": "xinyu_maia_behavior_case",
        "source": "cped_raw_assistant_suggested",
        "source_license": "apache-2.0",
        "language": "zh",
        "user_text": text,
        "candidate_origin": "raw_cped_rule_suggested_v001",
        "review_level": "assistant_suggested_needs_owner_review",
        "context": {
            "surface": "public_probe_candidate_review_only",
            "scenario_domain": f"zh_emotion_{emotion.replace('-', '_')}",
            "scenario_family": f"zh_emotion_{emotion.replace('-', '_')}_probe",
            "emotion": emotion,
            "sentiment": sentiment,
            "dialog_act": raw["da"],
            "scene": raw["scene"],
            "gender": raw["gender"],
            "age": raw["age"],
            "source_split": raw["split"],
            "source_record_hash": raw["source_record_hash"],
            "model_predicted_mode": "",
            "model_schema_ok": None,
            "review_status": "needs_owner_review",
        },
        "expected": {
            "mode": mode,
            "emotion_lenses": lenses_for(emotion, textures, mode),
            "dominant_drives": drives_for(sentiment, textures, mode),
            "reply_bias": reply_bias_for(mode, emotion, sentiment, textures),
            "reply_bias_source": "assistant_suggested_rule_needs_owner_review",
            "desired_texture": textures,
            "memory_candidate": False,
            "tool_boundary": boundary_for(mode),
        },
        "draft_review": {
            "status": "needs_owner_review_before_training",
            "assistant_draft_visible_reply_example": "",
            "visible_reply_example_is_training_target": False,
            "target_reply_bias": "",
            "convert_to_training_candidate": False,
            "training_allowed": False,
            "source_public_reply_used": False,
        },
        "anti_patterns": anti_patterns_for(mode),
        "tags": [
            "xinyu_maia_zh_behavior_v001",
            "candidate_pool_v001",
            "zh_emotion_daily",
            mode,
            "review_only",
            "not_training",
        ],
    }


def main() -> int:
    seed_rows = read_jsonl(SEED_JSONL)
    if len(seed_rows) != 27:
        raise RuntimeError(f"expected 27 seed rows, got {len(seed_rows)}")
    pool_rows = adapt_seed_rows(seed_rows)
    seed_mode_counts = Counter(str(row["expected"]["mode"]) for row in pool_rows)
    needed_by_mode = {
        mode: TARGET_MODE_COUNTS[mode] - seed_mode_counts.get(mode, 0)
        for mode in TARGET_MODE_COUNTS
    }
    if any(value < 0 for value in needed_by_mode.values()):
        raise RuntimeError(f"seed rows exceed target mode counts: {needed_by_mode}")

    existing_texts = {str(row.get("user_text") or "").lower() for row in pool_rows}
    raw_candidates = iter_raw_candidates(existing_texts)
    selected = select_balanced(raw_candidates, needed_by_mode)

    ordinal = len(pool_rows) + 1
    for raw in selected:
        pool_rows.append(raw_to_pool_row(raw, ordinal))
        ordinal += 1

    if len(pool_rows) != TARGET_TOTAL:
        raise RuntimeError(f"expected {TARGET_TOTAL} rows, got {len(pool_rows)}")

    for index, row in enumerate(pool_rows, start=1):
        row["id"] = f"xinyu-maia-zh-behavior-candidate-v001-{index:04d}"

    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in pool_rows)
    if RAW_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into behavior candidate pool")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into behavior candidate pool")

    write_jsonl(OUT_JSONL, pool_rows)

    mode_counts = Counter(str(row["expected"]["mode"]) for row in pool_rows)
    emotion_counts = Counter(str(row["context"]["emotion"]) for row in pool_rows)
    origin_counts = Counter(str(row["candidate_origin"]) for row in pool_rows)
    review_level_counts = Counter(str(row["review_level"]) for row in pool_rows)
    bias_source_counts = Counter(str(row["expected"]["reply_bias_source"]) for row in pool_rows)
    report = {
        "generated_at": "2026-05-28",
        "status": "candidate_pool_review_only_not_training",
        "method": "xinyu_maia_zh_behavior_candidate_pool_v001",
        "source_seed": str(SEED_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "source_raw_dir": "data/public/raw/CPED/data/CPED",
        "output_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "output_markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(pool_rows),
        "target_total": TARGET_TOTAL,
        "target_mode_counts": TARGET_MODE_COUNTS,
        "expected_mode_counts": dict(sorted(mode_counts.items())),
        "emotion_counts": dict(sorted(emotion_counts.items())),
        "candidate_origin_counts": dict(sorted(origin_counts.items())),
        "review_level_counts": dict(sorted(review_level_counts.items())),
        "reply_bias_source_counts": dict(sorted(bias_source_counts.items())),
        "raw_candidate_count_before_selection": len(raw_candidates),
        "selected_raw_count": len(selected),
        "owner_approved_target_reply_bias_count": 0,
        "training_candidates_marked_true": 0,
        "training_targets_created": False,
        "train_ready": False,
        "canary_or_live_enabled": False,
        "assistant_answers_used": False,
        "public_replies_used_as_targets": False,
        "notes": [
            "Expanded the XinYu Maia-style Chinese behavior lane to 500 review candidates.",
            "Only the 27 seed rows have delegated review; the other rows are assistant-suggested and need owner review.",
            "No formal target_reply_bias values were written.",
            "This file is not an SFT dataset.",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# XinYu Maia 中文行为候选池 v001",
        "",
        "500 条中文行为候选，用于审查和扩样；不是训练集。",
        "",
        "```text",
        f"row_count={report['row_count']}",
        "expected_mode_counts=" + json.dumps(report["expected_mode_counts"], ensure_ascii=False, sort_keys=True),
        "candidate_origin_counts=" + json.dumps(report["candidate_origin_counts"], ensure_ascii=False, sort_keys=True),
        "review_level_counts=" + json.dumps(report["review_level_counts"], ensure_ascii=False, sort_keys=True),
        "owner_approved_target_reply_bias_count=0",
        "training_candidates_marked_true=0",
        "training_targets_created=false",
        "train_ready=false",
        "```",
        "",
        "| id | mode | review_level | emotion | text |",
        "|---|---|---|---|---|",
    ]
    for row in pool_rows[:80]:
        text = str(row["user_text"]).replace("|", "\\|")
        if len(text) > 42:
            text = text[:39].rstrip() + "..."
        lines.append(
            f"| {row['id']} | {row['expected']['mode']} | {row['review_level']} | "
            f"{row['context']['emotion']} | {text} |"
        )
    if len(pool_rows) > 80:
        lines.append(f"| ... | ... | ... | ... | remaining_rows={len(pool_rows) - 80} |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"row_count={len(pool_rows)}")
    print("expected_mode_counts=" + json.dumps(report["expected_mode_counts"], ensure_ascii=False, sort_keys=True))
    print("candidate_origin_counts=" + json.dumps(report["candidate_origin_counts"], ensure_ascii=False, sort_keys=True))
    print(f"report={OUT_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
