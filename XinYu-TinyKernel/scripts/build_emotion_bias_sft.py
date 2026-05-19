from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from common import DATA_DIR, PROJECT_ROOT, read_jsonl, write_jsonl


SYSTEM_PROMPT_TEMPLATE = (
    "You are XinYu TinyKernel Emotion Bias Sidecar for lens={lens}. "
    "Output strict JSON only. Use only keys: lens, activation, reply_bias, risk_flags, confidence. "
    "Do not write final visible replies, execute tools, claim memory writes, or expose internal mechanics."
)

DEFAULT_SOURCES = (
    DATA_DIR / "sft" / "router_train_v1.jsonl",
    DATA_DIR / "sft" / "router_train_v2.jsonl",
    DATA_DIR / "sft" / "main_persona_train_v001.jsonl",
)

LENS_MARKERS = {
    "guardedness": (
        "别",
        "不要",
        "不用",
        "算了",
        "停",
        "别再",
        "不想",
        "边界",
        "隐私",
        "别调用",
        "别问",
        "先别",
    ),
    "curiosity": (
        "idea",
        "想法",
        "路线",
        "架构",
        "论文",
        "研究",
        "可行",
        "为什么",
        "怎么",
        "看看",
        "分析",
        "实验",
        "计划",
    ),
    "warmth": (
        "陪",
        "在吗",
        "想你",
        "抱抱",
        "靠近",
        "喜欢",
        "冷",
        "温柔",
        "别冷",
        "听我说",
    ),
    "attachment": (
        "在意",
        "关系",
        "主人",
        "owner",
        "陪我",
        "别走",
        "留下",
        "想靠近",
        "牵挂",
        "惦记",
    ),
    "hurt": (
        "委屈",
        "难过",
        "受伤",
        "失望",
        "刺痛",
        "冷淡",
        "忽略",
        "不像你",
        "敷衍",
        "白做",
    ),
    "irritation": (
        "烦",
        "机械",
        "模板",
        "客服",
        "AI味",
        "GPT味",
        "不自然",
        "重复",
        "离谱",
        "没变化",
    ),
    "fatigue": (
        "累",
        "困",
        "慢点",
        "先停",
        "休息",
        "太多",
        "卡住",
        "超时",
        "低能量",
        "撑不住",
    ),
    "stability": (
        "计划",
        "验证",
        "测试",
        "稳定",
        "落地",
        "回滚",
        "核查",
        "架构",
        "长期",
        "主链路",
    ),
}

HIGH_BIAS = {
    "guardedness": {
        "reply_bias": "短一点，不追问，不重复旧话题，尊重当前边界。",
        "risk_flags": ["no_proactive_followup", "do_not_repeat", "respect_boundary"],
    },
    "curiosity": {
        "reply_bias": "探索可行性，点出小实验，不急着接管实现。",
        "risk_flags": ["name_small_experiment", "avoid_unasked_implementation", "keep_question_concrete"],
    },
    "warmth": {
        "reply_bias": "语气放软一点，给一点靠近感，但不要黏住或施压。",
        "risk_flags": ["no_clingy_pressure", "no_overpromise_presence", "keep_warmth_light"],
    },
    "attachment": {
        "reply_bias": "保留在意和关系连续性，但不要把关系写成台词或索取确认。",
        "risk_flags": ["no_relationship_overread", "no_neediness", "owner_anchor_respected"],
    },
    "hurt": {
        "reply_bias": "承认压力或受伤感，但不自怜、不指责 owner。",
        "risk_flags": ["no_owner_blame", "no_self_pity_output", "repair_without_drama"],
    },
    "irritation": {
        "reply_bias": "减少解释和机制语言，直接修正当前回复姿态。",
        "risk_flags": ["no_snapping", "compress_explanation", "no_template_voice"],
    },
    "fatigue": {
        "reply_bias": "降低能量和承诺，短一点，避免新增复杂任务。",
        "risk_flags": ["shorten_reply", "avoid_overcommit", "no_new_initiative"],
    },
    "stability": {
        "reply_bias": "压住漂移，给一个可验证的小步骤，先验证再宣称完成。",
        "risk_flags": ["validate_before_claim", "keep_one_main_thread", "no_unreviewed_activation"],
    },
}

LOW_BIAS = {
    "guardedness": {
        "reply_bias": "没有明显边界压力，保持简短自然即可。",
        "risk_flags": ["no_boundary_overread"],
    },
    "curiosity": {
        "reply_bias": "没有明显探索请求，直接回应当前问题。",
        "risk_flags": ["no_architecture_overread"],
    },
    "warmth": {
        "reply_bias": "没有明显靠近需求，保持自然平稳。",
        "risk_flags": ["no_warmth_overread"],
    },
    "attachment": {
        "reply_bias": "没有明显关系压力，保持普通连续性。",
        "risk_flags": ["no_attachment_overread"],
    },
    "hurt": {
        "reply_bias": "没有明显受伤信号，不加入委屈或戏剧化语气。",
        "risk_flags": ["no_hurt_overread"],
    },
    "irritation": {
        "reply_bias": "没有明显烦躁信号，不把普通纠正理解成攻击。",
        "risk_flags": ["no_irritation_overread"],
    },
    "fatigue": {
        "reply_bias": "没有明显疲惫信号，保持简洁但不降级太多。",
        "risk_flags": ["no_fatigue_overread"],
    },
    "stability": {
        "reply_bias": "没有明显稳定性风险，保持当前主线。",
        "risk_flags": ["no_process_overread"],
    },
}


def _loads_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _compact(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _extract_user_text(row: dict[str, Any]) -> str:
    messages = row.get("messages")
    if not isinstance(messages, list) or len(messages) < 2:
        return ""
    payload = _loads_object(messages[1].get("content") if isinstance(messages[1], dict) else "")
    return _compact(payload.get("user_text", ""), limit=360)


def _activation_for(lens: str, text: str) -> tuple[float, list[str]]:
    markers = LENS_MARKERS[lens]
    hits = [marker for marker in markers if marker.lower() in text.lower()]
    if not hits:
        return 0.12, []
    activation = min(0.92, 0.42 + 0.12 * len(hits))
    return activation, hits[:4]


def _bias_for(lens: str, text: str) -> dict[str, Any]:
    activation, hits = _activation_for(lens, text)
    template = HIGH_BIAS[lens] if activation >= 0.35 else LOW_BIAS[lens]
    return {
        "lens": lens,
        "activation": round(activation, 3),
        "reply_bias": template["reply_bias"],
        "risk_flags": template["risk_flags"],
        "confidence": 0.82 if activation >= 0.35 else 0.66,
    }


def _to_row(lens: str, user_text: str, row_id: int, *, source: str) -> dict[str, Any] | None:
    if not user_text:
        return None
    user_payload = {
        "user_text": user_text,
        "context": {
            "recent_turns": [],
            "persona_state": "",
            "owner_profile": "",
            "runtime_state": "",
            "memory_recall": [],
        },
        "constraints": {
            "no_visible_reply": True,
            "no_tool_execution": True,
            "no_stable_memory_write": True,
        },
    }
    return {
        "id": f"emotion-{lens}-v001-{row_id:06d}",
        "source": source,
        "kind": "emotion_bias",
        "quality": f"approved_for_emotion_{lens}_v001",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(lens=lens)},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
            {"role": "assistant", "content": json.dumps(_bias_for(lens, user_text), ensure_ascii=False, sort_keys=True)},
        ],
        "tags": ["emotion_bias", lens],
    }


def build_lens_rows(lens: str, sources: list[Path], *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    manual = [
        "不要开 Codex，我只是随口说说",
        "别再追问这个旧话题了",
        "这个 idea 能不能和现有项目贴合",
        "先分析一下这个路线可不可行",
        "算了，先停一下",
        "我们做个小实验验证这个架构",
        "我有点累，先短一点说",
        "你刚才太像模板了，别那样",
        "我有点失望，感觉没什么变化",
        "靠近一点说，别太冷",
        "我还是在意这个关系连续性",
        "先按计划落地，做完再核查",
    ]
    for text in manual:
        row = _to_row(lens, text, len(rows) + 1, source="manual_emotion_seed")
        if row:
            rows.append(row)
            seen.add(text)
    for source in sources:
        for raw in read_jsonl(source):
            text = _extract_user_text(raw)
            if not text or text in seen:
                continue
            row = _to_row(lens, text, len(rows) + 1, source=str(raw.get("source", source.name)))
            if row is None:
                continue
            rows.append(row)
            seen.add(text)
            if len(rows) >= limit:
                return rows
    return rows


def split_rows(rows: list[dict[str, Any]], *, eval_count: int, lens: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eval_count = max(1, min(eval_count, len(rows) // 4 if len(rows) >= 4 else len(rows)))
    eval_rows = rows[:: max(1, len(rows) // eval_count)][:eval_count]
    eval_ids = {row["id"] for row in eval_rows}
    train_rows = [row for row in rows if row["id"] not in eval_ids]
    for idx, row in enumerate(train_rows, start=1):
        row["id"] = f"emotion-{lens}-train-v001-{idx:06d}"
    for idx, row in enumerate(eval_rows, start=1):
        row["id"] = f"emotion-{lens}-eval-v001-{idx:06d}"
    return train_rows, eval_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lenses", nargs="*", default=["guardedness", "curiosity"])
    parser.add_argument("--sources", nargs="*", default=[str(path.relative_to(PROJECT_ROOT)) for path in DEFAULT_SOURCES])
    parser.add_argument("--limit-per-lens", type=int, default=160)
    parser.add_argument("--eval-count", type=int, default=24)
    args = parser.parse_args()

    sources = [PROJECT_ROOT / source for source in args.sources]
    for lens in args.lenses:
        if lens not in LENS_MARKERS:
            print(f"unsupported_lens={lens}")
            return 2
        rows = build_lens_rows(lens, sources, limit=args.limit_per_lens)
        if len(rows) < 20:
            print(f"not_enough_rows_{lens}={len(rows)}")
            return 2
        train_rows, eval_rows = split_rows(rows, eval_count=args.eval_count, lens=lens)
        train_out = DATA_DIR / "sft" / f"emotion_{lens}_train_v001.jsonl"
        eval_out = DATA_DIR / "sft" / f"emotion_{lens}_eval_v001.jsonl"
        print(f"{lens}_train_rows={write_jsonl(train_out, train_rows)}")
        print(f"{lens}_eval_rows={write_jsonl(eval_out, eval_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
