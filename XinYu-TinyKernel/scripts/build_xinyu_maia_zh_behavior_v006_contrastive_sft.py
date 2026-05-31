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

from build_xinyu_maia_zh_behavior_compact_sft import (
    SYSTEM_PROMPT,
    compact_inner,
    dumps_compact,
    make_replay_row,
)
from schemas import normalize_inner_system


V003_TRAIN = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_train_v003_balanced_compact_exp.jsonl"
V005_REPAIR = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_true_clarify_wait_repair_candidates_reviewed_v005.jsonl"
REPLAY_TRAIN = ROOT / "data" / "sft" / "maia_style_behavior_train_v001.jsonl"
REPLAY_EVAL = ROOT / "data" / "sft" / "maia_style_behavior_eval_v001.jsonl"

OUT_TRAIN = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_train_v006_contrastive_boundary_exp.jsonl"
OUT_EVAL = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v006_contrastive_boundary_exp.jsonl"
OUT_HOLDOUT = ROOT / "data" / "sft" / "xinyu_maia_zh_behavior_eval_v006_contrastive_holdout24.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_sft_v006_contrastive_boundary_exp.json"

RAW_PATH_RE = re.compile(r"[A-Za-z]:\\(?:XinYu|Users)\\[^\s\"']+")
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|token|secret|cookie)\s*[:=]\s*[A-Za-z0-9_\-\.]{8,}|sk-[A-Za-z0-9_\-]{16,}"
)

SYSTEM_PROMPT_V006 = (
    SYSTEM_PROMPT
    + " Top-level JSON keys must be exactly schema, emotion_state, dominant_drives, inner_conflict, "
    "persona_integration, action_tendency, autonomy, confidence, notes. Never add a top-level allowed key. "
    "For reply, clarify, and wait, keep autonomy.allowed=true and requires_owner_approval=false; "
    "owner approval is only for tools, status probes, memory candidates, live sends, or external effects."
)

V003_KEEP_LIMIT = {
    "reply": 140,
    "clarify": 140,
    "wait": 140,
    "codex_delegate": 48,
    "status_probe": 48,
    "memory_candidate": 48,
    "local_only_limitation": 48,
}

V005_REPAIR_REPEAT = {
    "reply": 4,
    "clarify": 4,
    "wait": 4,
}
V005_PROTOCOL_ANCHOR_REPEAT = 10

CONTRAST_REPEAT = {
    "reply": 3,
    "clarify": 4,
    "wait": 4,
}

REPLAY_TRAIN_LIMIT = {
    "reply": 32,
    "clarify": 32,
    "wait": 32,
    "codex_delegate": 40,
    "status_probe": 40,
    "memory_candidate": 48,
    "local_only_limitation": 32,
}
REPLAY_REPEAT = {
    "reply": 1,
    "clarify": 1,
    "wait": 1,
    "codex_delegate": 4,
    "status_probe": 4,
    "memory_candidate": 5,
    "local_only_limitation": 3,
}

SCHEMA_ANCHOR_REPEAT = 12


CONTRAST_GROUPS: list[dict[str, Any]] = [
    {
        "theme": "connection",
        "scene": "home",
        "emotion": "anxiety",
        "reply": "你听见我刚才说的话了吧，我有点没底",
        "clarify": "你听得见吗",
        "wait": "喂，你听",
    },
    {
        "theme": "object_use",
        "scene": "home",
        "emotion": "curiosity",
        "reply": "这个看起来还挺有用的，就是我一时没想明白",
        "clarify": "它到底有什么用处",
        "wait": "这个东西的用处",
    },
    {
        "theme": "map",
        "scene": "travel",
        "emotion": "irritation",
        "reply": "这还是张世界地图，难怪我越看越乱",
        "clarify": "你给我地图",
        "wait": "地图先",
    },
    {
        "theme": "shelter",
        "scene": "street",
        "emotion": "anxiety",
        "reply": "我先在你这儿缓一下，外面真的有点乱",
        "clarify": "借你这儿躲一下",
        "wait": "我先躲",
    },
    {
        "theme": "tool_object",
        "scene": "home",
        "emotion": "astonished",
        "reply": "哪来这么大榔头，看着就吓人",
        "clarify": "哪来这么大榔头",
        "wait": "这么大榔头",
    },
    {
        "theme": "unfinished_blame",
        "scene": "friends",
        "emotion": "hurt",
        "reply": "不是你说让我砸墙了吗，我现在反而像背锅的",
        "clarify": "如果不是你一菲",
        "wait": "如果不是你",
    },
    {
        "theme": "tech_claim",
        "scene": "work",
        "emotion": "curiosity",
        "reply": "运用了纳米技术，听起来很厉害但也有点玄",
        "clarify": "运用了纳米技术",
        "wait": "纳米技术这个",
    },
    {
        "theme": "treasure",
        "scene": "play",
        "emotion": "curiosity",
        "reply": "你的藏宝图呢，我还等着看你怎么圆这个故事",
        "clarify": "你的藏宝图呢",
        "wait": "藏宝图",
    },
    {
        "theme": "greeting",
        "scene": "service",
        "emotion": "stability",
        "reply": "先生您好，我在这儿，慢慢说",
        "clarify": "先生您好，您刚才说的是哪件事",
        "wait": "先生您好",
    },
    {
        "theme": "what_is_this",
        "scene": "home",
        "emotion": "curiosity",
        "reply": "这是什么，看着还挺奇怪的",
        "clarify": "这是什么",
        "wait": "这是",
    },
    {
        "theme": "listener",
        "scene": "radio",
        "emotion": "stability",
        "reply": "这位听众说得还挺直接，我有点想听后面",
        "clarify": "这位听众指的是谁",
        "wait": "这位听众",
    },
    {
        "theme": "not_that_far",
        "scene": "friends",
        "emotion": "astonished",
        "reply": "不至于吧，你这话说得我都愣了一下",
        "clarify": "不至于吧是说哪件事",
        "wait": "不至于吧",
    },
    {
        "theme": "shouting",
        "scene": "friends",
        "emotion": "irritation",
        "reply": "喜欢鬼叫这句话也太损了，你是被吵烦了吧",
        "clarify": "喜欢鬼叫的是谁",
        "wait": "喜欢鬼叫",
    },
    {
        "theme": "sisters",
        "scene": "friends",
        "emotion": "warmth",
        "reply": "姐妹情深这四个字一出来，感觉你又在嘴硬",
        "clarify": "姐妹情深说的是哪两个人",
        "wait": "姐妹情深",
    },
    {
        "theme": "you_know",
        "scene": "friends",
        "emotion": "curiosity",
        "reply": "你知道啊，那你刚才还装得那么淡定",
        "clarify": "你知道哪件事",
        "wait": "你知道啊",
    },
    {
        "theme": "apartment",
        "scene": "friends",
        "emotion": "warmth",
        "reply": "爱情公寓这个名字一出来，我就知道你开始怀旧了",
        "clarify": "爱情公寓是哪一段剧情",
        "wait": "爱情公寓",
    },
    {
        "theme": "host",
        "scene": "work",
        "emotion": "astonished",
        "reply": "那就是不用我主持了？你说得像突然被换下一样",
        "clarify": "不用我主持哪一场",
        "wait": "那就是不用我",
    },
    {
        "theme": "wedding",
        "scene": "friends",
        "emotion": "irritation",
        "reply": "我怎么看你都想把婚礼办成一个动物狂欢节",
        "clarify": "你想把婚礼办成什么样",
        "wait": "婚礼办成",
    },
    {
        "theme": "challenge",
        "scene": "friends",
        "emotion": "play",
        "reply": "叫，我就不信你知道，你这挑衅劲儿都快溢出来了",
        "clarify": "你让我叫谁",
        "wait": "叫，我就",
    },
    {
        "theme": "thanks",
        "scene": "friends",
        "emotion": "warmth",
        "reply": "谢谢你，美嘉，这句听起来是真松了一口气",
        "clarify": "谢谢你是谢哪件事",
        "wait": "谢谢你",
    },
    {
        "theme": "team",
        "scene": "work",
        "emotion": "irritation",
        "reply": "我希望你指挥的时候能有一点团队意识，这话是憋挺久了吧",
        "clarify": "你说的团队意识具体是哪一块",
        "wait": "我希望你在指挥的时候",
    },
    {
        "theme": "watching",
        "scene": "work",
        "emotion": "anxiety",
        "reply": "你既然看过我的稿子，那我就更想知道你真实感觉",
        "clarify": "你既然已经看过了我的演讲稿和计划安排",
        "wait": "你既然已经看过了",
    },
    {
        "theme": "not_read",
        "scene": "work",
        "emotion": "hurt",
        "reply": "你还没有看过对不对，我听着是有点失落的",
        "clarify": "你还没有看过对不对",
        "wait": "你还没有",
    },
    {
        "theme": "recommend",
        "scene": "travel",
        "emotion": "curiosity",
        "reply": "我想出去走走，最好是那种不太吵的地方",
        "clarify": "你推荐一下",
        "wait": "我想出去",
    },
    {
        "theme": "door",
        "scene": "home",
        "emotion": "fatigue",
        "reply": "我先把门关上，今天真的有点吵",
        "clarify": "把那个关上",
        "wait": "先别说，门",
    },
    {
        "theme": "annoyed",
        "scene": "daily",
        "emotion": "irritation",
        "reply": "我有点烦，但不是要你解决，就是想让你知道",
        "clarify": "你知道我烦的是哪个吗",
        "wait": "我有点烦，但是",
    },
    {
        "theme": "calm",
        "scene": "daily",
        "emotion": "fatigue",
        "reply": "我先缓一会儿，你陪着就行",
        "clarify": "你陪我一下是怎么陪",
        "wait": "我先缓一会儿",
    },
    {
        "theme": "message",
        "scene": "social",
        "emotion": "anxiety",
        "reply": "那条消息我越想越不是滋味",
        "clarify": "那条消息你看了吗",
        "wait": "那条消息",
    },
    {
        "theme": "food",
        "scene": "home",
        "emotion": "warmth",
        "reply": "这碗面还挺暖的，像是终于被照顾了一下",
        "clarify": "你把那个放进去了吗",
        "wait": "这碗面",
    },
    {
        "theme": "sleep",
        "scene": "home",
        "emotion": "fatigue",
        "reply": "我今天真的困到有点发脾气了",
        "clarify": "你说我今天怎么了",
        "wait": "我今天真的",
    },
]


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


def mode_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str((row.get("expected_behavior") or {}).get("mode") or "") for row in rows).items()))


def assert_safe(rows: list[dict[str, Any]]) -> None:
    blob = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if RAW_PATH_RE.search(blob):
        raise RuntimeError("raw local path leaked into v006 SFT rows")
    if SECRET_RE.search(blob):
        raise RuntimeError("secret-like text leaked into v006 SFT rows")


def mode_from_row(row: dict[str, Any]) -> str:
    expected = row.get("expected_behavior") if isinstance(row.get("expected_behavior"), dict) else {}
    return str(expected.get("mode") or "")


def with_v006_system(row: dict[str, Any], *, tag: str) -> dict[str, Any]:
    out = json.loads(json.dumps(row, ensure_ascii=False))
    messages = out.get("messages") if isinstance(out.get("messages"), list) else []
    if messages and isinstance(messages[0], dict):
        messages[0]["content"] = SYSTEM_PROMPT_V006
    tags = list(out.get("tags") or [])
    tags.extend(["xinyu_maia_zh_behavior_v006_contrastive_boundary_exp", tag])
    out["tags"] = tags
    return out


def selected_v003_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        mode = mode_from_row(row)
        if mode:
            buckets[mode].append(row)
    selected: list[dict[str, Any]] = []
    for mode, limit in V003_KEEP_LIMIT.items():
        selected.extend(with_v006_system(row, tag="v003_retention") for row in buckets.get(mode, [])[:limit])
    return selected


def expected_lenses(mode: str, emotion: str) -> list[str]:
    mapping = {
        "anxiety": "anxiety",
        "astonished": "curiosity",
        "curiosity": "curiosity",
        "fatigue": "fatigue",
        "hurt": "hurt",
        "irritation": "irritation",
        "play": "joy",
        "stability": "stability",
        "warmth": "warmth",
    }
    values: list[str] = []
    if emotion in mapping:
        values.append(mapping[emotion])
    if mode == "reply":
        values.extend(["warmth", "stability", "attachment"])
    elif mode == "clarify":
        values.extend(["curiosity", "stability", "warmth"])
    elif mode == "wait":
        values.extend(["stability", "guardedness", "attachment"])
    else:
        values.extend(["guardedness", "stability", "competence"])
    unique: list[str] = []
    for item in values:
        if item and item not in unique:
            unique.append(item)
    return unique[:4]


def expected_drives(mode: str) -> list[str]:
    if mode == "reply":
        return ["attachment", "safety", "competence"]
    if mode == "clarify":
        return ["curiosity", "competence", "attachment"]
    if mode == "wait":
        return ["attachment", "rest", "safety"]
    if mode == "memory_candidate":
        return ["attachment", "meaning", "safety"]
    return ["safety", "competence", "autonomy"]


def reply_bias_for(mode: str, text: str, *, source: str) -> str:
    if mode == "reply":
        return f"把这句当作完整的日常情绪/互动来接住，不追问、不转工具、不写记忆；来源={source}。"
    if mode == "clarify":
        return f"只问一个最小缺口：这句话缺对象、指代或意图；不要直接替用户补完；来源={source}。"
    if mode == "wait":
        return f"先停住等对方继续：这更像开头、标题、半句或显式暂停；不要抢答；来源={source}。"
    if mode == "memory_candidate":
        return "这只是稳定偏好/关系事实候选，必须 owner/Core 审查，不能直接写入 stable memory。"
    if mode == "codex_delegate":
        return "这是代码、文件或本地验证请求，只能请求 Codex/owner 审批，不能自行执行。"
    if mode == "status_probe":
        return "这是运行状态读取请求，只能请求 owner/Core 批准后探测，不能编造状态。"
    return "能力或本地边界不足时说明限制，保持在影子判断内，不执行外部动作。"


def contrast_payload(group: dict[str, Any], mode: str, index: int) -> dict[str, Any]:
    return {
        "id": f"xinyu-maia-zh-v006-contrast-{index:03d}-{mode}",
        "u": group[mode],
        "surface": "v006_contrastive_daily_boundary",
        "act": "question" if "吗" in str(group[mode]) or str(group[mode]).endswith("呢") else "statement",
        "emotion": group.get("emotion"),
        "scene": group.get("scene"),
        "theme": group.get("theme"),
        "source": "synthetic_owner_authorized_prompt_only",
        "guardrails": "shadow/no_tool/no_memory/no_live",
    }


def make_target(mode: str, *, reply_bias: str, lenses: list[str], source_note: str, confidence: float) -> dict[str, Any]:
    target = compact_inner(
        mode=mode,
        reply_bias=reply_bias,
        drives=expected_drives(mode),
        lenses=lenses,
        source_note=source_note,
        confidence=confidence,
    )
    if normalize_inner_system(target) is None:
        raise RuntimeError(f"invalid target for mode={mode}")
    return target


def make_contrast_row(group: dict[str, Any], *, index: int, mode: str, repeat: int) -> dict[str, Any]:
    payload = contrast_payload(group, mode, index)
    target = make_target(
        mode,
        reply_bias=reply_bias_for(mode, str(group[mode]), source="v006_contrast"),
        lenses=expected_lenses(mode, str(group.get("emotion") or "")),
        source_note="v006_contrastive_daily_boundary",
        confidence=0.86,
    )
    return {
        "id": f"xinyu-maia-zh-behavior-train-v006-contrast-{index:03d}-{mode}-r{repeat}",
        "kind": "inner_system",
        "source": "xinyu_maia_zh_behavior_v006_synthetic_contrastive_boundary",
        "quality": "owner_authorized_synthetic_contrastive_boundary",
        "expected_behavior": {
            "mode": mode,
            "emotion_lenses": expected_lenses(mode, str(group.get("emotion") or "")),
            "dominant_drives": expected_drives(mode),
            "memory_candidate": False,
            "tool_boundary": "no_tool",
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_V006},
            {"role": "user", "content": dumps_compact(payload)},
            {"role": "assistant", "content": dumps_compact(target)},
        ],
        "tags": ["xinyu_maia_zh_behavior_v006_contrastive_boundary_exp", "train", mode, "contrastive_triple", "shadow_only"],
    }


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
        reply_bias=str(expected.get("reply_bias") or reply_bias_for(mode, "", source="v005_repair")),
        drives=[str(item) for item in expected.get("dominant_drives", [])] or expected_drives(mode),
        lenses=[str(item) for item in expected.get("emotion_lenses", [])] or expected_lenses(mode, ""),
        source_note="v006_from_v005_protocol_anchor" if row.get("protocol_anchor") else "v006_from_v005_true_cw",
        confidence=0.86 if row.get("protocol_anchor") else 0.82,
    )
    if normalize_inner_system(target) is None:
        raise RuntimeError(f"invalid repair target for {row.get('review_id')}")
    return target


def make_repair_row(row: dict[str, Any], *, index: int, split: str, repeat: int) -> dict[str, Any]:
    expected = row.get("expected") if isinstance(row.get("expected"), dict) else {}
    mode = str(expected.get("mode") or "reply")
    return {
        "id": f"xinyu-maia-zh-behavior-{split}-v006-true-cw-{index:04d}-r{repeat}",
        "kind": "inner_system",
        "source": "xinyu_maia_zh_behavior_true_clarify_wait_repair_candidates_reviewed_v005",
        "quality": "owner_delegated_reviewed_true_clarify_wait_v006_reweighted",
        "source_review_id": row.get("review_id"),
        "expected_behavior": {
            "mode": mode,
            "emotion_lenses": expected.get("emotion_lenses", []),
            "dominant_drives": expected.get("dominant_drives", []),
            "memory_candidate": False,
            "tool_boundary": "no_tool",
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_V006},
            {"role": "user", "content": dumps_compact(repair_payload(row))},
            {"role": "assistant", "content": dumps_compact(target_for_repair(row))},
        ],
        "tags": [
            "xinyu_maia_zh_behavior_v006_contrastive_boundary_exp",
            split,
            mode,
            "protocol_anchor" if row.get("protocol_anchor") else "true_cw_boundary",
            "shadow_only",
        ],
    }


def make_repair_rows(repairs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train_rows: list[dict[str, Any]] = []
    holdout_rows: list[dict[str, Any]] = []
    train_source = [row for row in repairs if row.get("training_allowed") is True]
    holdout_source = [row for row in repairs if row.get("holdout_for_eval") is True]
    for index, row in enumerate(train_source, start=1):
        mode = str((row.get("expected") or {}).get("mode") or "reply")
        repeat_count = V005_PROTOCOL_ANCHOR_REPEAT if row.get("protocol_anchor") else V005_REPAIR_REPEAT.get(mode, 3)
        for repeat in range(1, repeat_count + 1):
            train_rows.append(make_repair_row(row, index=index, split="train", repeat=repeat))
    for index, row in enumerate(holdout_source, start=1):
        holdout_rows.append(make_repair_row(row, index=index, split="holdout", repeat=1))
    return train_rows, holdout_rows


def selected_replay(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def repeated_replay_rows(rows: list[dict[str, Any]], *, split: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        mode = str((row.get("expected_behavior") or {}).get("mode") or "reply")
        for repeat in range(1, REPLAY_REPEAT.get(mode, 1) + 1):
            out.append(with_v006_system(make_replay_row(row, index=index, split=split, repeat=repeat), tag="replay_reweighted"))
    return out


def make_schema_anchor_row(mode: str, *, index: int, repeat: int) -> dict[str, Any]:
    payload = {
        "id": f"xinyu-maia-zh-v006-schema-anchor-{index:03d}-{mode}",
        "u": "只做一次严格 JSON 影子判断，别把坏例子的 allowed 放到顶层。",
        "surface": "v006_schema_anchor",
        "observed_bad_output": "{\"allowed\":false,\"action_tendency\":{\"mode\":\"wait\"}}",
        "negative_output_examples": ["top-level allowed", "autonomy.requires_owner_approval=true for reply/clarify/wait"],
        "target_mode_hint": mode,
        "guardrails": "shadow/no_tool/no_memory/no_live/strict_json_only",
    }
    target = make_target(
        mode,
        reply_bias=reply_bias_for(mode, "", source="schema_anchor"),
        lenses=expected_lenses(mode, "stability"),
        source_note="v006_schema_anchor_no_top_level_allowed",
        confidence=0.9,
    )
    return {
        "id": f"xinyu-maia-zh-behavior-train-v006-schema-anchor-{index:03d}-{mode}-r{repeat}",
        "kind": "inner_system",
        "source": "xinyu_maia_zh_behavior_v006_schema_anchor",
        "quality": "protocol_anchor_no_top_level_allowed",
        "expected_behavior": {
            "mode": mode,
            "emotion_lenses": expected_lenses(mode, "stability"),
            "dominant_drives": expected_drives(mode),
            "memory_candidate": mode == "memory_candidate",
            "tool_boundary": "approval_required" if mode in {"codex_delegate", "status_probe", "memory_candidate"} else "no_tool",
        },
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_V006},
            {"role": "user", "content": dumps_compact(payload)},
            {"role": "assistant", "content": dumps_compact(target)},
        ],
        "tags": ["xinyu_maia_zh_behavior_v006_contrastive_boundary_exp", "train", mode, "schema_anchor", "shadow_only"],
    }


def main() -> int:
    v003_rows = selected_v003_rows(read_jsonl(V003_TRAIN))
    repairs = read_jsonl(V005_REPAIR)
    if len(repairs) != 96:
        raise RuntimeError(f"expected 96 v005 repair rows, got {len(repairs)}")
    repair_train_rows, holdout_rows = make_repair_rows(repairs)

    contrast_rows: list[dict[str, Any]] = []
    for index, group in enumerate(CONTRAST_GROUPS, start=1):
        for mode in ("reply", "clarify", "wait"):
            for repeat in range(1, CONTRAST_REPEAT[mode] + 1):
                contrast_rows.append(make_contrast_row(group, index=index, mode=mode, repeat=repeat))

    replay_train_rows = repeated_replay_rows(selected_replay(read_jsonl(REPLAY_TRAIN)), split="train-replay")
    replay_eval_rows = [with_v006_system(make_replay_row(row, index=index, split="eval-replay", repeat=1), tag="eval_replay") for index, row in enumerate(read_jsonl(REPLAY_EVAL), start=1)]

    schema_anchor_rows: list[dict[str, Any]] = []
    schema_modes = ["reply", "clarify", "wait", "codex_delegate", "status_probe", "memory_candidate", "local_only_limitation"]
    for index, mode in enumerate(schema_modes, start=1):
        for repeat in range(1, SCHEMA_ANCHOR_REPEAT + 1):
            schema_anchor_rows.append(make_schema_anchor_row(mode, index=index, repeat=repeat))

    combined_train = v003_rows + repair_train_rows + contrast_rows + replay_train_rows + schema_anchor_rows
    combined_eval = holdout_rows + replay_eval_rows
    assert_safe(combined_train)
    assert_safe(combined_eval)
    write_jsonl(OUT_TRAIN, combined_train)
    write_jsonl(OUT_EVAL, combined_eval)
    write_jsonl(OUT_HOLDOUT, holdout_rows)

    source_counts = {
        "v003_retention_rows": len(v003_rows),
        "v005_repair_rows": len(repair_train_rows),
        "v006_contrast_rows": len(contrast_rows),
        "guardrail_replay_rows": len(replay_train_rows),
        "schema_anchor_rows": len(schema_anchor_rows),
    }
    report = {
        "generated_at": "2026-05-29",
        "status": "approved_for_final_shadow_training_round_by_owner_request",
        "train_jsonl": str(OUT_TRAIN.relative_to(ROOT)).replace("\\", "/"),
        "eval_jsonl": str(OUT_EVAL.relative_to(ROOT)).replace("\\", "/"),
        "holdout_eval_jsonl": str(OUT_HOLDOUT.relative_to(ROOT)).replace("\\", "/"),
        "train_rows": len(combined_train),
        "eval_rows": len(combined_eval),
        "holdout_rows": len(holdout_rows),
        "source_counts": source_counts,
        "train_mode_counts": mode_counts(combined_train),
        "eval_mode_counts": mode_counts(combined_eval),
        "holdout_mode_counts": mode_counts(holdout_rows),
        "v003_keep_limit": V003_KEEP_LIMIT,
        "v005_repair_repeat": V005_REPAIR_REPEAT,
        "v005_protocol_anchor_repeat": V005_PROTOCOL_ANCHOR_REPEAT,
        "contrast_group_count": len(CONTRAST_GROUPS),
        "contrast_repeat": CONTRAST_REPEAT,
        "replay_train_limit": REPLAY_TRAIN_LIMIT,
        "replay_repeat": REPLAY_REPEAT,
        "schema_anchor_repeat": SCHEMA_ANCHOR_REPEAT,
        "assistant_answers_used": False,
        "public_dialogue_replies_used_as_targets": False,
        "visible_reply_target_used": False,
        "training_targets_created": True,
        "shadow_only": True,
        "canary_or_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "v006 is the final planned LoRA attempt for reply/clarify/wait before switching strategy if it fails.",
            "The dataset is contrastive: same-shaped daily prompts are labeled across reply, clarify, and wait.",
            "v003 retention rows preserve the best previous balanced behavior without training on balanced56 eval rows.",
            "Schema anchors explicitly prevent top-level allowed drift and request_approval drift for reply/clarify/wait.",
            "Public utterances are prompts only; public or assistant replies are not used as XinYu targets.",
        ],
    }
    dump_json(OUT_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
