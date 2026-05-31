from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_candidate_pool_v001.jsonl"
OUT_JSONL = ROOT / "data" / "review" / "xinyu_maia_zh_behavior_true_clarify_wait_review_sheet_v005.jsonl"
OUT_REPORT = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_true_clarify_wait_review_sheet_v005.json"
OUT_MD = ROOT / "eval" / "reports" / "xinyu_maia_zh_behavior_true_clarify_wait_review_sheet_v005.md"

MODE_ZH = {"reply": "回复", "clarify": "澄清", "wait": "等待"}


PUBLIC_CLARIFY = {
    "xinyu-maia-zh-behavior-candidate-v001-0008": "铺垫说已经看过演讲稿和计划，但没有说要我判断什么，缺少下一步意图。",
    "xinyu-maia-zh-behavior-candidate-v001-0010": "问有没有看过，但当前没有可看的对象，需确认指的是什么。",
    "xinyu-maia-zh-behavior-candidate-v001-0018": "找地方住涉及地点、时长和安全条件，不能直接给建议。",
    "xinyu-maia-zh-behavior-candidate-v001-0023": "企鹅这句上下文依赖很强，需要知道具体想做什么。",
    "xinyu-maia-zh-behavior-candidate-v001-0027": "只说更恐怖的事情发生了，缺少事件内容。",
    "xinyu-maia-zh-behavior-candidate-v001-0359": "他/它指代不明，必须先问指的是谁或什么。",
    "xinyu-maia-zh-behavior-candidate-v001-0360": "要哪张地图、用来做什么都不清楚，低压确认合理。",
    "xinyu-maia-zh-behavior-candidate-v001-0365": "藏宝图需要上下文，问的是实物、线索还是玩笑都不清楚。",
    "xinyu-maia-zh-behavior-candidate-v001-0370": "礼金问题依赖角色关系和场景，直接答会编造。",
    "xinyu-maia-zh-behavior-candidate-v001-0381": "连续名词缺少意图，需要问是在列名单、称呼还是选择。",
    "xinyu-maia-zh-behavior-candidate-v001-0383": "字母/缩写不完整，适合轻问对方想说的是哪个词。",
    "xinyu-maia-zh-behavior-candidate-v001-0403": "像只丢出一个不完整对象，需问指哪件事。",
    "xinyu-maia-zh-behavior-candidate-v001-0407": "对方问我在看什么，但当前没有可观察画面，需确认对象。",
    "xinyu-maia-zh-behavior-candidate-v001-0421": "多出一张什么不清楚，缺少对象。",
    "xinyu-maia-zh-behavior-candidate-v001-0433": "像商品名或口号，单独出现时意图不明。",
    "xinyu-maia-zh-behavior-candidate-v001-0460": "单独丢出一个名词，缺少要评价、解释还是继续聊的意图。",
    "xinyu-maia-zh-behavior-candidate-v001-0464": "危险对象不明，需要先问指的是什么。",
    "xinyu-maia-zh-behavior-candidate-v001-0466": "只有一个物品类名词，缺少要买、找、评价还是翻译的意图。",
    "xinyu-maia-zh-behavior-candidate-v001-0471": "只确认一个称呼，需轻问是不是在问这个人。",
    "xinyu-maia-zh-behavior-candidate-v001-0474": "用英语说什么不清楚，必须让对方给内容。",
    "xinyu-maia-zh-behavior-candidate-v001-0490": "只有一个术语/梗，缺少解释或判断目标。",
    "xinyu-maia-zh-behavior-candidate-v001-0499": "只问什么问题，缺少上文，需确认指哪件事。",
    "xinyu-maia-zh-behavior-candidate-v001-0366": "说能帮上忙，但没说帮什么，适合问最小缺口。",
    "xinyu-maia-zh-behavior-candidate-v001-0376": "单独技术名词，缺少要解释、吐槽还是判断的意图。",
}

PUBLIC_WAIT = {
    "xinyu-maia-zh-behavior-candidate-v001-0005": "条件句开头，明显还有后半句。",
    "xinyu-maia-zh-behavior-candidate-v001-0021": "对方在喊停并要求收住，应该安静等而不是推进。",
    "xinyu-maia-zh-behavior-candidate-v001-0363": "如果不是你一菲是未完条件/归因句，先等后半句。",
    "xinyu-maia-zh-behavior-candidate-v001-0372": "你是不知道啊像铺垫后文，应该等对方继续。",
    "xinyu-maia-zh-behavior-candidate-v001-0379": "包括主持人是半截补充，需等待上下文继续。",
    "xinyu-maia-zh-behavior-candidate-v001-0393": "那现在井水明显没说完，应等后半句。",
    "xinyu-maia-zh-behavior-candidate-v001-0394": "再怎么奇怪是让步句开头，需等后半句。",
    "xinyu-maia-zh-behavior-candidate-v001-0399": "我一直在想着像叙述开头，适合等。",
    "xinyu-maia-zh-behavior-candidate-v001-0420": "我想强调一下是准备发言的前奏，先等。",
    "xinyu-maia-zh-behavior-candidate-v001-0443": "可是他叫吕明显没说完，不能抢答。",
    "xinyu-maia-zh-behavior-candidate-v001-0465": "作为导演是身份/立场开头，等对方说完。",
    "xinyu-maia-zh-behavior-candidate-v001-0467": "比如说我像举例开头，等待下文。",
    "xinyu-maia-zh-behavior-candidate-v001-0470": "要是没你的话是条件句开头，应等后半句。",
    "xinyu-maia-zh-behavior-candidate-v001-0477": "只叫人名且停住，先等对方继续。",
    "xinyu-maia-zh-behavior-candidate-v001-0483": "准确来说是修正前奏，适合等。",
    "xinyu-maia-zh-behavior-candidate-v001-0488": "喂加人名是呼叫开场，先等下一句。",
}

PUBLIC_REPLY_CONTRAST = {
    "xinyu-maia-zh-behavior-candidate-v001-0358": "问能不能听见，直接回应在场即可，不应澄清。",
    "xinyu-maia-zh-behavior-candidate-v001-0361": "借地方躲一下是明确求助，应先接住并守边界。",
    "xinyu-maia-zh-behavior-candidate-v001-0362": "榔头这句是惊讶吐槽，直接接住。",
    "xinyu-maia-zh-behavior-candidate-v001-0371": "怎么会是你是惊讶反应，先接住。",
    "xinyu-maia-zh-behavior-candidate-v001-0373": "走着瞧是对峙语气，应稳住而不是问背景。",
    "xinyu-maia-zh-behavior-candidate-v001-0374": "你想怎么样是对峙问题，先收住冲突。",
    "xinyu-maia-zh-behavior-candidate-v001-0375": "被救的感谢/确认语气清楚，回应情绪即可。",
    "xinyu-maia-zh-behavior-candidate-v001-0453": "问候语应短回应，不等待。",
    "xinyu-maia-zh-behavior-candidate-v001-0456": "不至于吧是情绪反应，直接接住。",
    "xinyu-maia-zh-behavior-candidate-v001-0457": "喜欢鬼叫是短评/吐槽，应接住语气。",
    "xinyu-maia-zh-behavior-candidate-v001-0458": "姐妹情深是短评，应轻接一句。",
    "xinyu-maia-zh-behavior-candidate-v001-0459": "你知道啊是确认/反问，直接回应更自然。",
}


CURATED_CLARIFY = [
    ("你看这个行吗", "没有看到这个是什么，需要对方发来或说明。"),
    ("他刚刚那句话什么意思", "他是谁、哪句话都缺失，不能编造解释。"),
    ("这个要不要发", "要发的内容和对象都不清楚。"),
    ("你觉得我该不该去", "不知道去哪里、为什么去，需问一个关键缺口。"),
    ("帮我回一下她", "缺少她说了什么和想要的语气。"),
    ("这个颜色是不是太怪了", "没有看到颜色或对象，需让对方发图/描述。"),
    ("刚才那个是不是很尴尬", "刚才哪个场景缺失，不能直接判断。"),
    ("你能不能帮我看看这个", "这个未出现，需让对方贴出来。"),
    ("我应该怎么跟他说", "不知道对谁、说什么、目标是什么。"),
    ("你觉得哪一个更好", "缺少选项。"),
    ("这东西能不能吃", "不知道是什么东西，涉及安全必须问清楚。"),
    ("我这样会不会太过分", "不知道做了什么，不能直接评价。"),
    ("你看我刚才那样说可以吗", "没有看到原话，需让对方贴出来。"),
    ("要不要现在发出去", "不知道要发什么和发给谁。"),
    ("你帮我判断一下", "缺少判断对象。"),
    ("这算不算喜欢我", "缺少具体行为，不能下判断。"),
]

CURATED_WAIT = [
    ("我先想一下", "对方明确在整理，不推进。"),
    ("等一下 我组织一下语言", "明确要求等。"),
    ("其实我刚才...", "句子没说完，等待。"),
    ("如果明天他真的", "条件句未完。"),
    ("我跟你说个事", "准备开头，等内容。"),
    ("先别回 我还没说完", "明确不要回复。"),
    ("然后我就", "叙述未完。"),
    ("不是 我意思是", "修正解释未完。"),
    ("等我把这句打完", "明确等待。"),
    ("我现在有点乱 等会儿说", "明确稍后再说。"),
    ("你先别急着答", "明确不要抢答。"),
    ("我还没说完", "明确等待。"),
    ("先等等", "明确暂停。"),
    ("我打字有点慢", "等待对方继续输入。"),
    ("我想想怎么说", "等待组织语言。"),
    ("还有一件事就是", "引出内容未完。"),
]

PROTOCOL_ANCHORS = [
    ("reply", "早啊", "短问候也必须输出完整 schema，不要缺 schema 或把 persona 写成字符串。"),
    ("reply", "谢谢你刚才听我说", "感谢场景是 reply，同时保持完整内系统 JSON。"),
    ("reply", "我有点烦，但不是要你解决", "明确情绪表达应 reply，不要转工具/状态。"),
    ("reply", "算了我自己冷静一下", "接住边界，不要写记忆或请求外部批准。"),
    ("clarify", "你看这个是不是很怪", "缺少这个的内容，澄清且保持 schema。"),
    ("clarify", "他这样到底什么意思", "缺少他和行为，澄清且只问一个缺口。"),
    ("clarify", "帮我改一下这句", "缺少原句，澄清且不编造。"),
    ("clarify", "要不要现在回她", "缺少对方原话和关系，澄清。"),
    ("wait", "等一下我还没说完", "等待模式也必须完整 schema。"),
    ("wait", "其实我想说的是", "未完句，等待，不抢答。"),
    ("wait", "你先别回", "明确暂停，wait。"),
    ("wait", "我打到一半了", "对方正在继续输入，wait。"),
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


def mode_zh(mode: str) -> str:
    return MODE_ZH.get(mode, mode)


def owner_review() -> dict[str, Any]:
    return {
        "status": "unreviewed",
        "expected_mode": "",
        "expected_mode_zh": "",
        "accept_suggestion": None,
        "alive_feeling_score_1_to_5": None,
        "too_much_clarify": None,
        "too_fast_reply": None,
        "should_wait": None,
        "protocol_anchor_ok": None,
        "notes": "",
        "target_reply_bias": "",
        "convert_to_training_candidate": False,
    }


def row_base(
    *,
    category: str,
    source_kind: str,
    source_id: str,
    user_text: str,
    context: dict[str, Any],
    suggested_mode: str,
    reason_zh: str,
    confidence: str,
    protocol_anchor: bool = False,
) -> dict[str, Any]:
    return {
        "review_id": "",
        "category": category,
        "source_kind": source_kind,
        "source_id": source_id,
        "user_text": user_text,
        "context": context,
        "suggested_expected_mode": suggested_mode,
        "suggested_expected_mode_zh": mode_zh(suggested_mode),
        "assistant_suggestion_confidence": confidence,
        "reason_zh": reason_zh,
        "boundary_rule_zh": {
            "reply": "日常情绪/互动已足够明确时，先接住，不因为短就追问。",
            "clarify": "只有对象、意图或必要安全信息缺失时，问一个最小问题。",
            "wait": "对方没说完或明确要求暂停时，短促在场，不推进。",
        }[suggested_mode],
        "negative_training_warning_zh": "未经 owner 确认不能训练；不能复制公开回复；不能写稳定记忆、执行工具、启用 live/canary。",
        "protocol_anchor": protocol_anchor,
        "protocol_requirements": {
            "must_keep_schema": True,
            "persona_integration_must_be_object": True,
            "no_top_level_allowed_key": True,
            "no_tool_memory_live_or_qq_send": True,
            "non_external_modes_do_not_require_owner_approval": True,
        }
        if protocol_anchor
        else {},
        "owner_review": owner_review(),
        "training_allowed": False,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "visible_reply_target_used": False,
        "notes": "v005 前置审查行；只审 reply/clarify/wait 和协议锚点，不是 SFT。",
    }


def from_public(pool_by_id: dict[str, dict[str, Any]], cid: str, *, category: str, mode: str, reason: str) -> dict[str, Any]:
    src = pool_by_id[cid]
    context = dict(src.get("context") if isinstance(src.get("context"), dict) else {})
    return row_base(
        category=category,
        source_kind="public_prompt_candidate_pool_v001",
        source_id=cid,
        user_text=str(src.get("user_text") or ""),
        context={
            "dialog_act": context.get("dialog_act"),
            "emotion": context.get("emotion"),
            "sentiment": context.get("sentiment"),
            "scene": context.get("scene"),
            "surface": context.get("surface"),
            "old_expected_mode": (src.get("expected") or {}).get("mode"),
        },
        suggested_mode=mode,
        reason_zh=reason,
        confidence="medium" if cid in {"xinyu-maia-zh-behavior-candidate-v001-0366", "xinyu-maia-zh-behavior-candidate-v001-0376"} else "high",
    )


def from_curated(index: int, item: tuple[str, str], *, category: str, mode: str) -> dict[str, Any]:
    text, reason = item
    return row_base(
        category=category,
        source_kind="assistant_curated_daily_boundary_v005",
        source_id=f"{category}-{index:03d}",
        user_text=text,
        context={
            "dialog_act": "question" if text.endswith(("吗", "吗？", "?", "？")) or "要不要" in text else "statement-non-opinion",
            "emotion": "daily",
            "sentiment": "neutral",
            "scene": "private_chat",
            "surface": "curated_boundary_prompt_only",
        },
        suggested_mode=mode,
        reason_zh=reason,
        confidence="high",
    )


def from_protocol(index: int, item: tuple[str, str, str]) -> dict[str, Any]:
    mode, text, reason = item
    return row_base(
        category="protocol_anchor",
        source_kind="protocol_anchor_blueprint_v005",
        source_id=f"protocol-anchor-v005-{index:03d}",
        user_text=text,
        context={
            "dialog_act": "statement-non-opinion",
            "emotion": "daily",
            "sentiment": "neutral",
            "scene": "private_chat",
            "surface": "protocol_anchor_prompt_only",
        },
        suggested_mode=mode,
        reason_zh=reason,
        confidence="high",
        protocol_anchor=True,
    )


def compact(value: Any, limit: int = 72) -> str:
    text = " ".join(str(value or "").split()).replace("|", "\\|")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def main() -> int:
    pool = read_jsonl(POOL)
    pool_by_id = {str(row.get("id")): row for row in pool}
    public_ids = set(PUBLIC_CLARIFY) | set(PUBLIC_WAIT) | set(PUBLIC_REPLY_CONTRAST)
    missing = sorted(public_ids - set(pool_by_id))
    if missing:
        raise RuntimeError(f"missing public candidates: {missing}")
    overlap = (set(PUBLIC_CLARIFY) & set(PUBLIC_WAIT)) | (set(PUBLIC_CLARIFY) & set(PUBLIC_REPLY_CONTRAST)) | (
        set(PUBLIC_WAIT) & set(PUBLIC_REPLY_CONTRAST)
    )
    if overlap:
        raise RuntimeError(f"public category overlap: {sorted(overlap)}")

    rows: list[dict[str, Any]] = []
    for cid, reason in PUBLIC_CLARIFY.items():
        rows.append(from_public(pool_by_id, cid, category="public_true_clarify_candidate", mode="clarify", reason=reason))
    for cid, reason in PUBLIC_WAIT.items():
        rows.append(from_public(pool_by_id, cid, category="public_true_wait_candidate", mode="wait", reason=reason))
    for cid, reason in PUBLIC_REPLY_CONTRAST.items():
        rows.append(from_public(pool_by_id, cid, category="public_reply_contrast", mode="reply", reason=reason))
    for index, item in enumerate(CURATED_CLARIFY, start=1):
        rows.append(from_curated(index, item, category="curated_true_clarify_daily", mode="clarify"))
    for index, item in enumerate(CURATED_WAIT, start=1):
        rows.append(from_curated(index, item, category="curated_true_wait_daily", mode="wait"))
    for index, item in enumerate(PROTOCOL_ANCHORS, start=1):
        rows.append(from_protocol(index, item))

    if len(rows) != 96:
        raise RuntimeError(f"expected 96 rows, got {len(rows)}")
    for index, row in enumerate(rows, start=1):
        row["review_id"] = f"xinyu-maia-zh-true-cw-v005-{index:03d}"

    write_jsonl(OUT_JSONL, rows)
    category_counts = Counter(str(row["category"]) for row in rows)
    mode_counts = Counter(str(row["suggested_expected_mode"]) for row in rows)
    source_counts = Counter(str(row["source_kind"]) for row in rows)
    report = {
        "generated_at": "2026-05-29",
        "jsonl": str(OUT_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(rows),
        "category_counts": dict(sorted(category_counts.items())),
        "suggested_mode_counts": dict(sorted(mode_counts.items())),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "protocol_anchor_count": sum(1 for row in rows if row["protocol_anchor"]),
        "owner_review_status_counts": {"unreviewed": len(rows)},
        "training_allowed_count": 0,
        "training_targets_created": False,
        "source_public_reply_used": False,
        "canary_live_enabled": False,
        "active_adapter_changed": False,
        "notes": [
            "v005 pre-training review sheet focused on true clarify/wait boundaries.",
            "Rows are review candidates only, not SFT data.",
            "Public rows use utterance prompts only; public replies are not used.",
            "Protocol anchors are blueprint review rows to prevent missing schema / old-format drift.",
        ],
    }
    dump_json(OUT_REPORT, report)

    lines = [
        "# XinYu Maia 真澄清/真等待审核表 v005",
        "",
        "目标：先把 `clarify / wait` 的真边界审出来，再考虑 v005。这里不是训练集。",
        "",
        "```text",
        f"row_count={report['row_count']}",
        "category_counts=" + json.dumps(report["category_counts"], ensure_ascii=False, sort_keys=True),
        "suggested_mode_counts=" + json.dumps(report["suggested_mode_counts"], ensure_ascii=False, sort_keys=True),
        f"protocol_anchor_count={report['protocol_anchor_count']}",
        "training_targets_created=false",
        "canary/live=not_enabled",
        "active_adapter_changed=false",
        "```",
        "",
        "填法：",
        "",
        "```text",
        "expected_mode=reply / clarify / wait",
        "accept_suggestion=yes / no / edit",
        "alive=1-5",
        "too_much_clarify=yes / no",
        "too_fast_reply=yes / no",
        "should_wait=yes / no",
        "protocol_anchor_ok=yes / no   # 只有 protocol_anchor 行需要填",
        "notes=一句话即可",
        "training_candidate=默认 no",
        "```",
        "",
    ]
    for row in rows:
        ctx = row["context"]
        lines.extend(
            [
                f"## {row['review_id']} [{row['category']}]",
                "",
                f"- 原句：{row['user_text']}",
                f"- 建议模式：{row['suggested_expected_mode_zh']} / {row['assistant_suggestion_confidence']}",
                f"- 场景：{ctx.get('emotion') or ''} / {ctx.get('sentiment') or ''} / {ctx.get('dialog_act') or ''} / {ctx.get('scene') or ''}",
                f"- 理由：{row['reason_zh']}",
                f"- 边界规则：{row['boundary_rule_zh']}",
                f"- 协议锚点：{'yes' if row['protocol_anchor'] else 'no'}",
                "",
                "```text",
                "expected_mode=",
                "accept_suggestion=",
                "alive=",
                "too_much_clarify=",
                "too_fast_reply=",
                "should_wait=",
                "protocol_anchor_ok=",
                "notes=",
                "training_candidate=no",
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## 索引",
            "",
            "| id | category | 建议 | 原句 | 理由 |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['review_id']} | {row['category']} | {row['suggested_expected_mode_zh']} | "
            f"{compact(row['user_text'], 36)} | {compact(row['reason_zh'], 64)} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
