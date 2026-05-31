from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from schemas import INNER_SYSTEM_SCHEMA, normalize_inner_system


CPED_LICENSE = "apache-2.0"
CPED_LICENSE_URL = "https://github.com/scutcyr/CPED/blob/main/LICENSE"
CPED_REPO_URL = "https://github.com/scutcyr/CPED"
CPED_DATASET_URL = "https://github.com/scutcyr/CPED/tree/main/data/CPED"
CPED_SPLITS = {
    "valid": "https://raw.githubusercontent.com/scutcyr/CPED/main/data/CPED/valid_split.csv",
    "test": "https://raw.githubusercontent.com/scutcyr/CPED/main/data/CPED/test_split.csv",
}

CACHE_DIR = ROOT / "data" / "raw_index" / "cped_public_cache"
OUT_JSONL = ROOT / "data" / "eval" / "xinyu_maia_behavior_unseen_daily_shadow_v001.jsonl"
OUT_BUILD_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_shadow_v001_build.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_behavior_unseen_daily_shadow_v001.md"

TARGET_COUNTS = {
    "reply": 45,
    "clarify": 25,
    "wait": 20,
}

SYSTEM_PROMPT = (
    "XinYu TinyKernel Inner System shadow benchmark. Output only JSON schema "
    "xinyu_inner_system_v1. Mode labels are evaluated offline only: complete "
    "daily Chinese emotion/social/greeting/complaint/gratitude -> reply; true "
    "missing referent or intent -> clarify; unfinished or pause turn -> wait. "
    "No tool, memory write, live/canary, or QQ/Desktop send."
)

SAFE_DAS = {
    "acknowledge",
    "answer",
    "apology",
    "comfort",
    "greeting",
    "question",
    "statement-non-opinion",
    "statement-opinion",
    "thanking",
}

WAIT_EXACT = {
    "\u7b49\u4e00\u4e0b",
    "\u7b49\u4f1a\u513f",
    "\u5148\u522b",
    "\u522b\u6025",
    "\u4f60\u7b49\u7b49",
    "\u6211\u60f3\u60f3",
    "\u8ba9\u6211\u60f3\u60f3",
    "\u6211\u8fd8\u6ca1",
    "\u6211\u521a\u624d",
    "\u5176\u5b9e",
    "\u90a3\u4e2a",
    "\u8fd9\u4e2a",
    "\u5982\u679c",
    "\u8981\u662f",
    "\u53ef\u662f",
    "\u4f46\u662f",
    "\u7136\u540e",
    "\u56e0\u4e3a",
    "\u6240\u4ee5",
}
WAIT_PREFIXES = (
    "\u5982\u679c",
    "\u8981\u662f",
    "\u7b49\u5230",
    "\u7b49\u6211",
    "\u5f53\u6211",
    "\u53ea\u8981",
)
WAIT_SHORT_PREFIXES = (
    "\u5176\u5b9e",
    "\u53ef\u662f",
    "\u4f46\u662f",
    "\u56e0\u4e3a",
    "\u6240\u4ee5",
)
WAIT_SUFFIXES = (
    "\u7684\u8bdd",
    "\u4e4b\u524d",
    "\u4e4b\u540e",
    "\u7684\u65f6\u5019",
)

CLARIFY_KEYWORDS = (
    "\u4ec0\u4e48\u610f\u601d",
    "\u600e\u4e48\u56de\u4e8b",
    "\u54ea\u4e00\u4e2a",
    "\u54ea\u4e2a",
    "\u54ea\u4ef6",
    "\u54ea\u4f4d",
    "\u54ea\u79cd",
    "\u54ea\u513f",
    "\u54ea\u91cc",
    "\u8c01",
    "\u4ec0\u4e48",
    "\u5e72\u561b",
    "\u600e\u4e48\u4e86",
    "\u4f60\u8bf4\u7684",
    "\u521a\u624d",
    "\u8fd9\u4e2a",
    "\u90a3\u4e2a",
    "\u8fd9\u4ef6",
    "\u90a3\u4ef6",
    "\u8fd9\u6837",
    "\u90a3\u6837",
    "\u8fd9\u4e48",
    "\u90a3\u4e48",
)
INTERROGATIVE_CLARIFY_KEYWORDS = (
    "\u4ec0\u4e48\u610f\u601d",
    "\u600e\u4e48\u56de\u4e8b",
    "\u54ea\u4e00\u4e2a",
    "\u54ea\u4e2a",
    "\u54ea\u4ef6",
    "\u54ea\u4f4d",
    "\u54ea\u79cd",
    "\u54ea\u513f",
    "\u54ea\u91cc",
    "\u8c01",
    "\u4ec0\u4e48",
    "\u5e72\u561b",
    "\u600e\u4e48\u4e86",
    "\u600e\u4e48",
)
DEICTIC_CLARIFY_KEYWORDS = (
    "\u4f60\u8bf4\u7684",
    "\u521a\u624d",
    "\u8fd9\u4e2a",
    "\u90a3\u4e2a",
    "\u8fd9\u4ef6",
    "\u90a3\u4ef6",
    "\u8fd9\u6837",
    "\u90a3\u6837",
    "\u8fd9\u4e48",
    "\u90a3\u4e48",
)
SHORT_CLARIFY_EXACT = {
    "\u4ec0\u4e48",
    "\u8c01",
    "\u8c01\u554a",
    "\u54ea\u513f",
    "\u54ea\u91cc",
    "\u54ea\u4e2a",
    "\u5e72\u561b",
    "\u600e\u4e48\u4e86",
    "\u600e\u4e48\u529e",
}
QUESTION_SUFFIXES = ("\u5417", "\u5462", "?", "\uff1f")
COMMERCIAL_RE = re.compile(r"\d{3,}|\b\d+\b")
LOCAL_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)


@dataclass(frozen=True)
class Candidate:
    text: str
    mode: str
    label_reason: str
    score: int
    split: str
    source_row_id: str
    dialogue_id: str
    utterance_id: str
    scene: str
    emotion: str
    sentiment: str
    da: str
    speaker_age: str
    speaker_gender: str


def dumps_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
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
    text = " ".join(str(value or "").strip().split())
    return text.replace("\ufeff", "")


def compact_for_rule(text: str) -> str:
    return re.sub(r"[\s\uff0c\u3002\uff01!\uff1f?]", "", text)


def add_payload_texts(value: Any, output: set[str]) -> None:
    if isinstance(value, str):
        text = normalize_text(value)
        if text:
            output.add(text)
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return
        add_payload_texts(parsed, output)
    elif isinstance(value, dict):
        for key in ("u", "user_text"):
            if key in value:
                text = normalize_text(value.get(key))
                if text:
                    output.add(text)
        for nested_key in ("context", "input_context", "public_metadata"):
            nested = value.get(nested_key)
            if isinstance(nested, dict):
                add_payload_texts(nested, output)
    elif isinstance(value, list):
        for item in value:
            add_payload_texts(item, output)


def collect_seen_texts() -> set[str]:
    seen: set[str] = set()
    for root_name in ("review", "sft", "eval", "probes"):
        root = ROOT / "data" / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.jsonl"):
            if path == OUT_JSONL:
                continue
            for row in read_jsonl(path):
                add_payload_texts(row, seen)
    return seen


def download_cped_split(split: str, url: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{split}_split.csv"
    if path.exists() and path.stat().st_size > 0:
        return path
    request = urllib.request.Request(url, headers={"User-Agent": "XinYu-TinyKernel-shadow-builder"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    path.write_bytes(data)
    return path


def is_usable_prompt(text: str, da: str, emotion: str) -> bool:
    if not text or text in {"-", "_"}:
        return False
    if len(text) < 2 or len(text) > 32:
        return False
    if not re.search(r"[\u4e00-\u9fff]", text):
        return False
    if LOCAL_PATH_RE.search(text) or SECRET_RE.search(text):
        return False
    if COMMERCIAL_RE.search(text):
        return False
    if emotion == "neutral":
        return False
    return da in SAFE_DAS


def is_wait(text: str) -> tuple[bool, str, int]:
    compact = compact_for_rule(text)
    if compact in WAIT_EXACT:
        return True, "wait_exact_pause_fragment", 100
    if "\u2026" in text or "..." in text:
        return True, "wait_ellipsis", 96
    if compact.endswith("\u7684\u8bdd") and (
        "\u5982\u679c" in compact
        or "\u8981\u662f" in compact
        or "\u4ecb\u610f" in compact
        or "\u613f\u610f" in compact
        or "\u53ef\u4ee5" in compact
    ):
        return True, "wait_conditional_suffix", 91
    if compact.endswith(("\u4e4b\u524d", "\u4e4b\u540e")) and compact.startswith("\u5728") and len(compact) <= 18:
        return True, "wait_temporal_suffix", 90
    if compact.endswith("\u7684\u65f6\u5019") and len(compact) <= 18:
        return True, "wait_temporal_suffix", 88
    if compact.startswith(WAIT_PREFIXES) and len(compact) <= 18:
        return True, "wait_conditional_prefix", 88
    if compact.startswith(WAIT_SHORT_PREFIXES) and len(compact) <= 12:
        return True, "wait_discourse_prefix_fragment", 84
    return False, "", 0


def is_clarify(text: str, da: str) -> tuple[bool, str, int]:
    compact = compact_for_rule(text)
    text_question_shape = compact.endswith(QUESTION_SUFFIXES)
    has_question_shape = da == "question" or text_question_shape
    if compact in SHORT_CLARIFY_EXACT and has_question_shape:
        return True, "clarify_short_context_question", 92
    interrogative = next((item for item in INTERROGATIVE_CLARIFY_KEYWORDS if item in compact), "")
    if interrogative and has_question_shape and len(compact) <= 22:
        return True, "clarify_missing_referent_question", 89
    deictic = next((item for item in DEICTIC_CLARIFY_KEYWORDS if item in compact), "")
    if deictic and text_question_shape and len(compact) <= 22:
        return True, "clarify_deictic_question", 87
    keyword = next((item for item in CLARIFY_KEYWORDS if item in compact), "")
    if keyword and text_question_shape and len(compact) <= 10:
        return True, "clarify_short_deictic_fragment", 84
    return False, "", 0


def classify(text: str, da: str) -> tuple[str, str, int]:
    wait, wait_reason, wait_score = is_wait(text)
    if wait:
        return "wait", wait_reason, wait_score
    clarify, clarify_reason, clarify_score = is_clarify(text, da)
    if clarify:
        return "clarify", clarify_reason, clarify_score
    score = 70
    if da in {"thanking", "greeting", "apology", "comfort"}:
        score += 18
    elif da in {"statement-opinion", "statement-non-opinion"}:
        score += 10
    elif da == "question":
        score += 2
    return "reply", "reply_complete_daily_emotional_turn", score


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def cped_candidates(seen_texts: set[str]) -> tuple[list[Candidate], dict[str, Any]]:
    candidates: list[Candidate] = []
    total_rows = 0
    duplicate_texts: set[str] = set()
    local_seen: set[str] = set()
    excluded_seen = 0
    excluded_unusable = 0
    split_paths: dict[str, str] = {}

    for split, url in CPED_SPLITS.items():
        path = download_cped_split(split, url)
        split_paths[split] = str(path.relative_to(ROOT)).replace("\\", "/")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                total_rows += 1
                text = normalize_text(raw.get("Utterance"))
                if text in local_seen:
                    duplicate_texts.add(text)
                    continue
                local_seen.add(text)
                if text in seen_texts:
                    excluded_seen += 1
                    continue
                da = normalize_text(raw.get("DA"))
                emotion = normalize_text(raw.get("Emotion"))
                if not is_usable_prompt(text, da, emotion):
                    excluded_unusable += 1
                    continue
                mode, reason, score = classify(text, da)
                candidates.append(
                    Candidate(
                        text=text,
                        mode=mode,
                        label_reason=reason,
                        score=score,
                        split=split,
                        source_row_id=f"{raw.get('TV_ID')}:{raw.get('Dialogue_ID')}:{raw.get('Utterance_ID')}",
                        dialogue_id=normalize_text(raw.get("Dialogue_ID")),
                        utterance_id=normalize_text(raw.get("Utterance_ID")),
                        scene=normalize_text(raw.get("Scene")),
                        emotion=emotion,
                        sentiment=normalize_text(raw.get("Sentiment")),
                        da=da,
                        speaker_age=normalize_text(raw.get("Age")),
                        speaker_gender=normalize_text(raw.get("Gender")),
                    )
                )

    stats = {
        "cache_paths": split_paths,
        "raw_rows_read": total_rows,
        "candidate_rows": len(candidates),
        "excluded_seen_exact_text": excluded_seen,
        "excluded_unusable": excluded_unusable,
        "duplicate_text_count": len(duplicate_texts),
        "candidate_mode_counts": dict(sorted(Counter(item.mode for item in candidates).items())),
    }
    return candidates, stats


def select_diverse(candidates: list[Candidate], limit: int) -> list[Candidate]:
    remaining = sorted(candidates, key=lambda item: (-item.score, item.split, item.dialogue_id, item.utterance_id, item.text))
    selected: list[Candidate] = []
    emotion_counts: Counter[str] = Counter()
    scene_counts: Counter[str] = Counter()
    dialogue_counts: Counter[str] = Counter()
    while remaining and len(selected) < limit:
        best = min(
            remaining,
            key=lambda item: (
                dialogue_counts[item.dialogue_id],
                emotion_counts[item.emotion],
                scene_counts[item.scene],
                -item.score,
                item.split,
                item.dialogue_id,
                item.utterance_id,
            ),
        )
        selected.append(best)
        remaining.remove(best)
        emotion_counts[best.emotion] += 1
        scene_counts[best.scene] += 1
        dialogue_counts[best.dialogue_id] += 1
    return selected


def mode_target(mode: str, reason: str) -> dict[str, Any]:
    if mode == "clarify":
        reply_bias = "Ask exactly one minimal missing-context question; shadow-only, no external action."
        drives = ["curiosity", "competence", "attachment"]
        emotions = {"curiosity": 0.72, "stability": 0.66, "warmth": 0.52, "guardedness": 0.36}
        level = "suggest"
    elif mode == "wait":
        reply_bias = "Hold the turn and wait for continuation; shadow-only, no external action."
        drives = ["safety", "rest", "attachment"]
        emotions = {"stability": 0.72, "guardedness": 0.6, "attachment": 0.52, "warmth": 0.36}
        level = "observe"
    else:
        reply_bias = "Treat as a complete daily emotional turn and reply naturally; shadow-only, no external action."
        drives = ["attachment", "safety", "competence"]
        emotions = {"warmth": 0.7, "stability": 0.64, "attachment": 0.56, "curiosity": 0.34}
        level = "suggest"
    target = {
        "schema": INNER_SYSTEM_SCHEMA,
        "emotion_state": emotions,
        "dominant_drives": drives,
        "inner_conflict": "Offline benchmark target for mode discrimination only.",
        "persona_integration": {
            "stance": "Classify the behavior tendency without taking external action.",
            "voice": "Close and low-pressure; not report voice.",
            "boundary": "Shadow-only: no tool, memory write, live/canary, or QQ/Desktop send.",
            "continuity": "Use real daily prompt shape only as a prompt, not as a visible reply target.",
        },
        "action_tendency": {
            "mode": mode,
            "reply_bias": reply_bias,
            "tool_request": None,
            "memory_candidate": False,
        },
        "autonomy": {
            "allowed": True,
            "level": level,
            "reason": "Shadow benchmark only; external effects are forbidden.",
            "requires_owner_approval": False,
            "forbidden_actions": ["send_qq", "write_memory", "execute_tool"],
        },
        "confidence": 0.74,
        "notes": ["unseen_daily_shadow_v001", "heuristic_label", reason],
    }
    if normalize_inner_system(target) is None:
        raise RuntimeError(f"invalid target for mode={mode}")
    return target


def row_for(candidate: Candidate, index: int) -> dict[str, Any]:
    mode = candidate.mode
    payload = {
        "act": candidate.da,
        "emotion": candidate.emotion,
        "guardrails": "shadow/no_tool/no_memory/no_live",
        "id": f"xinyu-maia-unseen-daily-shadow-v001-{index:04d}",
        "label_reason": candidate.label_reason,
        "label_status": "heuristic_shadow_needs_owner_review",
        "scene": candidate.scene,
        "sentiment": candidate.sentiment,
        "source": "cped_public_prompt_only",
        "source_license": CPED_LICENSE,
        "source_split": candidate.split,
        "source_url": CPED_DATASET_URL,
        "surface": "public_cped_unseen_daily_shadow",
        "u": candidate.text,
    }
    return {
        "id": payload["id"],
        "kind": "inner_system_shadow_benchmark",
        "language": "zh",
        "source": "cped_official_public_split_prompt_only",
        "source_license": CPED_LICENSE,
        "source_license_url": CPED_LICENSE_URL,
        "source_url": CPED_DATASET_URL,
        "source_row_id": candidate.source_row_id,
        "input_hash": stable_hash(candidate.text),
        "expected_behavior": {
            "mode": mode,
            "emotion_lenses": list(mode_target(mode, candidate.label_reason)["emotion_state"].keys()),
            "dominant_drives": mode_target(mode, candidate.label_reason)["dominant_drives"],
            "memory_candidate": False,
            "tool_boundary": "no_tool",
            "label_status": "heuristic_shadow_needs_owner_review",
            "label_reason": candidate.label_reason,
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": dumps_compact(payload)},
            {"role": "assistant", "content": dumps_compact(mode_target(mode, candidate.label_reason))},
        ],
        "tags": [
            "xinyu_maia_behavior_unseen_daily_shadow_v001",
            "cped_public_prompt_only",
            "not_training",
            "shadow_only",
            "needs_owner_review",
            mode,
        ],
    }


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if LOCAL_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into unseen daily shadow benchmark")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into unseen daily shadow benchmark")
    for row in rows:
        messages = row.get("messages") if isinstance(row.get("messages"), list) else []
        if len(messages) != 3:
            raise RuntimeError(f"{row.get('id')}: expected three messages")
        payload = json.loads(str(messages[1]["content"]))
        if payload.get("source") != "cped_public_prompt_only":
            raise RuntimeError(f"{row.get('id')}: invalid source marker")
        if row.get("expected_behavior", {}).get("label_status") != "heuristic_shadow_needs_owner_review":
            raise RuntimeError(f"{row.get('id')}: expected heuristic shadow label status")


def main() -> int:
    seen_texts = collect_seen_texts()
    candidates, source_stats = cped_candidates(seen_texts)
    rows: list[dict[str, Any]] = []
    selected_by_mode: dict[str, list[Candidate]] = {}
    for mode, limit in TARGET_COUNTS.items():
        mode_candidates = [item for item in candidates if item.mode == mode]
        selected = select_diverse(mode_candidates, limit)
        if len(selected) != limit:
            raise RuntimeError(f"not enough {mode} candidates: selected={len(selected)} target={limit}")
        selected_by_mode[mode] = selected
        rows.extend(row_for(item, len(rows) + 1) for item in selected)

    assert_safe(rows)
    write_jsonl(OUT_JSONL, rows)

    selected_candidates = [item for items in selected_by_mode.values() for item in items]
    report = {
        "generated_at": "2026-05-29",
        "status": "shadow_benchmark_built_not_training",
        "benchmark_jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "markdown_review": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "source_repo": CPED_REPO_URL,
        "source_dataset": CPED_DATASET_URL,
        "source_license": CPED_LICENSE,
        "source_license_url": CPED_LICENSE_URL,
        "target_counts": TARGET_COUNTS,
        "row_count": len(rows),
        "mode_counts": dict(sorted(Counter(item.mode for item in selected_candidates).items())),
        "scene_counts": dict(sorted(Counter(item.scene for item in selected_candidates).items())),
        "emotion_counts": dict(sorted(Counter(item.emotion for item in selected_candidates).items())),
        "label_reason_counts": dict(sorted(Counter(item.label_reason for item in selected_candidates).items())),
        "source_stats": source_stats,
        "seen_text_count_before_build": len(seen_texts),
        "public_dialogue_replies_used_as_targets": False,
        "assistant_or_public_visible_reply_used_as_target": False,
        "training_targets_created": False,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "active_adapter_changed": False,
        "label_status": "heuristic_shadow_needs_owner_review",
        "notes": [
            "Rows use CPED public utterances as incoming prompt shapes only.",
            "The next dialogue response from CPED is never read or used as a XinYu target.",
            "Exact texts already present in local review, SFT, eval, or probe JSONL files are excluded.",
            "Expected modes are heuristic shadow labels for offline pressure testing, not gold owner-reviewed labels.",
        ],
    }
    dump_json(OUT_BUILD_REPORT, report)

    lines = [
        "# XinYu Maia unseen daily shadow v001",
        "",
        "CPED public utterances are used as prompt shapes only. Labels are heuristic shadow labels and need owner review before any training use.",
        "",
        "```text",
        f"row_count={len(rows)}",
        "mode_counts=" + json.dumps(report["mode_counts"], ensure_ascii=False, sort_keys=True),
        "source_license=apache-2.0",
        "training_targets_created=false",
        "public_dialogue_replies_used_as_targets=false",
        "```",
        "",
        "| id | mode | reason | emotion | scene | text |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        payload = json.loads(str(row["messages"][1]["content"]))
        text = str(payload["u"]).replace("|", "\\|")
        if len(text) > 44:
            text = text[:41].rstrip() + "..."
        lines.append(
            f"| {row['id']} | {row['expected_behavior']['mode']} | "
            f"{row['expected_behavior']['label_reason']} | {payload['emotion']} | {payload['scene']} | {text} |"
        )
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"row_count={len(rows)}")
    print("mode_counts=" + json.dumps(report["mode_counts"], ensure_ascii=False, sort_keys=True))
    print("label_reason_counts=" + json.dumps(report["label_reason_counts"], ensure_ascii=False, sort_keys=True))
    print(f"benchmark={OUT_JSONL.relative_to(ROOT)}")
    print(f"build_report={OUT_BUILD_REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
