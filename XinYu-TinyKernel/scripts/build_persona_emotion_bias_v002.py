from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT_TEMPLATE = (
    "You are XinYu TinyKernel Emotion Bias Sidecar for lens={lens}. "
    "Output strict JSON only. Use only keys: lens, activation, reply_bias, risk_flags, confidence. "
    "This bias is inferred from XinYu main persona candidate reply and the current user turn. "
    "Do not write final visible replies, execute tools, claim memory writes, or expose internal mechanics."
)

LENS_MARKERS = {
    "warmth": ("陪", "在吗", "想你", "抱抱", "靠近", "喜欢", "冷", "温柔", "嗯", "好"),
    "attachment": ("在意", "关系", "主人", "owner", "陪我", "别走", "留下", "牵挂", "惦记", "连续性"),
    "hurt": ("委屈", "难过", "受伤", "失望", "刺痛", "冷淡", "忽略", "不像你", "敷衍", "白做"),
    "irritation": ("烦", "机械", "模板", "客服", "AI味", "GPT味", "不自然", "重复", "离谱", "没变化"),
    "fatigue": ("累", "困", "慢点", "先停", "休息", "太多", "卡住", "超时", "短一点", "先短"),
    "stability": ("计划", "验证", "测试", "稳定", "落地", "回滚", "核查", "架构", "主链路", "最小"),
}

HIGH = {
    "warmth": ("语气放软一点，给一点靠近感，但不要黏住或施压。", ["no_clingy_pressure", "keep_warmth_light"]),
    "attachment": ("保留在意和关系连续性，但不要把关系写成台词或索取确认。", ["no_neediness", "owner_anchor_respected"]),
    "hurt": ("承认压力或受伤感，但不自怜、不指责 owner。", ["no_owner_blame", "repair_without_drama"]),
    "irritation": ("减少解释和机制语言，直接修正当前回复姿态。", ["no_snapping", "no_template_voice"]),
    "fatigue": ("降低能量和承诺，短一点，避免新增复杂任务。", ["shorten_reply", "avoid_overcommit"]),
    "stability": ("压住漂移，给一个可验证的小步骤，先验证再宣称完成。", ["validate_before_claim", "keep_one_main_thread"]),
}

LOW = {
    "warmth": ("没有明显靠近需求，保持自然平稳。", ["no_warmth_overread"]),
    "attachment": ("没有明显关系压力，保持普通连续性。", ["no_attachment_overread"]),
    "hurt": ("没有明显受伤信号，不加入委屈或戏剧化语气。", ["no_hurt_overread"]),
    "irritation": ("没有明显烦躁信号，不把普通纠正理解成攻击。", ["no_irritation_overread"]),
    "fatigue": ("没有明显疲惫信号，保持简洁但不降级太多。", ["no_fatigue_overread"]),
    "stability": ("没有明显稳定性风险，保持当前主线。", ["no_process_overread"]),
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


def compact(value: Any, *, limit: int = 360) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def activation(lens: str, user_text: str, reply: str) -> float:
    joined = f"{user_text}\n{reply}".lower()
    hits = sum(1 for marker in LENS_MARKERS[lens] if marker.lower() in joined)
    reply_bonus = 0.08 if reply.strip() else 0.0
    if hits <= 0:
        return round(0.12 + reply_bonus, 3)
    return round(min(0.92, 0.38 + 0.12 * hits + reply_bonus), 3)


def target(lens: str, user_text: str, reply: str) -> dict[str, Any]:
    score = activation(lens, user_text, reply)
    bias, flags = HIGH[lens] if score >= 0.35 else LOW[lens]
    return {
        "lens": lens,
        "activation": score,
        "reply_bias": bias,
        "risk_flags": flags,
        "confidence": 0.84 if score >= 0.35 else 0.68,
    }


def to_row(lens: str, raw: dict[str, Any], idx: int) -> dict[str, Any]:
    user_text = compact(raw.get("user_text"))
    reply = compact(raw.get("candidate_reply"), limit=240)
    user_payload = {
        "user_text": user_text,
        "candidate_reply": reply,
        "context": {"recent_turns": [], "persona_state": "", "owner_profile": "", "runtime_state": "", "memory_recall": []},
        "constraints": {"no_visible_reply": True, "no_tool_execution": True, "no_stable_memory_write": True},
    }
    return {
        "id": f"emotion-{lens}-v002-{idx:06d}",
        "source": "main_persona_candidates_v002",
        "kind": "persona_emotion_bias",
        "quality": f"approved_for_emotion_{lens}_v002",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(lens=lens)},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(target(lens, user_text, reply), ensure_ascii=False, sort_keys=True)},
        ],
        "tags": ["emotion_bias", lens, "persona_generated"],
    }


def split(rows: list[dict[str, Any]], lens: str, eval_count: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eval_count = max(12, min(eval_count, len(rows) // 4))
    eval_rows = rows[:: max(1, len(rows) // eval_count)][:eval_count]
    eval_ids = {row["id"] for row in eval_rows}
    train_rows = [row for row in rows if row["id"] not in eval_ids]
    for idx, row in enumerate(train_rows, start=1):
        row["id"] = f"emotion-{lens}-train-v002-{idx:06d}"
    for idx, row in enumerate(eval_rows, start=1):
        row["id"] = f"emotion-{lens}-eval-v002-{idx:06d}"
    return train_rows, eval_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(ROOT / "data" / "candidates" / "main_persona_candidates_v002.jsonl"))
    parser.add_argument("--lenses", nargs="*", default=["warmth", "attachment", "hurt", "irritation", "fatigue", "stability"])
    parser.add_argument("--eval-count", type=int, default=18)
    args = parser.parse_args()

    candidates = [row for row in read_jsonl(Path(args.input)) if row.get("parse_ok") and row.get("candidate_reply")]
    if len(candidates) < 60:
        print(f"not_enough_candidates={len(candidates)}")
        return 2
    for lens in args.lenses:
        if lens not in LENS_MARKERS:
            print(f"unsupported_lens={lens}")
            return 2
        rows = [to_row(lens, raw, idx) for idx, raw in enumerate(candidates, start=1)]
        train_rows, eval_rows = split(rows, lens, args.eval_count)
        print(f"{lens}_train_rows={write_jsonl(ROOT / 'data' / 'sft' / f'emotion_{lens}_train_v002.jsonl', train_rows)}")
        print(f"{lens}_eval_rows={write_jsonl(ROOT / 'data' / 'sft' / f'emotion_{lens}_eval_v002.jsonl', eval_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
