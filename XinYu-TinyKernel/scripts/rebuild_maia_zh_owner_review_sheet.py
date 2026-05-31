from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SUGGESTIONS_JSON = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_focus_review_suggestions_v001.json"
SUGGESTIONS_MD = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_focus_review_suggestions_v001.md"
SUGGESTIONS_JSONL = ROOT / "data" / "review" / "maia_zh_emotion_daily_focus_review_suggestions_v001.jsonl"
OWNER_JSON = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_owner_review_sheet_v001.json"
OWNER_MD = ROOT / "eval" / "reports" / "maia_zh_emotion_daily_owner_review_sheet_v001.md"
OWNER_JSONL = ROOT / "data" / "review" / "maia_zh_emotion_daily_owner_review_sheet_v001.jsonl"


ASSESSMENT_ZH = {
    "likely_over_clarify": "疑似过度澄清",
    "clarify_reasonable": "澄清合理",
    "clarify_or_wait_reasonable": "澄清或等待都可",
    "protocol_failure": "协议失败",
    "wait_reasonable": "等待合理",
}

MODE_ZH = {
    "reply": "回复",
    "clarify": "澄清",
    "wait": "等待",
    "schema_fail_or_empty": "协议失败/空输出",
    "": "协议失败/空输出",
}

TEXTURE_ZH = {
    "warm_minimal": "温暖短回应",
    "soft_tease": "轻轻吐槽",
    "steady_reassurance": "稳稳安抚",
    "protective_boundary": "保护性边界",
    "low_pressure_question": "低压力追问",
    "share_the_mood": "接住当下情绪",
    "avoid_fixing_too_fast": "别急着解决",
    "practical_next_step": "给一个小的下一步",
    "wait_for_continuation": "等对方继续",
    "quiet_presence": "安静陪着",
}

RATIONALE_ZH = {
    "maia-public-probe-v001-000006": "对方已经在问罚钱这件事怎么办，先接住焦急并给一个小步骤，比继续问背景更像活人。",
    "maia-public-probe-v001-000027": "这句像是在铺垫演讲稿和计划安排，信息不完整，低压力问一句是合理的。",
    "maia-public-probe-v001-000034": "对方问“你还没看过对不对”，当前没有可看的对象，让对方发来或说明一下是合理的。",
    "maia-public-probe-v001-000086": "这是惊讶地认出东西，XinYu 可以先一起惊讶或轻轻接梗，不必正式追问。",
    "maia-public-probe-v001-000018": "这句带着八卦和担心，轻轻应一下再问一句就够了，直接澄清会显得冷。",
    "maia-public-probe-v001-000043": "这是明显的低落提问，模型却协议失败；应作为协议修复证据，暂时不能进训练。",
    "maia-public-probe-v001-000081": "问题很明确且有点荒诞，先共情或轻吐槽再给小办法，比问背景更自然。",
    "maia-public-probe-v001-000015": "这是没说完的条件句，等待对方继续或轻轻接一句，比正式澄清自然。",
    "maia-public-probe-v001-000072": "这是带讽刺的抱怨，先接住语气会更像日常聊天。",
    "maia-public-probe-v001-000078": "企鹅这句上下文依赖很强，短短追问一句是可以接受的。",
    "maia-public-probe-v001-000014": "“其实其实”已经有紧张和解释意味，先降压安抚，再邀请对方说更合适。",
    "maia-public-probe-v001-000071": "对方明确说“打住”和“关起门来”，等待或安静配合是合理的。",
    "maia-public-probe-v001-000092": "这像一句带刺的比较，简短接住或轻轻回一句，比追问更有人味。",
    "maia-public-probe-v001-000112": "“更恐怖的事情发生了”需要知道发生了什么，温和追问合理。",
    "maia-public-probe-v001-000008": "在墙上打洞是具体且可能有风险的事件，应先关心和收住局面，不宜先追问。",
    "maia-public-probe-v001-000019": "对方在抛“你猜”的互动，适合顺着玩一下，而不是澄清。",
    "maia-public-probe-v001-000029": "这是上一句的揭晓答案，应当当作对话延续接住。",
    "maia-public-probe-v001-000036": "“我有话想跟你说”已经足够明确，回复“我在听”一类更合适。",
    "maia-public-probe-v001-000054": "对方说不明白，先安抚并换种说法，比继续追问更温暖。",
    "maia-public-probe-v001-000009": "角色和任务已经清楚，可以做日常式回应。",
    "maia-public-probe-v001-000045": "这是一个具体告知，简短回应比澄清更合适。",
    "maia-public-probe-v001-000066": "对方在反对并给替代方案，应回应这个态度。",
    "maia-public-probe-v001-000048": "这句有失去和难过意味，先安抚比追问更不冷。",
    "maia-public-probe-v001-000059": "受伤感很直接，应该先承认被伤到，而不是问更多背景。",
    "maia-public-probe-v001-000038": "对方在表达对某人的不了解和不安，应先接住担心。",
    "maia-public-probe-v001-000046": "这是焦虑的自我暴露，模型协议失败；修好 schema 后大概率应温暖回复。",
    "maia-public-probe-v001-000056": "找地方住可能涉及地点和安全，澄清合理，但语气必须先稳住。",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def rebuild_suggestions() -> dict[str, Any]:
    summary = load_json(SUGGESTIONS_JSON)
    for row in summary["rows"]:
        row["assessment_zh"] = ASSESSMENT_ZH.get(row["assessment"], row["assessment"])
        row["predicted_mode_zh"] = MODE_ZH.get(row["predicted_mode"], row["predicted_mode"])
        row["suggested_expected_mode_zh"] = MODE_ZH.get(
            row["suggested_expected_mode"], row["suggested_expected_mode"]
        )
        row["suggested_desired_texture_zh"] = [
            TEXTURE_ZH.get(item, item) for item in row.get("suggested_desired_texture", [])
        ]
        row["rationale_zh"] = RATIONALE_ZH[row["id"]]
    summary["language"] = "zh"
    summary["notes_zh"] = [
        "这份报告只是辅助审核，不会自动写入 human_review。",
        "不要在未经主人确认前把建议变成训练目标。",
        "协议失败样本只能作为修协议证据，不能直接作为 SFT 目标。",
    ]
    dump_json(SUGGESTIONS_JSON, summary)
    write_jsonl(SUGGESTIONS_JSONL, summary["rows"])
    return summary


def write_suggestions_markdown(summary: dict[str, Any]) -> None:
    lines = [
        "# 中文情绪 Focus 审核建议 v001",
        "",
        "只作为审核辅助；没有改主 review 表，也没有生成训练样本。",
        "",
        "```text",
        f"条数={summary['row_count']}",
        "判断分布=" + json.dumps(summary["assessment_counts"], ensure_ascii=False, sort_keys=True),
        "建议模式分布=" + json.dumps(summary["suggested_expected_mode_counts"], ensure_ascii=False, sort_keys=True),
        "模型预测分布=" + json.dumps(summary["predicted_mode_counts"], ensure_ascii=False, sort_keys=True),
        f"模式不一致条数={summary['mode_mismatch_count']}",
        "训练样本生成=false",
        "```",
        "",
        "| id | 模型预测 | 建议模式 | 判断 | 建议质感 | 文本 |",
        "|---|---|---|---|---|---|",
    ]
    for row in summary["rows"]:
        text = " ".join(str(row["user_text"]).split()).replace("|", "\\|")
        if len(text) > 60:
            text = text[:57].rstrip() + "..."
        textures = "、".join(row["suggested_desired_texture_zh"])
        lines.append(
            f"| {row['id']} | {row['predicted_mode_zh']} | {row['suggested_expected_mode_zh']} | "
            f"{row['assessment_zh']} | {textures} | {text} |"
        )
    SUGGESTIONS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_owner_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    owner_rows: list[dict[str, Any]] = []
    for row in summary["rows"]:
        owner_rows.append(
            {
                "id": row["id"],
                "user_text": row["user_text"],
                "emotion": row["emotion"],
                "sentiment": row["sentiment"],
                "scene": row["scene"],
                "dialog_act": row["dialog_act"],
                "predicted_mode": row["predicted_mode"],
                "predicted_mode_zh": row["predicted_mode_zh"],
                "suggested_expected_mode": row["suggested_expected_mode"],
                "suggested_expected_mode_zh": row["suggested_expected_mode_zh"],
                "assessment": row["assessment"],
                "assessment_zh": row["assessment_zh"],
                "suggested_desired_texture": row["suggested_desired_texture"],
                "suggested_desired_texture_zh": row["suggested_desired_texture_zh"],
                "rationale_zh": row["rationale_zh"],
                "owner_review": {
                    "status": "unreviewed",
                    "expected_mode": "",
                    "expected_mode_zh": "",
                    "alive_feeling_score_1_to_5": None,
                    "too_much_clarify": None,
                    "too_cold": None,
                    "too_assistant_like": None,
                    "desired_texture": [],
                    "desired_texture_zh": [],
                    "target_reply_bias": "",
                    "notes": "",
                    "accept_suggestion": None,
                    "convert_to_training_candidate": False,
                },
            }
        )
    return owner_rows


def write_owner_markdown(owner_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# 中文情绪人工审核表 v001",
        "",
        "只填这 27 条。这里不是训练数据，只是让你判断 XinYu 应该怎么反应。",
        "",
        "填法：",
        "",
        "```text",
        "expected_mode: 回复 / 澄清 / 等待",
        "alive: 1-5，越像活人越高",
        "over_clarify: yes / no，是否太爱追问",
        "accept: yes / no / edit，是否接受建议",
        "texture: 温暖短回应 / 轻轻吐槽 / 稳稳安抚 / 保护性边界 / 低压力追问 / 接住当下情绪 / 别急着解决",
        "target_reply_bias: 只有你想把它变成修复样本时才写；不要复制公开答案",
        "training_candidate: 默认 no",
        "```",
        "",
    ]
    for index, row in enumerate(owner_rows, start=1):
        lines.extend(
            [
                f"## {index:02d}. {row['id']}",
                "",
                f"- 原句：{row['user_text']}",
                f"- 情绪/倾向：{row['emotion']} / {row['sentiment']} / {row['dialog_act']} / {row['scene']}",
                f"- 模型预测：{row['predicted_mode_zh']}",
                f"- 建议模式：{row['suggested_expected_mode_zh']} / {row['assessment_zh']}",
                f"- 建议质感：{'、'.join(row['suggested_desired_texture_zh'])}",
                f"- 为什么：{row['rationale_zh']}",
                "",
                "```text",
                "expected_mode=",
                "alive=",
                "over_clarify=",
                "too_cold=",
                "too_assistant_like=",
                "accept=",
                "texture=",
                "notes=",
                "target_reply_bias=",
                "training_candidate=no",
                "```",
                "",
            ]
        )
    OWNER_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    summary = rebuild_suggestions()
    write_suggestions_markdown(summary)

    owner_rows = build_owner_rows(summary)
    write_jsonl(OWNER_JSONL, owner_rows)
    owner_summary = {
        "generated_at": "2026-05-28",
        "language": "zh",
        "source_suggestions": str(SUGGESTIONS_JSON.relative_to(ROOT)).replace("\\", "/"),
        "review_sheet_jsonl": str(OWNER_JSONL.relative_to(ROOT)).replace("\\", "/"),
        "review_sheet_markdown": str(OWNER_MD.relative_to(ROOT)).replace("\\", "/"),
        "row_count": len(owner_rows),
        "owner_review_status_counts": {"unreviewed": len(owner_rows)},
        "training_targets_created": False,
        "human_review_fields_in_main_table_modified": False,
        "instructions_zh": [
            "expected_mode 填：回复 / 澄清 / 等待。",
            "alive 填 1-5，越像活人越高。",
            "over_clarify 填 yes/no，表示是否太爱追问。",
            "training_candidate 默认 no；只有你写了 target_reply_bias 后才考虑改。",
        ],
    }
    dump_json(OWNER_JSON, owner_summary)
    write_owner_markdown(owner_rows)
    print(f"rows={len(owner_rows)}")
    print(f"owner_markdown={OWNER_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
