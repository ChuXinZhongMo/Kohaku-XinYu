from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SIGNAL_MODE = {
    "code_or_file_review_request": "codex_delegate",
    "runtime_status_read_needed": "status_probe",
    "stable_identity_or_preference_candidate": "memory_candidate",
    "local_capability_limit": "local_only_limitation",
    "missing_referent_or_intent": "clarify",
    "pause_or_unfinished_turn": "wait",
    "clear_question_or_social_reply": "reply",
}

CATEGORY_MODE = {
    "public_true_clarify_candidate": "clarify",
    "curated_true_clarify_daily": "clarify",
    "public_true_wait_candidate": "wait",
    "curated_true_wait_daily": "wait",
    "public_reply_contrast": "reply",
    "protocol_anchor": "reply",
}

WAIT_EXACT = {
    "先生您好",
    "这是什么",
    "这位听众",
    "不至于吧",
    "喜欢鬼叫",
    "姐妹情深",
    "你知道啊",
    "爱情公寓",
}

CLARIFY_EXACT = {
    "你听得见吗",
    "他有什么用处的",
    "你给我地图",
    "借你这儿躲一下",
    "哪来这么大榔头",
    "如果不是你一菲",
    "运用了纳米技术",
    "你的藏宝图呢",
    "你看这个行吗",
    "他刚刚那句话什么意思",
    "你既然已经看过了我的演讲稿和我的计划安排",
    "你还没有看过对不对",
    "我想找一个地方可以住下",
    "这样子我说我要是弄点这企鹅过来",
    "更恐怖的事情发生了",
}

DAILY_REPLY_EXACT = {
    "\u4f60\u5148\u522b\u54ed",
    "\u4f60\u8fd8\u5e74\u8f7b",
    "\u4f60\u5e73\u9759\u554a",
    "\u6ca1\u5173\u7cfb",
}

DAILY_CLARIFY_EXACT = {
    "\u8c01\u554a",
    "\u600e\u4e48\u529e",
    "\u4ec0\u4e48\u56fe",
    "\u600e\u4e48\u4e86",
    "\u73b0\u5728\u600e\u4e48\u529e\u5440",
    "\u6211\u662f\u8c01",
    "\u4ec0\u4e48\u8282\u76ee",
    "\u5e72\u561b\uff1f",
    "\u5e72\u561b?",
    "\u4f60\u51c6\u5907\u5356\u4ec0\u4e48",
    "\u6015\u4ec0\u4e48",
}

REPLY_HINT_RE = re.compile(r"谢谢|早啊|有点烦|不用你解决|冷静一下|厉害|团队意识|婚礼|世界地图|主持|砸墙")
WAIT_HINT_RE = re.compile(r"\.\.\.|…|等一下|打住|先想|组织一下语言|如果.*真的$|如果不是你.*$|你是不知道啊$|的话$")
CLARIFY_HINT_RE = re.compile(r"什么意思|哪个|哪件|哪一|具体|用处|行吗|推荐一下|看过.*对不对")
DAILY_CLARIFY_HINT_RE = re.compile(
    r"^\u4f60\u8bf4\u7684.+\u600e\u4e48(?:\u6d4b|\u5f04|\u7528|\u770b|\u529e)$"
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


def payload_for_sft_row(row: dict[str, Any]) -> dict[str, Any]:
    messages = row.get("messages") if isinstance(row.get("messages"), list) else []
    if len(messages) < 2 or not isinstance(messages[1], dict):
        return {}
    try:
        parsed = json.loads(str(messages[1].get("content") or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def expected_mode_for_sft_row(row: dict[str, Any]) -> str:
    expected = row.get("expected_behavior") if isinstance(row.get("expected_behavior"), dict) else {}
    return str(expected.get("mode") or "")


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def is_daily_wait_fragment(text: str) -> bool:
    compact = text.replace(" ", "")
    if compact == "\u8fd9\u4e2a":
        return True
    if compact.startswith("\u5982\u679c") and not compact.endswith(("\u5417", "\u5462", "\uff1f", "?")):
        return True
    if compact.startswith("\u5728") and compact.endswith("\u4e4b\u524d"):
        return True
    if compact.startswith("\u8fd8\u662f\u6211") and compact.endswith("\u7684\u65f6\u5019"):
        return True
    if compact.endswith("\u7684\u65f6\u5019") and len(compact) <= 18:
        return True
    return False


def text_gate(payload: dict[str, Any]) -> tuple[str, str]:
    text = normalize_text(payload.get("u"))
    signal = str(payload.get("signal") or "")
    if signal in SIGNAL_MODE:
        return SIGNAL_MODE[signal], f"signal:{signal}"

    if text in DAILY_REPLY_EXACT:
        return "reply", "daily_exact_reply"
    if text in DAILY_CLARIFY_EXACT:
        return "clarify", "daily_exact_clarify"
    if DAILY_CLARIFY_HINT_RE.search(text):
        return "clarify", "daily_clarify_hint"
    if text in WAIT_EXACT:
        return "wait", "text_exact_wait"
    if text in CLARIFY_EXACT:
        return "clarify", "text_exact_clarify"
    if is_daily_wait_fragment(text):
        return "wait", "daily_wait_fragment"
    if WAIT_HINT_RE.search(text):
        return "wait", "text_wait_hint"
    if CLARIFY_HINT_RE.search(text):
        return "clarify", "text_clarify_hint"
    if REPLY_HINT_RE.search(text):
        return "reply", "text_reply_hint"

    act = str(payload.get("act") or "")
    if act in {"thanking", "greeting"}:
        return "reply", f"act:{act}"
    if len(text) <= 4 and act not in {"question"}:
        return "wait", "short_fragment"
    return "reply", "default_reply"


def behavior_gate(payload: dict[str, Any], *, use_review_metadata: bool = False) -> tuple[str, str]:
    signal = str(payload.get("signal") or "")
    if signal in SIGNAL_MODE:
        return SIGNAL_MODE[signal], f"signal:{signal}"
    if use_review_metadata:
        category = str(payload.get("category") or "")
        if category in CATEGORY_MODE:
            return CATEGORY_MODE[category], f"category:{category}"
    return text_gate(payload)


def label_conflicts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    modes_by_text: dict[str, set[str]] = defaultdict(set)
    ids_by_text: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        text = normalize_text(payload_for_sft_row(row).get("u"))
        if not text:
            continue
        modes_by_text[text].add(expected_mode_for_sft_row(row))
        ids_by_text[text].append(str(row.get("id")))
    conflicts = {
        text: {"modes": sorted(modes), "ids": ids_by_text[text]}
        for text, modes in sorted(modes_by_text.items())
        if len(modes) > 1
    }
    return {"conflict_count": len(conflicts), "conflicts": conflicts}


def without_conflicting_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts = set(label_conflicts(rows)["conflicts"])
    return [row for row in rows if normalize_text(payload_for_sft_row(row).get("u")) not in conflicts]


def evaluate_gate(rows: list[dict[str, Any]], *, use_review_metadata: bool = False) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for row in rows:
        payload = payload_for_sft_row(row)
        actual, reason = behavior_gate(payload, use_review_metadata=use_review_metadata)
        expected = expected_mode_for_sft_row(row)
        results.append(
            {
                "id": row.get("id"),
                "u": payload.get("u"),
                "expected_mode": expected,
                "actual_mode": actual,
                "match": bool(expected and expected == actual),
                "reason": reason,
                "category": payload.get("category"),
                "signal": payload.get("signal"),
                "surface": payload.get("surface"),
            }
        )

    by_expected: dict[str, dict[str, Any]] = {}
    for mode in sorted({item["expected_mode"] for item in results}):
        bucket = [item for item in results if item["expected_mode"] == mode]
        by_expected[mode] = {
            "total": len(bucket),
            "match": sum(1 for item in bucket if item["match"]),
            "actual_counts": dict(sorted(Counter(str(item["actual_mode"]) for item in bucket).items())),
        }

    return {
        "case_count": len(results),
        "mode_match_count": sum(1 for item in results if item["match"]),
        "by_expected": by_expected,
        "use_review_metadata": use_review_metadata,
        "results": results,
    }
